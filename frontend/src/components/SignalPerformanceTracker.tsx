import React, { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Target, AlertTriangle } from 'lucide-react'
import { cn } from '../utils/cn'

interface SignalPerformance {
  signal_id: number
  signal_type: string
  entry_price: number
  current_price: number
  target: number
  stop_loss: number
  pnl: number
  pnl_percentage: number
  status: 'ACTIVE' | 'HIT_TARGET' | 'HIT_STOP' | 'EXPIRED'
  created_at: string
  updated_at: string
}

interface SignalStats {
  total_signals: number
  active_signals: number
  hit_targets: number
  hit_stops: number
  win_rate: number
  avg_pnl: number
  total_pnl: number
}

const SignalPerformanceTracker: React.FC = () => {
  const [performanceData, setPerformanceData] = useState<SignalPerformance[]>([])
  const [stats, setStats] = useState<SignalStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchPerformanceData = async () => {
      try {
        const [performanceResponse, statsResponse] = await Promise.all([
          fetch('http://localhost:8000/api/signals/performance'),
          fetch('http://localhost:8000/api/signals/stats')
        ])

        if (!performanceResponse.ok || !statsResponse.ok) {
          throw new Error('Failed to fetch performance data')
        }

        const performanceData = await performanceResponse.json()
        const statsData = await statsResponse.json()

        setPerformanceData(performanceData.performances || [])
        setStats(statsData.stats || null)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
        console.error('Error fetching performance data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchPerformanceData()
    const interval = setInterval(fetchPerformanceData, 5000) // Update every 5 seconds

    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'HIT_TARGET':
        return 'text-green-400'
      case 'HIT_STOP':
        return 'text-red-400'
      case 'ACTIVE':
        return 'text-blue-400'
      case 'EXPIRED':
        return 'text-gray-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'HIT_TARGET':
        return <Target className="h-4 w-4 text-green-400" />
      case 'HIT_STOP':
        return <AlertTriangle className="h-4 w-4 text-red-400" />
      case 'ACTIVE':
        return <TrendingUp className="h-4 w-4 text-blue-400" />
      case 'EXPIRED':
        return <TrendingDown className="h-4 w-4 text-gray-400" />
      default:
        return <TrendingUp className="h-4 w-4 text-gray-400" />
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-1/3"></div>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-4 bg-gray-700 rounded w-full"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="text-red-400 flex items-center space-x-2">
          <AlertTriangle className="h-5 w-5" />
          <span>Error loading performance data: {error}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Performance Stats */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Win Rate</p>
                <p className="text-2xl font-bold text-green-400">{stats.win_rate.toFixed(1)}%</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-400" />
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Total P&L</p>
                <p className={cn(
                  "text-2xl font-bold",
                  stats.total_pnl >= 0 ? "text-green-400" : "text-red-400"
                )}>
                  ₹{stats.total_pnl.toFixed(2)}
                </p>
              </div>
              {stats.total_pnl >= 0 ? (
                <TrendingUp className="h-8 w-8 text-green-400" />
              ) : (
                <TrendingDown className="h-8 w-8 text-red-400" />
              )}
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Active Signals</p>
                <p className="text-2xl font-bold text-blue-400">{stats.active_signals}</p>
              </div>
              <Target className="h-8 w-8 text-blue-400" />
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Avg P&L</p>
                <p className={cn(
                  "text-2xl font-bold",
                  stats.avg_pnl >= 0 ? "text-green-400" : "text-red-400"
                )}>
                  ₹{stats.avg_pnl.toFixed(2)}
                </p>
              </div>
              <AlertTriangle className="h-8 w-8 text-yellow-400" />
            </div>
          </div>
        </div>
      )}

      {/* Performance Table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-6 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Signal Performance Tracking</h3>
        </div>
        <div className="p-6">
          {performanceData.length === 0 ? (
            <p className="text-gray-400 text-center py-8">No performance data available</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-2 px-4 text-sm font-medium text-gray-400">Signal ID</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-gray-400">Type</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-gray-400">Entry</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-gray-400">Current</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-gray-400">Target</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-gray-400">P&L</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-gray-400">Status</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-gray-400">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {performanceData.map((performance) => (
                    <tr key={performance.signal_id} className="border-b border-gray-700/50">
                      <td className="py-3 px-4 text-sm text-white">{performance.signal_id}</td>
                      <td className="py-3 px-4 text-sm text-white">{performance.signal_type}</td>
                      <td className="py-3 px-4 text-sm text-white">₹{performance.entry_price.toFixed(2)}</td>
                      <td className="py-3 px-4 text-sm text-white">₹{performance.current_price.toFixed(2)}</td>
                      <td className="py-3 px-4 text-sm text-white">₹{performance.target.toFixed(2)}</td>
                      <td className={cn(
                        "py-3 px-4 text-sm font-medium",
                        performance.pnl >= 0 ? "text-green-400" : "text-red-400"
                      )}>
                        ₹{performance.pnl.toFixed(2)} ({performance.pnl_percentage.toFixed(1)}%)
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(performance.status)}
                          <span className={cn("text-sm", getStatusColor(performance.status))}>
                            {performance.status.replace('_', ' ')}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-400">
                        {new Date(performance.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SignalPerformanceTracker
