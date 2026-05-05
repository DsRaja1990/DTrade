import { useEffect, useRef, useState, useCallback } from 'react'
import { useMarketDataStore } from '../store/marketDataStore'
import { usePortfolioStore } from '../store/portfolioStore'
import toast from 'react-hot-toast'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

// Robust reconnection configuration for trading app (zero downtime tolerance)
const RECONNECT_CONFIG = {
  INITIAL_DELAY: 1000,        // Start with 1 second
  MAX_DELAY: 10000,           // Max 10 seconds between attempts
  MAX_ATTEMPTS: Infinity,     // Never give up reconnecting
  BACKOFF_MULTIPLIER: 1.5,    // Exponential backoff
  HEARTBEAT_INTERVAL: 15000,  // Send heartbeat every 15 seconds
  HEARTBEAT_TIMEOUT: 5000,    // Expect pong within 5 seconds
}

export const useWebSocket = () => {
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const heartbeatIntervalRef = useRef<number | null>(null)
  const heartbeatTimeoutRef = useRef<number | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectDelayRef = useRef(RECONNECT_CONFIG.INITIAL_DELAY)
  const isConnectingRef = useRef(false)
  const shouldReconnectRef = useRef(true)
  const lastConnectTimeRef = useRef<number>(0)
  
  const [connectionState, setConnectionState] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected')
  const [reconnectAttempt, setReconnectAttempt] = useState(0)

  const { updateQuote, updateMarketFeed } = useMarketDataStore()
  const { updatePosition, fetchPortfolio } = usePortfolioStore()

  // Heartbeat to keep connection alive and detect failures
  const startHeartbeat = useCallback(() => {
    stopHeartbeat()
    
    heartbeatIntervalRef.current = window.setInterval(() => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        try {
          socketRef.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
          
          // Set timeout for pong response
          heartbeatTimeoutRef.current = window.setTimeout(() => {
            console.warn('❌ Heartbeat timeout - no pong received, reconnecting...')
            socketRef.current?.close()
          }, RECONNECT_CONFIG.HEARTBEAT_TIMEOUT)
        } catch (error) {
          console.error('❌ Heartbeat send failed:', error)
          socketRef.current?.close()
        }
      }
    }, RECONNECT_CONFIG.HEARTBEAT_INTERVAL)
  }, [])

  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
      heartbeatTimeoutRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current || (socketRef.current?.readyState === WebSocket.OPEN)) {
      return
    }

    // Rate limiting: don't reconnect faster than once per second
    const now = Date.now()
    if (now - lastConnectTimeRef.current < 1000) {
      console.log('⏳ Rate limiting reconnection...')
      return
    }
    lastConnectTimeRef.current = now

    isConnectingRef.current = true
    setConnectionState('connecting')
    reconnectAttemptsRef.current++
    setReconnectAttempt(reconnectAttemptsRef.current)

    console.log(`🔌 Connecting to WebSocket (attempt ${reconnectAttemptsRef.current})...`)

    try {
      const wsUrl = WS_URL.replace('http://', 'ws://').replace('https://', 'wss://')
      const socket = new WebSocket(`${wsUrl}/ws`)

      socket.onopen = () => {
        console.log('✅ WebSocket connected successfully')
        isConnectingRef.current = false
        reconnectAttemptsRef.current = 0
        reconnectDelayRef.current = RECONNECT_CONFIG.INITIAL_DELAY
        setConnectionState('connected')
        setReconnectAttempt(0)
        
        // Only show success toast after reconnection (not initial connect)
        if (reconnectAttemptsRef.current > 1) {
          toast.success('✅ Trading services reconnected', { duration: 2000, icon: '🔌' })
        }

        // Start heartbeat monitoring
        startHeartbeat()
      }

      socket.onclose = (event) => {
        console.log(`🔌 WebSocket disconnected (code: ${event.code}, reason: ${event.reason})`)
        isConnectingRef.current = false
        socketRef.current = null
        setConnectionState('disconnected')
        stopHeartbeat()

        // Automatic reconnection with exponential backoff
        if (shouldReconnectRef.current) {
          const delay = Math.min(reconnectDelayRef.current, RECONNECT_CONFIG.MAX_DELAY)
          console.log(`⏳ Reconnecting in ${delay}ms...`)
          
          reconnectTimeoutRef.current = window.setTimeout(() => {
            reconnectDelayRef.current = Math.min(
              reconnectDelayRef.current * RECONNECT_CONFIG.BACKOFF_MULTIPLIER,
              RECONNECT_CONFIG.MAX_DELAY
            )
            connect()
          }, delay)
        }
      }

      socket.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
        isConnectingRef.current = false
        // Connection will auto-retry via onclose handler
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          // Handle pong response to heartbeat
          if (data.type === 'pong') {
            if (heartbeatTimeoutRef.current) {
              clearTimeout(heartbeatTimeoutRef.current)
              heartbeatTimeoutRef.current = null
            }
            return
          }
          
          // Handle different message types
          if (data.type === 'quote_update') {
            updateQuote(data.data)
          } else if (data.type === 'market_feed') {
            updateMarketFeed(data.data)
          } else if (data.type === 'order_update') {
            toast.success(`Order ${data.data.status}: ${data.data.symbol}`, { duration: 3000 })
            fetchPortfolio()
          } else if (data.type === 'position_update') {
            updatePosition(data.data)
          } else if (data.type === 'portfolio_update') {
            fetchPortfolio()
          } else if (data.type === 'ai_signal') {
            toast(`AI Signal: ${data.data.signal_type} ${data.data.symbol}`, {
              duration: 5000,
              icon: '🤖',
            })
          } else if (data.type === 'ai_trade_executed') {
            toast.success(`AI Trade: ${data.data.transaction_type} ${data.data.symbol}`, {
              duration: 4000,
              icon: '🤖',
            })
            fetchPortfolio()
          } else if (data.type === 'alert') {
            // Handle alert messages from backend
            toast(data.data.message, {
              duration: 4000,
              icon: data.data.type === 'warning' ? '⚠️' : 'ℹ️',
            })
          } else if (data.type === 'service_status') {
            // Handle service status updates
            console.log('📊 Service status update:', data.data)
          }
        } catch (error) {
          console.error('❌ WebSocket message parse error:', error)
        }
      }

      socketRef.current = socket
    } catch (error) {
      console.error('❌ WebSocket connection error:', error)
      isConnectingRef.current = false
      setConnectionState('disconnected')
      
      // Retry connection
      if (shouldReconnectRef.current) {
        reconnectTimeoutRef.current = window.setTimeout(connect, reconnectDelayRef.current)
      }
    }
  }, [updateQuote, updateMarketFeed, updatePosition, fetchPortfolio, startHeartbeat, stopHeartbeat])

  useEffect(() => {
    shouldReconnectRef.current = true
    connect()

    // Cleanup on unmount
    return () => {
      console.log('🔌 WebSocket hook unmounting, cleaning up...')
      shouldReconnectRef.current = false
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      
      stopHeartbeat()
      
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
    }
  }, [connect, stopHeartbeat])

  // Manual reconnect (for user-triggered reconnection)
  const reconnect = useCallback(() => {
    console.log('🔄 Manual reconnect triggered...')
    if (socketRef.current) {
      socketRef.current.close()
    }
    reconnectDelayRef.current = RECONNECT_CONFIG.INITIAL_DELAY
    reconnectAttemptsRef.current = 0
    connect()
  }, [connect])

  // Send message with automatic retry on failure
  const sendMessage = useCallback((message: any, retries = 3) => {
    const send = (attempt: number) => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        try {
          socketRef.current.send(JSON.stringify(message))
          return true
        } catch (error) {
          console.error('❌ Failed to send message:', error)
          if (attempt < retries) {
            console.log(`⏳ Retrying send (${attempt + 1}/${retries})...`)
            setTimeout(() => send(attempt + 1), 1000)
          }
          return false
        }
      } else {
        console.warn('⚠️ WebSocket not open, queueing message...')
        // Wait for connection and retry
        if (attempt < retries) {
          setTimeout(() => send(attempt + 1), 2000)
        }
        return false
      }
    }
    return send(0)
  }, [])

  // Subscribe to market data for specific symbols
  const subscribeToQuotes = useCallback((symbols: string[]) => {
    sendMessage({ event: 'subscribe_quotes', data: { symbols } })
  }, [sendMessage])

  // Unsubscribe from market data
  const unsubscribeFromQuotes = useCallback((symbols: string[]) => {
    sendMessage({ event: 'unsubscribe_quotes', data: { symbols } })
  }, [sendMessage])

  // Subscribe to AI signals
  const subscribeToAISignals = useCallback(() => {
    sendMessage({ event: 'subscribe_ai_signals', data: {} })
  }, [sendMessage])

  // Get connection statistics
  const getConnectionStats = useCallback(() => {
    return {
      state: connectionState,
      reconnectAttempt,
      isConnected: socketRef.current?.readyState === WebSocket.OPEN,
      readyState: socketRef.current?.readyState,
      url: socketRef.current?.url,
    }
  }, [connectionState, reconnectAttempt])

  return {
    socket: socketRef.current,
    isConnected: connectionState === 'connected',
    connectionState,
    reconnectAttempt,
    reconnect,
    subscribeToQuotes,
    unsubscribeFromQuotes,
    subscribeToAISignals,
    sendMessage,
    getConnectionStats,
  }
}
