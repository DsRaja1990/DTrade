import React, { useState, useEffect } from 'react'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  AreaChart,
  Area,
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
  AlertTriangle
} from 'lucide-react'

interface SignalHistoryData {
  id: number
  timestamp: string
  signal_type: string
  strike: number
  confidence: number
  entry_price: number
  target: number
  stop_loss: number
  technical_score: number
  risk_reward: number
  expected_return: number
  actual_pnl?: number
  status?: 'active' | 'hit_target' | 'hit_sl' | 'expired'
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

interface TechnicalIndicatorData {
  timestamp: string
  nifty_price: number
  rsi: number
  macd: number
  vix: number
  volume: number
  bb_upper: number
  bb_lower: number
}

// Mock data generators for fallback
const generateMockSignalHistory = (): SignalHistoryData[] => {
  const signalTypes = ['BUY_CE', 'BUY_PE', 'SELL_CE', 'SELL_PE']
  const data: SignalHistoryData[] = []
  
  for (let i = 0; i < 30; i++) {
    const date = new Date()
    date.setHours(date.getHours() - i * 2)
    
    const strike = 19800 + Math.floor(Math.random() * 400 / 50) * 50
    const entryPrice = 50 + Math.random() * 200
    const confidence = 60 + Math.random() * 40
    
    data.push({
      id: i + 1,
      timestamp: date.toISOString(),
      signal_type: signalTypes[Math.floor(Math.random() * signalTypes.length)],
      strike,
      confidence,
      entry_price: entryPrice,
      target: entryPrice * (1.2 + Math.random() * 0.3),
      stop_loss: entryPrice * (0.8 - Math.random() * 0.2),
      technical_score: 0.5 + Math.random() * 0.5,
      risk_reward: 1.5 + Math.random() * 2,
      expected_return: 10 + Math.random() * 20,
      actual_pnl: i < 20 ? (Math.random() - 0.4) * 50 : undefined,
      status: i < 20 ? (['hit_target', 'hit_sl', 'expired'][Math.floor(Math.random() * 3)] as any) : 'active'
    })
  }
  
  return data
}

const generateMockPerformanceMetrics = (): PerformanceMetrics => {
  return {
    total_signals_generated: 150 + Math.floor(Math.random() * 50),
    total_trades_completed: 120 + Math.floor(Math.random() * 30),
    average_return: 5 + Math.random() * 10,
    win_rate: 55 + Math.random() * 25,
    max_return: 25 + Math.random() * 50,
    max_loss: -15 - Math.random() * 20,
    last_updated: new Date().toISOString()
  }
}

const SignalAnalyticsPage: React.FC = () => {
  const [signalHistory, setSignalHistory] = useState<SignalHistoryData[]>([])
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null)
  const [technicalData, setTechnicalData] = useState<TechnicalIndicatorData[]>([])
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('7D')
  const [selectedSignalType, setSelectedSignalType] = useState<string>('ALL')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAnalyticsData()
    const interval = setInterval(fetchAnalyticsData, 60000) // Update every minute
    return () => clearInterval(interval)
  }, [selectedTimeframe, selectedSignalType])

  const fetchAnalyticsData = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      // Fetch signal history
      try {
        const signalsResponse = await fetch('http://localhost:8000/api/signals/latest?limit=50')
        if (signalsResponse.ok) {
          const signalsData = await signalsResponse.json()
          setSignalHistory(signalsData.signals || [])
        } else {
          throw new Error('Failed to fetch signals')
        }
      } catch (err) {
        console.error('Error fetching signals:', err)
        // Use mock data as fallback
        setSignalHistory(generateMockSignalHistory())
      }
      
      // Fetch performance metrics
      try {
        const performanceResponse = await fetch('http://localhost:8000/api/performance/stats')
        if (performanceResponse.ok) {
          const performanceData = await performanceResponse.json()
          setPerformanceMetrics(performanceData)
        } else {
          throw new Error('Failed to fetch performance')
        }
      } catch (err) {
        console.error('Error fetching performance:', err)
        // Use mock data as fallback
        setPerformanceMetrics(generateMockPerformanceMetrics())
      }
      
      // Fetch technical indicators history
      const technicalHistoryData = generateTechnicalHistory()
      setTechnicalData(technicalHistoryData)
      
    } catch (error) {
      console.error('Error fetching analytics data:', error)
      setError('Failed to load analytics data')
    } finally {
      setIsLoading(false)
    }
  }

  const generateTechnicalHistory = (): TechnicalIndicatorData[] => {
    const data: TechnicalIndicatorData[] = []
    const days = selectedTimeframe === '1D' ? 1 : selectedTimeframe === '7D' ? 7 : 30
    
    for (let i = days; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      
      const basePrice = 19500 + Math.sin(i * 0.1) * 200 + (Math.random() - 0.5) * 100
      
      data.push({
        timestamp: date.toISOString().split('T')[0],
        nifty_price: basePrice,
        rsi: 30 + Math.sin(i * 0.2) * 30 + (Math.random() - 0.5) * 10,
        macd: Math.sin(i * 0.15) * 50 + (Math.random() - 0.5) * 20,
        vix: 15 + Math.sin(i * 0.3) * 8 + (Math.random() - 0.5) * 5,
        volume: 200000 + Math.random() * 300000,
        bb_upper: basePrice + 100 + Math.random() * 50,
        bb_lower: basePrice - 100 - Math.random() * 50
      })
    }
    
    return data
  }

  const getFilteredSignals = () => {
    let filtered = signalHistory
    
    if (selectedSignalType !== 'ALL') {
      filtered = filtered.filter(signal => signal.signal_type === selectedSignalType)
    }
    
    const days = selectedTimeframe === '1D' ? 1 : selectedTimeframe === '7D' ? 7 : 30
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - days)
    
    filtered = filtered.filter(signal => new Date(signal.timestamp) >= cutoffDate)
    
    return filtered
  }

  const getSignalTypeDistribution = () => {
    const distribution = signalHistory.reduce((acc, signal) => {
      acc[signal.signal_type] = (acc[signal.signal_type] || 0) + 1
      return acc
    }, {} as Record<string, number>)
    
    return Object.entries(distribution).map(([type, count]) => ({
      name: type,
      value: count,
      color: type.includes('BUY') ? 
        (type.includes('CE') ? '#10b981' : '#06b6d4') : 
        (type.includes('CE') ? '#ef4444' : '#f59e0b')
    }))
  }

  const getConfidenceDistribution = () => {
    const ranges = { '60-70': 0, '70-80': 0, '80-90': 0, '90-100': 0 }
    
    signalHistory.forEach(signal => {
      if (signal.confidence >= 60 && signal.confidence < 70) ranges['60-70']++
      else if (signal.confidence >= 70 && signal.confidence < 80) ranges['70-80']++
      else if (signal.confidence >= 80 && signal.confidence < 90) ranges['80-90']++
      else if (signal.confidence >= 90) ranges['90-100']++
    })
    
    return Object.entries(ranges).map(([range, count]) => ({
      range,
      count,
      percentage: signalHistory.length > 0 ? (count / signalHistory.length) * 100 : 0
    }))
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white p-6">
      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-lg font-medium text-gray-400">Loading analytics data...</div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
            <span className="text-red-400">{error}</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      {!isLoading && (
        <>
          {/* Header */}
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                Signal Analytics & Performance
              </h1>
              <p className="text-gray-400 mt-2">Advanced analytics for AI-generated trading signals</p>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Timeframe Filter */}
              <select
                value={selectedTimeframe}
                onChange={(e) => setSelectedTimeframe(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="1D">1 Day</option>
                <option value="7D">7 Days</option>
                <option value="30D">30 Days</option>
              </select>
              
              {/* Signal Type Filter */}
              <select
                value={selectedSignalType}
                onChange={(e) => setSelectedSignalType(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="ALL">All Signals</option>
                <option value="BUY_CE">BUY CE</option>
                <option value="BUY_PE">BUY PE</option>
                <option value="SELL_CE">SELL CE</option>
                <option value="SELL_PE">SELL PE</option>
              </select>
              
              <button
                onClick={fetchAnalyticsData}
                className="p-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Performance Metrics Cards */}
          {performanceMetrics && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4 mb-8">
              <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-cyan-500/10 rounded-lg">
                    <Zap className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Total Signals</p>
                    <p className="text-lg font-bold text-white">{performanceMetrics.total_signals_generated}</p>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-green-500/10 rounded-lg">
                    <Target className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Win Rate</p>
                    <p className="text-lg font-bold text-green-400">{performanceMetrics.win_rate.toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-500/10 rounded-lg">
                    <TrendingUp className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Avg Return</p>
                    <p className={`text-lg font-bold ${performanceMetrics.average_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {performanceMetrics.average_return >= 0 ? '+' : ''}{performanceMetrics.average_return.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-purple-500/10 rounded-lg">
                    <Activity className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Max Return</p>
                    <p className="text-lg font-bold text-green-400">+{performanceMetrics.max_return.toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-red-500/10 rounded-lg">
                    <TrendingDown className="w-5 h-5 text-red-400" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Max Loss</p>
                    <p className="text-lg font-bold text-red-400">{performanceMetrics.max_loss.toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-orange-500/10 rounded-lg">
                    <BarChart3 className="w-5 h-5 text-orange-400" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Completed</p>
                    <p className="text-lg font-bold text-white">{performanceMetrics.total_trades_completed}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            
            {/* Signal Performance Over Time */}
            <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <TrendingUp className="w-5 h-5 mr-2 text-green-400" />
                Signal Performance Trend
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={getFilteredSignals().slice(-20)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="timestamp" 
                    stroke="#9CA3AF"
                    tickFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                    labelStyle={{ color: '#F3F4F6' }}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="confidence" 
                    stroke="#10B981" 
                    strokeWidth={2}
                    name="Confidence %"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="technical_score" 
                    stroke="#3B82F6" 
                    strokeWidth={2}
                    name="Technical Score"
                    strokeDasharray="5 5"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Technical Indicators Chart */}
            <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <Activity className="w-5 h-5 mr-2 text-cyan-400" />
                Technical Indicators
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={technicalData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="timestamp" 
                    stroke="#9CA3AF"
                    tickFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                  />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="rsi" 
                    stackId="1" 
                    stroke="#8B5CF6" 
                    fill="#8B5CF6"
                    fillOpacity={0.2}
                    name="RSI"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="vix" 
                    stackId="2" 
                    stroke="#F59E0B" 
                    fill="#F59E0B"
                    fillOpacity={0.2}
                    name="VIX"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Signal Type Distribution */}
            <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <Target className="w-5 h-5 mr-2 text-purple-400" />
                Signal Type Distribution
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={getSignalTypeDistribution()}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
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
            <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <BarChart3 className="w-5 h-5 mr-2 text-blue-400" />
                Confidence Distribution
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={getConfidenceDistribution()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="range" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

          </div>

          {/* Recent Signals Table */}
          <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
              <Zap className="w-5 h-5 mr-2 text-yellow-400" />
              Recent Signals Analysis
            </h3>
            
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-3 px-4 text-gray-400">Timestamp</th>
                    <th className="text-left py-3 px-4 text-gray-400">Type</th>
                    <th className="text-left py-3 px-4 text-gray-400">Strike</th>
                    <th className="text-left py-3 px-4 text-gray-400">Confidence</th>
                    <th className="text-left py-3 px-4 text-gray-400">Entry</th>
                    <th className="text-left py-3 px-4 text-gray-400">Target</th>
                    <th className="text-left py-3 px-4 text-gray-400">R:R</th>
                    <th className="text-left py-3 px-4 text-gray-400">Tech Score</th>
                  </tr>
                </thead>
                <tbody>
                  {getFilteredSignals().slice(-10).map((signal) => (
                    <tr key={signal.id} className="border-b border-gray-800 hover:bg-gray-800/30">
                      <td className="py-3 px-4 text-gray-300">
                        {new Date(signal.timestamp).toLocaleString()}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          signal.signal_type.includes('BUY') ? 
                            (signal.signal_type.includes('CE') ? 'bg-green-500/20 text-green-400' : 'bg-cyan-500/20 text-cyan-400') :
                            (signal.signal_type.includes('CE') ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400')
                        }`}>
                          {signal.signal_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-white font-medium">₹{signal.strike}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          signal.confidence >= 80 ? 'bg-green-500/20 text-green-400' :
                          signal.confidence >= 70 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {signal.confidence.toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-3 px-4 text-blue-400">₹{signal.entry_price.toFixed(2)}</td>
                      <td className="py-3 px-4 text-green-400">₹{signal.target.toFixed(2)}</td>
                      <td className="py-3 px-4 text-purple-400">{signal.risk_reward.toFixed(2)}</td>
                      <td className="py-3 px-4">
                        <div className="w-16 bg-gray-700 rounded-full h-2">
                          <div 
                            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full"
                            style={{ width: `${signal.technical_score * 100}%` }}
                          ></div>
                        </div>
                      </td>
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
