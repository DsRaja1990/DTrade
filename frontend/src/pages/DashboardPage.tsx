import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  Target,
  Zap,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Wifi,
  WifiOff
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useTradingStore } from '../store/tradingStore'

// Service Configuration
const SERVICES = {
  AI_SCALPING: { port: 4002, name: 'AI Scalping', type: 'index' },
  AI_HEDGER: { port: 4003, name: 'AI Hedger', type: 'options' },
  ELITE_EQUITY: { port: 5080, name: 'Elite Equity', type: 'equity' },
  GEMINI_SIGNAL: { port: 4080, name: 'Gemini Signal', type: 'signal' }
}

interface ServiceHealth {
  status: 'healthy' | 'unhealthy' | 'unknown'
  uptime?: string
  version?: string
}

interface Signal {
  id: string
  symbol: string
  action: 'BUY' | 'SELL'
  price: number
  target: number
  stopLoss: number
  confidence: number
  source: string
  timestamp: string
  instrument: 'INDEX' | 'EQUITY' | 'OPTIONS'
}

const DashboardPage = () => {
  const { dhanCredentials } = useAuthStore()
  const { 
    refreshOrders, 
    refreshPositions, 
    refreshFunds,
    positions,
    availableFunds
  } = useTradingStore()

  const [currentTime, setCurrentTime] = useState(new Date())
  const [serviceHealth, setServiceHealth] = useState<Record<string, ServiceHealth>>({})
  const [signals, setSignals] = useState<Signal[]>([])
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Check if market is open (IST 9:15 AM to 3:30 PM)
  const isMarketOpen = () => {
    const now = new Date()
    const hours = now.getHours()
    const minutes = now.getMinutes()
    const time = hours * 60 + minutes
    const marketOpen = 9 * 60 + 15  // 9:15 AM
    const marketClose = 15 * 60 + 30 // 3:30 PM
    const day = now.getDay()
    return day >= 1 && day <= 5 && time >= marketOpen && time <= marketClose
  }

  // Fetch service health
  const fetchServiceHealth = async () => {
    const healthData: Record<string, ServiceHealth> = {}
    
    for (const [key, service] of Object.entries(SERVICES)) {
      try {
        const response = await fetch(`http://localhost:${service.port}/health`, {
          method: 'GET',
          signal: AbortSignal.timeout(3000)
        })
        if (response.ok) {
          const data = await response.json()
          healthData[key] = {
            status: 'healthy',
            uptime: data.uptime,
            version: data.version
          }
        } else {
          healthData[key] = { status: 'unhealthy' }
        }
      } catch {
        healthData[key] = { status: 'unknown' }
      }
    }
    
    setServiceHealth(healthData)
  }

  // Fetch live signals from all services
  const fetchSignals = async () => {
    const allSignals: Signal[] = []
    
    // Try fetching from backend aggregated signals endpoint first
    try {
      const response = await fetch('http://localhost:8000/api/signals/latest?limit=20', {
        signal: AbortSignal.timeout(5000)
      })
      if (response.ok) {
        const data = await response.json()
        if (data.signals && Array.isArray(data.signals)) {
          allSignals.push(...data.signals.map((s: any) => ({
            ...s,
            instrument: s.instrument || 'INDEX' as const
          })))
        }
      }
    } catch { /* Backend aggregation failed, try individual services */ }

    // If no signals from backend, try individual services
    if (allSignals.length === 0) {
      // Try Signal Engine Service (new world-class service)
      try {
        const response = await fetch('http://localhost:4090/api/signals', {
          signal: AbortSignal.timeout(3000)
        })
        if (response.ok) {
          const data = await response.json()
          if (data.signals && Array.isArray(data.signals)) {
            allSignals.push(...data.signals.map((s: any) => ({
              ...s,
              source: s.source || 'SignalEngine',
              instrument: s.instrument || 'INDEX' as const
            })))
          }
        }
      } catch { /* Service offline */ }

      // Try fetching from Gemini Signal Service
      try {
        const response = await fetch('http://localhost:4080/api/signals/latest', {
          signal: AbortSignal.timeout(3000)
        })
        if (response.ok) {
          const data = await response.json()
          if (data.signals && Array.isArray(data.signals)) {
            allSignals.push(...data.signals.map((s: any) => ({
              ...s,
              source: 'Gemini',
              instrument: 'INDEX' as const
            })))
          }
        }
      } catch { /* Service offline */ }

      // Try fetching from AI Scalping Service
      try {
        const response = await fetch('http://localhost:4002/api/signals', {
          signal: AbortSignal.timeout(3000)
        })
        if (response.ok) {
          const data = await response.json()
          if (data.signals && Array.isArray(data.signals)) {
            allSignals.push(...data.signals.map((s: any) => ({
              ...s,
              source: 'AI Scalping',
              instrument: 'INDEX' as const
            })))
          }
        }
      } catch { /* Service offline */ }

      // Try fetching from AI Hedger Service
      try {
        const response = await fetch('http://localhost:4003/api/signals', {
          signal: AbortSignal.timeout(3000)
        })
        if (response.ok) {
          const data = await response.json()
          if (data.signals && Array.isArray(data.signals)) {
            allSignals.push(...data.signals.map((s: any) => ({
              ...s,
              source: 'AI Hedger',
              instrument: 'OPTIONS' as const
            })))
          }
        }
      } catch { /* Service offline */ }

      // Try fetching from Elite Equity Service
      try {
        const response = await fetch('http://localhost:5080/api/signals', {
          signal: AbortSignal.timeout(3000)
        })
        if (response.ok) {
          const data = await response.json()
          if (data.signals && Array.isArray(data.signals)) {
            allSignals.push(...data.signals.map((s: any) => ({
              ...s,
              source: 'Elite Equity',
              instrument: 'EQUITY' as const
            })))
          }
        }
      } catch { /* Service offline */ }
    }

    // Sort by timestamp (newest first)
    allSignals.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    setSignals(allSignals.slice(0, 10)) // Keep top 10
  }

  // Initialize trading data
  useEffect(() => {
    if (dhanCredentials) {
      refreshOrders()
      refreshPositions()
      refreshFunds()
    }
  }, [dhanCredentials, refreshOrders, refreshPositions, refreshFunds])

  // Real-time clock and data refresh
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    
    // Initial fetch
    fetchServiceHealth()
    fetchSignals()
    
    // Refresh every 10 seconds
    const dataTimer = setInterval(() => {
      fetchServiceHealth()
      fetchSignals()
    }, 10000)
    
    return () => {
      clearInterval(timer)
      clearInterval(dataTimer)
    }
  }, [])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await Promise.all([fetchServiceHealth(), fetchSignals()])
    if (dhanCredentials) {
      refreshOrders()
      refreshPositions()
      refreshFunds()
    }
    setIsRefreshing(false)
  }

  // Calculate metrics (with safe array checks)
  const portfolioValue = availableFunds || 0
  const positionsArray = Array.isArray(positions) ? positions : []
  const dayPnL = positionsArray.reduce((sum, pos) => sum + (pos.unrealizedProfit || 0), 0)
  const openPositionsCount = positionsArray.length
  const healthyServices = Object.values(serviceHealth).filter(h => h.status === 'healthy').length
  const totalServices = Object.keys(SERVICES).length

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Compact Header */}
      <div className="bg-gray-800/50 border-b border-gray-700/50 px-4 py-2">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <h1 className="text-lg font-bold text-white">Trading Dashboard</h1>
            
            {/* Clock */}
            <div className="flex items-center space-x-2 text-sm bg-gray-800 rounded px-2 py-1">
              <Clock className="w-3 h-3 text-cyan-400" />
              <span className="text-cyan-400 font-mono text-xs">
                {currentTime.toLocaleTimeString('en-IN', { hour12: false })}
              </span>
            </div>
            
            {/* Market Status */}
            <div className={`flex items-center space-x-1 px-2 py-1 rounded text-xs ${
              isMarketOpen() ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${isMarketOpen() ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
              <span>{isMarketOpen() ? 'MARKET OPEN' : 'MARKET CLOSED'}</span>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Services Status */}
            <div className="flex items-center space-x-1 text-xs">
              {healthyServices === totalServices ? (
                <Wifi className="w-3 h-3 text-green-400" />
              ) : (
                <WifiOff className="w-3 h-3 text-yellow-400" />
              )}
              <span className="text-gray-400">{healthyServices}/{totalServices} Services</span>
            </div>
            
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
            >
              <RefreshCw className={`w-4 h-4 text-gray-400 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Compact Metrics Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Portfolio Value */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400">Portfolio</p>
                <p className="text-lg font-bold text-white">₹{portfolioValue.toLocaleString()}</p>
              </div>
              <DollarSign className="w-5 h-5 text-green-400" />
            </div>
          </div>
          
          {/* Day P&L */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400">Day P&L</p>
                <p className={`text-lg font-bold ${dayPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {dayPnL >= 0 ? '+' : ''}₹{Math.abs(dayPnL).toLocaleString()}
                </p>
              </div>
              {dayPnL >= 0 ? (
                <TrendingUp className="w-5 h-5 text-green-400" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-400" />
              )}
            </div>
          </div>
          
          {/* Open Positions */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400">Positions</p>
                <p className="text-lg font-bold text-white">{openPositionsCount}</p>
              </div>
              <Target className="w-5 h-5 text-purple-400" />
            </div>
          </div>
          
          {/* Active Signals */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400">Signals</p>
                <p className="text-lg font-bold text-cyan-400">{signals.length}</p>
              </div>
              <Zap className="w-5 h-5 text-yellow-400" />
            </div>
          </div>
        </div>

        {/* Services Status Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(SERVICES).map(([key, service]) => {
            const health = serviceHealth[key]
            return (
              <div key={key} className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-gray-300">{service.name}</span>
                  <div className={`w-2 h-2 rounded-full ${
                    health?.status === 'healthy' ? 'bg-green-400 animate-pulse' :
                    health?.status === 'unhealthy' ? 'bg-red-400' : 'bg-gray-500'
                  }`} />
                </div>
                <div className="flex items-center justify-between">
                  <span className={`text-xs ${
                    health?.status === 'healthy' ? 'text-green-400' :
                    health?.status === 'unhealthy' ? 'text-red-400' : 'text-gray-500'
                  }`}>
                    {health?.status === 'healthy' ? 'Online' : 
                     health?.status === 'unhealthy' ? 'Error' : 'Offline'}
                  </span>
                  <span className="text-xs text-gray-500">:{service.port}</span>
                </div>
              </div>
            )
          })}
        </div>

        {/* Live Signals Section */}
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700/50">
            <div className="flex items-center space-x-2">
              <Zap className="w-4 h-4 text-yellow-400" />
              <h2 className="text-sm font-semibold text-white">Live Trading Signals</h2>
            </div>
            <span className="text-xs text-gray-400">
              All Instruments • Auto-refresh 10s
            </span>
          </div>
          
          {signals.length === 0 ? (
            <div className="p-8 text-center">
              <div className="flex items-center justify-center space-x-2 mb-2">
                {Object.values(serviceHealth).some(h => h.status === 'healthy') ? (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    <span className="text-sm text-gray-300">Services Active - Awaiting Signals</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-5 h-5 text-orange-400" />
                    <span className="text-sm text-gray-300">No Services Connected</span>
                  </>
                )}
              </div>
              <p className="text-xs text-gray-500">Signals appear when trading opportunities are detected</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-700/50">
              {signals.map((signal) => (
                <div key={signal.id} className="px-4 py-3 hover:bg-gray-700/20 transition-colors">
                  <div className="flex items-center justify-between">
                    {/* Left: Symbol & Action */}
                    <div className="flex items-center space-x-3">
                      <div className={`flex items-center space-x-1 px-2 py-1 rounded text-xs font-bold ${
                        signal.action === 'BUY' 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {signal.action === 'BUY' ? (
                          <ArrowUpRight className="w-3 h-3" />
                        ) : (
                          <ArrowDownRight className="w-3 h-3" />
                        )}
                        <span>{signal.action}</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">{signal.symbol}</p>
                        <p className="text-xs text-gray-500">{signal.source} • {signal.instrument}</p>
                      </div>
                    </div>
                    
                    {/* Center: Prices */}
                    <div className="flex items-center space-x-4 text-xs">
                      <div className="text-center">
                        <p className="text-gray-400">Entry</p>
                        <p className="text-white font-medium">₹{signal.price?.toFixed(2) || '-'}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-400">Target</p>
                        <p className="text-green-400 font-medium">₹{signal.target?.toFixed(2) || '-'}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-400">SL</p>
                        <p className="text-red-400 font-medium">₹{signal.stopLoss?.toFixed(2) || '-'}</p>
                      </div>
                    </div>
                    
                    {/* Right: Confidence & Time */}
                    <div className="flex items-center space-x-3">
                      <div className={`px-2 py-1 rounded text-xs font-medium ${
                        signal.confidence >= 80 ? 'bg-green-500/20 text-green-400' :
                        signal.confidence >= 60 ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {signal.confidence}%
                      </div>
                      <span className="text-xs text-gray-500">
                        {new Date(signal.timestamp).toLocaleTimeString('en-IN', { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-3 gap-3">
          <Link 
            to="/strategies" 
            className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 rounded-lg p-4 text-center transition-all"
          >
            <Activity className="w-6 h-6 mx-auto mb-2" />
            <span className="text-sm font-medium">Strategies</span>
          </Link>
          <Link 
            to="/signals" 
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 rounded-lg p-4 text-center transition-all"
          >
            <Zap className="w-6 h-6 mx-auto mb-2" />
            <span className="text-sm font-medium">Signal Analytics</span>
          </Link>
          <Link 
            to="/positions" 
            className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg p-4 text-center transition-all"
          >
            <Target className="w-6 h-6 mx-auto mb-2" />
            <span className="text-sm font-medium">Positions</span>
          </Link>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
