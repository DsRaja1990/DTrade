// Real-time Signal Engine API Service
import { useState, useEffect, useCallback } from 'react'

// Types
export interface MarketData {
  nifty_price: number
  trend: string
  pcr: number
  max_pain: number
  avg_iv: number
  total_ce_oi: number
  total_pe_oi: number
  atm_strike: number
  timestamp: string
}

export interface TradingSignal {
  id: number
  timestamp: string
  signal_type: 'BUY_CE' | 'BUY_PE' | 'SELL_CE' | 'SELL_PE' | 'BUY' | 'SELL' | 'STRONG_BUY' | 'STRONG_SELL'
  strike: number
  confidence: number
  entry_price: number
  target: number
  stop_loss: number
  reasoning: string
  hedge_suggestion?: string
  // Elite signal fields
  instrument?: string
  quality_grade?: string
  risk_reward?: number
  technical_score?: number
  momentum_score?: number
  confluence_score?: number
  market_structure?: string
  volatility_regime?: string
  key_resistance?: number[]
  key_support?: number[]
}

export interface OptionChainData {
  [key: string]: {
    symbol: string
    strike: number
    expiry: string
    option_type: 'CE' | 'PE'
    ltp: number
    bid: number
    ask: number
    volume: number
    oi: number
    oi_change: number
    iv: number
    delta: number
    gamma: number
    theta: number
    vega: number
  }
}

export interface SignalEngineStatus {
  status: 'healthy' | 'unhealthy'
  engine_running: boolean
  timestamp: string
  service?: string
  version?: string
  instruments?: string[]
  market_hours?: boolean
  cached_signals?: number
}

// API Configuration
const API_BASE_URL = 'http://localhost:8000'  // Main Dhan Backend
const SIGNAL_ENGINE_URL = 'http://localhost:4090'  // Elite Signal Engine
const WS_URL = 'ws://localhost:8000/ws/live-data'

class SignalEngineAPI {
  public wsConnection: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 5000
  private listeners: Set<(data: any) => void> = new Set()

  // REST API Methods - Signal Engine (Port 4090)
  async getHealthStatus(): Promise<SignalEngineStatus> {
    try {
      // Try Signal Engine first
      const response = await fetch(`${SIGNAL_ENGINE_URL}/health`, { 
        signal: AbortSignal.timeout(5000) 
      })
      if (response.ok) {
        const data = await response.json()
        return {
          status: data.status === 'healthy' ? 'healthy' : 'unhealthy',
          engine_running: true,
          timestamp: data.timestamp,
          service: data.service,
          version: data.version,
          instruments: data.instruments,
          market_hours: data.market_hours,
          cached_signals: data.cached_signals
        }
      }
      throw new Error('Signal Engine not responding')
    } catch (error) {
      // Fallback to main API
      try {
        const response = await fetch(`${API_BASE_URL}/health`)
        if (!response.ok) throw new Error('API not available')
        return await response.json()
      } catch {
        throw new Error(`Failed to get health status: ${error}`)
      }
    }
  }

  // Get Elite Signals from Signal Engine
  async getEliteSignals(instrument?: string): Promise<{ signals: TradingSignal[] }> {
    try {
      const url = instrument 
        ? `${SIGNAL_ENGINE_URL}/api/signals/${instrument}`
        : `${SIGNAL_ENGINE_URL}/api/signals`
      const response = await fetch(url, { signal: AbortSignal.timeout(5000) })
      if (!response.ok) throw new Error('Failed to fetch elite signals')
      const data = await response.json()
      return { signals: Array.isArray(data) ? data : data.signals || [] }
    } catch (error) {
      console.warn('Elite signals unavailable, falling back to main API')
      return this.getLatestSignals(10)
    }
  }

  // Get Active Elite Signals
  async getActiveEliteSignals(): Promise<{ signals: TradingSignal[] }> {
    try {
      const response = await fetch(`${SIGNAL_ENGINE_URL}/api/signals/active/all`, {
        signal: AbortSignal.timeout(5000)
      })
      if (!response.ok) throw new Error('Failed to fetch active signals')
      const data = await response.json()
      return { signals: data.signals || [] }
    } catch (error) {
      console.warn('Active signals unavailable:', error)
      return { signals: [] }
    }
  }

  // Force generate new signals
  async generateSignals(): Promise<{ status: string; signals: any }> {
    try {
      const response = await fetch(`${SIGNAL_ENGINE_URL}/api/generate`, {
        method: 'POST',
        signal: AbortSignal.timeout(10000)
      })
      if (!response.ok) throw new Error('Failed to generate signals')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to generate signals: ${error}`)
    }
  }

  // Get Signal Engine performance
  async getSignalPerformance(days: number = 30): Promise<any> {
    try {
      const response = await fetch(`${SIGNAL_ENGINE_URL}/api/performance?days=${days}`, {
        signal: AbortSignal.timeout(5000)
      })
      if (!response.ok) throw new Error('Failed to fetch performance')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get performance: ${error}`)
    }
  }

  // Evaluation mode endpoints
  async enableEvaluationMode(): Promise<any> {
    try {
      const response = await fetch(`${SIGNAL_ENGINE_URL}/evaluation/enable`, {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Failed to enable evaluation mode')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to enable evaluation: ${error}`)
    }
  }

  async getEvaluationStatus(): Promise<any> {
    try {
      const response = await fetch(`${SIGNAL_ENGINE_URL}/evaluation/status`)
      if (!response.ok) throw new Error('Failed to get evaluation status')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get evaluation status: ${error}`)
    }
  }

  async getMarketSummary(): Promise<MarketData> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/market/summary`)
      if (!response.ok) throw new Error('Failed to fetch market summary')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get market summary: ${error}`)
    }
  }

  async getLatestSignals(limit: number = 10): Promise<{ signals: TradingSignal[] }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/signals/latest?limit=${limit}`)
      if (!response.ok) throw new Error('Failed to fetch signals')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get signals: ${error}`)
    }
  }

  async getOptionChain(): Promise<{ option_chain: OptionChainData }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/options/chain`)
      if (!response.ok) throw new Error('Failed to fetch option chain')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get option chain: ${error}`)
    }
  }

  async getNiftyData(): Promise<{ price: number; timestamp: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/market/nifty`)
      if (!response.ok) throw new Error('Failed to fetch Nifty data')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get Nifty data: ${error}`)
    }
  }

  async getPCRData(): Promise<{ pcr: number; total_ce_oi: number; total_pe_oi: number; timestamp: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/analytics/pcr`)
      if (!response.ok) throw new Error('Failed to fetch PCR data')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get PCR data: ${error}`)
    }
  }

  async getMaxPain(): Promise<{ max_pain: number; current_price: number; timestamp: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/analytics/max-pain`)
      if (!response.ok) throw new Error('Failed to fetch max pain')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get max pain: ${error}`)
    }
  }

  async getIVData(): Promise<{ avg_iv: number; iv_percentile: number; timestamp: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/analytics/iv`)
      if (!response.ok) throw new Error('Failed to fetch IV data')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get IV data: ${error}`)
    }
  }

  async getMarketStats(): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/market/stats`)
      if (!response.ok) throw new Error('Failed to fetch market stats')
      return await response.json()
    } catch (error) {
      throw new Error(`Failed to get market stats: ${error}`)
    }
  }

  // WebSocket Methods
  connectWebSocket(): void {
    if (this.wsConnection?.readyState === WebSocket.OPEN) {
      return // Already connected
    }

    try {
      this.wsConnection = new WebSocket(WS_URL)

      this.wsConnection.onopen = () => {
        console.log('Connected to Signal Engine WebSocket')
        this.reconnectAttempts = 0
      }

      this.wsConnection.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.notifyListeners(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.wsConnection.onclose = () => {
        console.log('WebSocket connection closed')
        this.attemptReconnect()
      }

      this.wsConnection.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      this.attemptReconnect()
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      this.connectWebSocket()
    }, this.reconnectDelay * this.reconnectAttempts)
  }

  addListener(callback: (data: any) => void): void {
    this.listeners.add(callback)
  }

  removeListener(callback: (data: any) => void): void {
    this.listeners.delete(callback)
  }

  private notifyListeners(data: any): void {
    this.listeners.forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error('Error in WebSocket listener:', error)
      }
    })
  }

  disconnect(): void {
    if (this.wsConnection) {
      this.wsConnection.close()
      this.wsConnection = null
    }
    this.listeners.clear()
  }
}

// Singleton instance
export const signalEngineAPI = new SignalEngineAPI()

// React Hooks for Signal Engine Integration

export const useSignalEngineStatus = () => {
  const [status, setStatus] = useState<SignalEngineStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const checkStatus = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const healthStatus = await signalEngineAPI.getHealthStatus()
      setStatus(healthStatus)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setStatus(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkStatus()
    const interval = setInterval(checkStatus, 30000) // Check every 30 seconds
    return () => clearInterval(interval)
  }, [checkStatus])

  return { status, loading, error, refresh: checkStatus }
}

export const useRealTimeMarketData = () => {
  const [marketData, setMarketData] = useState<MarketData | null>(null)
  const [signals, setSignals] = useState<TradingSignal[]>([])
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')

  const handleWebSocketMessage = useCallback((data: any) => {
    if (data.type === 'market_update' && data.data) {
      if (data.data.market_summary) {
        setMarketData(data.data.market_summary)
      }
      if (data.data.latest_signals) {
        setSignals(data.data.latest_signals)
      }
      setLastUpdate(new Date())
    }
  }, [])

  useEffect(() => {
    setConnectionStatus('connecting')
    signalEngineAPI.addListener(handleWebSocketMessage)
    signalEngineAPI.connectWebSocket()

    // Set connection status based on WebSocket state
    const checkConnection = () => {
      if (signalEngineAPI.wsConnection?.readyState === WebSocket.OPEN) {
        setConnectionStatus('connected')
      } else {
        setConnectionStatus('disconnected')
      }
    }

    const interval = setInterval(checkConnection, 5000)

    return () => {
      signalEngineAPI.removeListener(handleWebSocketMessage)
      clearInterval(interval)
    }
  }, [handleWebSocketMessage])

  // Fetch initial data
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [marketSummary, latestSignals] = await Promise.all([
          signalEngineAPI.getMarketSummary().catch(() => null),
          signalEngineAPI.getLatestSignals(5).catch(() => ({ signals: [] }))
        ])

        if (marketSummary) setMarketData(marketSummary)
        if (latestSignals) setSignals(latestSignals.signals)
      } catch (error) {
        console.error('Failed to fetch initial data:', error)
      }
    }

    fetchInitialData()
  }, [])

  return {
    marketData,
    signals,
    lastUpdate,
    connectionStatus,
    isConnected: connectionStatus === 'connected'
  }
}

export const useOptionChain = () => {
  const [optionChain, setOptionChain] = useState<OptionChainData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchOptionChain = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await signalEngineAPI.getOptionChain()
      setOptionChain(data.option_chain)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch option chain')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchOptionChain()
    const interval = setInterval(fetchOptionChain, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, [fetchOptionChain])

  return { optionChain, loading, error, refresh: fetchOptionChain }
}

export const useSignalHistory = (hours: number = 24) => {
  const [signals, setSignals] = useState<TradingSignal[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSignalHistory = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`${API_BASE_URL}/api/signals/history?hours=${hours}`)
      if (!response.ok) throw new Error('Failed to fetch signal history')
      const data = await response.json()
      setSignals(data.signals)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch signal history')
    } finally {
      setLoading(false)
    }
  }, [hours])

  useEffect(() => {
    fetchSignalHistory()
  }, [fetchSignalHistory])

  return { signals, loading, error, refresh: fetchSignalHistory }
}

// Hook for Elite Signal Engine signals
export const useEliteSignals = (instrument?: string) => {
  const [signals, setSignals] = useState<TradingSignal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchEliteSignals = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await signalEngineAPI.getEliteSignals(instrument)
      setSignals(data.signals)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch elite signals')
    } finally {
      setLoading(false)
    }
  }, [instrument])

  useEffect(() => {
    fetchEliteSignals()
    const interval = setInterval(fetchEliteSignals, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [fetchEliteSignals])

  return { signals, loading, error, refresh: fetchEliteSignals }
}

// Hook for Signal Engine performance metrics
export const useSignalPerformance = (days: number = 30) => {
  const [performance, setPerformance] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPerformance = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await signalEngineAPI.getSignalPerformance(days)
      setPerformance(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch performance')
    } finally {
      setLoading(false)
    }
  }, [days])

  useEffect(() => {
    fetchPerformance()
    const interval = setInterval(fetchPerformance, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [fetchPerformance])

  return { performance, loading, error, refresh: fetchPerformance }
}

// Hook for evaluation mode status
export const useEvaluationMode = () => {
  const [evaluationStatus, setEvaluationStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await signalEngineAPI.getEvaluationStatus()
      setEvaluationStatus(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch evaluation status')
    } finally {
      setLoading(false)
    }
  }, [])

  const enableEvaluation = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      await signalEngineAPI.enableEvaluationMode()
      await fetchStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to enable evaluation')
      throw err
    } finally {
      setLoading(false)
    }
  }, [fetchStatus])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  return { evaluationStatus, loading, error, enableEvaluation, refresh: fetchStatus }
}

// Utility functions
export const formatSignalType = (signalType: string): string => {
  switch (signalType) {
    case 'BUY_CE': return 'Buy Call'
    case 'BUY_PE': return 'Buy Put'
    case 'SELL_CE': return 'Sell Call'
    case 'SELL_PE': return 'Sell Put'
    case 'BUY': return 'Buy'
    case 'SELL': return 'Sell'
    case 'STRONG_BUY': return '🔥 Strong Buy'
    case 'STRONG_SELL': return '📉 Strong Sell'
    default: return signalType
  }
}

export const getSignalColor = (signalType: string): string => {
  switch (signalType) {
    case 'BUY_CE': return 'text-green-400'
    case 'BUY_PE': return 'text-red-400'
    case 'SELL_CE': return 'text-orange-400'
    case 'SELL_PE': return 'text-purple-400'
    case 'BUY': return 'text-green-500'
    case 'SELL': return 'text-red-500'
    case 'STRONG_BUY': return 'text-green-300 font-bold'
    case 'STRONG_SELL': return 'text-red-300 font-bold'
    default: return 'text-gray-400'
  }
}

export const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 80) return 'text-green-400'
  if (confidence >= 60) return 'text-yellow-400'
  return 'text-red-400'
}

export const getQualityGradeColor = (grade: string): string => {
  switch (grade?.toUpperCase()) {
    case 'A+': return 'text-green-300 bg-green-900/50'
    case 'A': return 'text-green-400 bg-green-900/30'
    case 'B+': return 'text-blue-300 bg-blue-900/50'
    case 'B': return 'text-blue-400 bg-blue-900/30'
    case 'C': return 'text-yellow-400 bg-yellow-900/30'
    default: return 'text-gray-400 bg-gray-900/30'
  }
}

export const getTrendDirection = (trend: string): 'MOMENTUM' | 'SIDEWAYS' | 'BEARISH' => {
  switch (trend.toUpperCase()) {
    case 'BULLISH': return 'MOMENTUM'
    case 'BEARISH': return 'BEARISH'
    default: return 'SIDEWAYS'
  }
}
