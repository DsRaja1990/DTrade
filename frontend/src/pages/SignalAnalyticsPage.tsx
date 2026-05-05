import React, { useState, useEffect } from 'react'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import { 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  Activity, 
  Target,
  Zap,
  RefreshCw,
  AlertTriangle,
  Wifi,
  WifiOff
} from 'lucide-react'

// Service Configuration - Real Windows Services (excluding Gemini - used internally)
const SIGNAL_SERVICES = {
  SIGNAL_ENGINE: { port: 4090, name: 'Signal Engine', endpoint: '/api/signals/latest' },
  AI_SCALPING: { port: 4002, name: 'AI Scalping', endpoint: '/api/signals' },
  AI_HEDGER: { port: 4003, name: 'AI Hedger', endpoint: '/api/signals' },
  ELITE_EQUITY: { port: 5080, name: 'Elite Equity', endpoint: '/api/signals' }
}

interface SignalHistoryData {
  id: string
  timestamp: string
  signal_type: string
  symbol: string
  strike?: number
  confidence: number
  entry_price: number
  target: number
  stop_loss: number
  technical_score?: number
  risk_reward: number
  expected_return?: number
  actual_pnl?: number
  status?: 'active' | 'hit_target' | 'hit_sl' | 'expired'
  source: string
  instrument: 'INDEX' | 'EQUITY' | 'OPTIONS'
}

interface PerformanceMetrics {
  total_signals_generated: number
  total_trades_completed: number
  average_return: number
  win_rate: number
  max_return: number
  max_loss: number
  last_updated: string
}

interface ServiceStatus {
  name: string
  port: number
  status: 'online' | 'offline' | 'error'
  signalCount: number
}

const SignalAnalyticsPage: React.FC = () => {
  const [signalHistory, setSignalHistory] = useState<SignalHistoryData[]>([])
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null)
  const [serviceStatuses, setServiceStatuses] = useState<ServiceStatus[]>([])
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('7D')
  const [selectedSource, setSelectedSource] = useState<string>('ALL')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

  useEffect(() => {
    fetchAnalyticsData()
    const interval = setInterval(fetchAnalyticsData, 30000) // Update every 30 seconds
    return () => clearInterval(interval)
  }, [selectedTimeframe, selectedSource])

  const fetchAnalyticsData = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const allSignals: SignalHistoryData[] = []
      const statuses: ServiceStatus[] = []
      
      // Fetch signals from all real services
      for (const [key, service] of Object.entries(SIGNAL_SERVICES)) {
        try {
          const response = await fetch(`http://localhost:${service.port}${service.endpoint}`, {
            signal: AbortSignal.timeout(5000)
          })
          
          if (response.ok) {
            const data = await response.json()
            const signals = data.signals || data.data || []
            
            // Normalize and add source info
            const normalizedSignals = signals.map((s: any, idx: number) => ({
              id: s.id || `${key}-${idx}-${Date.now()}`,
              timestamp: s.timestamp || new Date().toISOString(),
              signal_type: s.signal_type || s.action || 'UNKNOWN',
              symbol: s.symbol || s.strike?.toString() || 'N/A',
              strike: s.strike,
              confidence: s.confidence || 0,
              entry_price: s.entry_price || s.price || 0,
              target: s.target || s.target_price || 0,
              stop_loss: s.stop_loss || s.sl || 0,
              technical_score: s.technical_score || s.tech_score || 0.5,
              risk_reward: s.risk_reward || ((s.target - s.entry_price) / (s.entry_price - s.stop_loss)) || 1,
              expected_return: s.expected_return || 0,
              actual_pnl: s.actual_pnl,
              status: s.status || 'active',
              source: service.name,
              instrument: key === 'ELITE_EQUITY' ? 'EQUITY' : key === 'AI_HEDGER' ? 'OPTIONS' : 'INDEX'
            }))
            
            allSignals.push(...normalizedSignals)
            statuses.push({
              name: service.name,
              port: service.port,
              status: 'online',
              signalCount: normalizedSignals.length
            })
          } else {
            statuses.push({
              name: service.name,
              port: service.port,
              status: 'error',
              signalCount: 0
            })
          }
        } catch {
          statuses.push({
            name: service.name,
            port: service.port,
            status: 'offline',
            signalCount: 0
          })
        }
      }
      
      // Sort by timestamp (newest first)
      allSignals.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      
      setSignalHistory(allSignals)
      setServiceStatuses(statuses)
      
      // Calculate performance metrics from real data
      const completedSignals = allSignals.filter(s => s.status !== 'active')
      const winningSignals = completedSignals.filter(s => (s.actual_pnl || 0) > 0)
      
      setPerformanceMetrics({
        total_signals_generated: allSignals.length,
        total_trades_completed: completedSignals.length,
        average_return: completedSignals.length > 0 
          ? completedSignals.reduce((sum, s) => sum + (s.expected_return || 0), 0) / completedSignals.length
          : 0,
        win_rate: completedSignals.length > 0 
          ? (winningSignals.length / completedSignals.length) * 100
          : 0,
        max_return: allSignals.length > 0 
          ? Math.max(...allSignals.map(s => s.expected_return || 0))
          : 0,
        max_loss: allSignals.length > 0 
          ? Math.min(...allSignals.map(s => s.actual_pnl || 0))
          : 0,
        last_updated: new Date().toISOString()
      })
      
      setLastRefresh(new Date())
      
    } catch (error) {
      console.error('Error fetching analytics data:', error)
      setError('Failed to load analytics data from services')
    } finally {
      setIsLoading(false)
    }
  }

  const getFilteredSignals = () => {
    let filtered = signalHistory
    
    if (selectedSource !== 'ALL') {
      filtered = filtered.filter(signal => signal.source === selectedSource)
    }
    
    const days = selectedTimeframe === '1D' ? 1 : selectedTimeframe === '7D' ? 7 : 30
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - days)
    
    filtered = filtered.filter(signal => new Date(signal.timestamp) >= cutoffDate)
    
    return filtered
  }

  const getSignalTypeDistribution = () => {
    const distribution = signalHistory.reduce((acc, signal) => {
      const type = signal.signal_type || 'UNKNOWN'
      acc[type] = (acc[type] || 0) + 1
      return acc
    }, {} as Record<string, number>)
    
    const colors: Record<string, string> = {
      'BUY': '#10b981',
      'BUY_CE': '#10b981',
      'BUY_PE': '#06b6d4',
      'SELL': '#ef4444',
      'SELL_CE': '#ef4444',
      'SELL_PE': '#f59e0b',
      'UNKNOWN': '#6b7280'
    }
    
    return Object.entries(distribution).map(([type, count]) => ({
      name: type,
      value: count,
      color: colors[type] || '#8b5cf6'
    }))
  }

  const getSourceDistribution = () => {
    const distribution = signalHistory.reduce((acc, signal) => {
      acc[signal.source] = (acc[signal.source] || 0) + 1
      return acc
    }, {} as Record<string, number>)
    
    return Object.entries(distribution).map(([source, count]) => ({
      source,
      count,
      percentage: signalHistory.length > 0 ? (count / signalHistory.length) * 100 : 0
    }))
  }

  const getConfidenceDistribution = () => {
    const ranges = { '0-60': 0, '60-70': 0, '70-80': 0, '80-90': 0, '90-100': 0 }
    
    signalHistory.forEach(signal => {
      if (signal.confidence < 60) ranges['0-60']++
      else if (signal.confidence < 70) ranges['60-70']++
      else if (signal.confidence < 80) ranges['70-80']++
      else if (signal.confidence < 90) ranges['80-90']++
      else ranges['90-100']++
    })
    
    return Object.entries(ranges).map(([range, count]) => ({
      range,
      count,
      percentage: signalHistory.length > 0 ? (count / signalHistory.length) * 100 : 0
    }))
  }

  const onlineServices = serviceStatuses.filter(s => s.status === 'online').length

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Signal Analytics</h1>
          <p className="text-sm text-gray-400">Real-time analytics from all trading services</p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Service Status */}
          <div className="flex items-center space-x-2 text-sm">
            {onlineServices > 0 ? (
              <Wifi className="w-4 h-4 text-green-400" />
            ) : (
              <WifiOff className="w-4 h-4 text-red-400" />
            )}
            <span className="text-gray-400">{onlineServices}/{serviceStatuses.length} Services</span>
          </div>
          
          {/* Last Refresh */}
          <span className="text-xs text-gray-500">
            Updated: {lastRefresh.toLocaleTimeString()}
          </span>
          
          {/* Timeframe Filter */}
          <select
            value={selectedTimeframe}
            onChange={(e) => setSelectedTimeframe(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
          >
            <option value="1D">1 Day</option>
            <option value="7D">7 Days</option>
            <option value="30D">30 Days</option>
          </select>
          
          {/* Source Filter */}
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
          >
            <option value="ALL">All Sources</option>
            {Object.values(SIGNAL_SERVICES).map(service => (
              <option key={service.port} value={service.name}>{service.name}</option>
            ))}
          </select>
          
          <button
            onClick={fetchAnalyticsData}
            disabled={isLoading}
            className="p-2 bg-blue-600 hover:bg-blue-700 rounded transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Service Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {serviceStatuses.map((service) => (
          <div key={service.port} className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-300">{service.name}</span>
              <div className={`w-2 h-2 rounded-full ${
                service.status === 'online' ? 'bg-green-400 animate-pulse' :
                service.status === 'error' ? 'bg-yellow-400' : 'bg-red-400'
              }`} />
            </div>
            <div className="flex items-center justify-between">
              <span className={`text-xs ${
                service.status === 'online' ? 'text-green-400' :
                service.status === 'error' ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {service.status === 'online' ? `${service.signalCount} signals` : service.status}
              </span>
              <span className="text-xs text-gray-500">:{service.port}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
            <span className="text-red-400">{error}</span>
          </div>
        </div>
      )}

      {/* No Data State */}
      {!isLoading && signalHistory.length === 0 && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-8 text-center mb-6">
          <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No Signal Data Available</h3>
          <p className="text-sm text-gray-400">
            {onlineServices === 0 
              ? 'No services are currently online. Please start the trading services.'
              : 'Waiting for signals from connected services...'}
          </p>
        </div>
      )}

      {/* Main Content */}
      {signalHistory.length > 0 && (
        <>
          {/* Performance Metrics Cards */}
          {performanceMetrics && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
              <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
                <div className="flex items-center space-x-2">
                  <Zap className="w-4 h-4 text-cyan-400" />
                  <div>
                    <p className="text-xs text-gray-400">Total Signals</p>
                    <p className="text-lg font-bold text-white">{performanceMetrics.total_signals_generated}</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
                <div className="flex items-center space-x-2">
                  <Target className="w-4 h-4 text-green-400" />
                  <div>
                    <p className="text-xs text-gray-400">Win Rate</p>
                    <p className="text-lg font-bold text-green-400">{performanceMetrics.win_rate.toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
                <div className="flex items-center space-x-2">
                  <TrendingUp className="w-4 h-4 text-blue-400" />
                  <div>
                    <p className="text-xs text-gray-400">Avg Return</p>
                    <p className={`text-lg font-bold ${performanceMetrics.average_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {performanceMetrics.average_return >= 0 ? '+' : ''}{performanceMetrics.average_return.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
                <div className="flex items-center space-x-2">
                  <Activity className="w-4 h-4 text-purple-400" />
                  <div>
                    <p className="text-xs text-gray-400">Max Return</p>
                    <p className="text-lg font-bold text-green-400">+{performanceMetrics.max_return.toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
                <div className="flex items-center space-x-2">
                  <TrendingDown className="w-4 h-4 text-red-400" />
                  <div>
                    <p className="text-xs text-gray-400">Max Loss</p>
                    <p className="text-lg font-bold text-red-400">{performanceMetrics.max_loss.toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
                <div className="flex items-center space-x-2">
                  <BarChart3 className="w-4 h-4 text-orange-400" />
                  <div>
                    <p className="text-xs text-gray-400">Completed</p>
                    <p className="text-lg font-bold text-white">{performanceMetrics.total_trades_completed}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            {/* Signal Type Distribution */}
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center">
                <Target className="w-4 h-4 mr-2 text-purple-400" />
                Signal Type Distribution
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={getSignalTypeDistribution()}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={70}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {getSignalTypeDistribution().map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Confidence Distribution */}
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center">
                <BarChart3 className="w-4 h-4 mr-2 text-blue-400" />
                Confidence Distribution
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={getConfidenceDistribution()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="range" stroke="#9CA3AF" fontSize={10} />
                  <YAxis stroke="#9CA3AF" fontSize={10} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '4px',
                      fontSize: '12px'
                    }}
                  />
                  <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Source Distribution */}
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center">
                <Activity className="w-4 h-4 mr-2 text-cyan-400" />
                Signals by Source
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={getSourceDistribution()} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" stroke="#9CA3AF" fontSize={10} />
                  <YAxis type="category" dataKey="source" stroke="#9CA3AF" fontSize={10} width={80} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '4px',
                      fontSize: '12px'
                    }}
                  />
                  <Bar dataKey="count" fill="#10B981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Signal Trend */}
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center">
                <TrendingUp className="w-4 h-4 mr-2 text-green-400" />
                Confidence Trend
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={getFilteredSignals().slice(-20).reverse()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="timestamp" 
                    stroke="#9CA3AF"
                    fontSize={10}
                    tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  />
                  <YAxis stroke="#9CA3AF" fontSize={10} domain={[0, 100]} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '4px',
                      fontSize: '12px'
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="confidence" 
                    stroke="#10B981" 
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recent Signals Table */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-700/50">
              <h3 className="text-sm font-semibold text-white flex items-center">
                <Zap className="w-4 h-4 mr-2 text-yellow-400" />
                Recent Signals ({getFilteredSignals().length})
              </h3>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-800/50">
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Time</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Source</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Type</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Symbol</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Confidence</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Entry</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Target</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">SL</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">R:R</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/30">
                  {getFilteredSignals().slice(0, 15).map((signal) => (
                    <tr key={signal.id} className="hover:bg-gray-700/20">
                      <td className="py-2 px-3 text-gray-300">
                        {new Date(signal.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-2 px-3">
                        <span className="px-1.5 py-0.5 bg-gray-700 rounded text-gray-300">{signal.source}</span>
                      </td>
                      <td className="py-2 px-3">
                        <span className={`px-1.5 py-0.5 rounded font-medium ${
                          signal.signal_type.includes('BUY') ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {signal.signal_type}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-white font-medium">{signal.symbol}</td>
                      <td className="py-2 px-3">
                        <span className={`px-1.5 py-0.5 rounded font-medium ${
                          signal.confidence >= 80 ? 'bg-green-500/20 text-green-400' :
                          signal.confidence >= 60 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {signal.confidence.toFixed(0)}%
                        </span>
                      </td>
                      <td className="py-2 px-3 text-blue-400">₹{signal.entry_price.toFixed(2)}</td>
                      <td className="py-2 px-3 text-green-400">₹{signal.target.toFixed(2)}</td>
                      <td className="py-2 px-3 text-red-400">₹{signal.stop_loss.toFixed(2)}</td>
                      <td className="py-2 px-3 text-purple-400">{signal.risk_reward.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default SignalAnalyticsPage
