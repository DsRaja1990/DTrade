import { useEffect, useState } from 'react'
import { Wifi, WifiOff, RefreshCw, AlertTriangle } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'

interface ConnectionStatusProps {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left'
  showDetails?: boolean
}

export const ConnectionStatus = ({ 
  position = 'top-right', 
  showDetails = false 
}: ConnectionStatusProps) => {
  const { connectionState, reconnectAttempt, reconnect, getConnectionStats } = useWebSocket()
  const [showTooltip, setShowTooltip] = useState(false)
  const [stats, setStats] = useState<any>(null)

  useEffect(() => {
    if (showDetails) {
      const interval = setInterval(() => {
        setStats(getConnectionStats())
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [showDetails, getConnectionStats])

  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
  }

  const getStatusColor = () => {
    switch (connectionState) {
      case 'connected':
        return 'bg-green-500 hover:bg-green-600'
      case 'connecting':
        return 'bg-yellow-500 hover:bg-yellow-600 animate-pulse'
      case 'disconnected':
        return 'bg-red-500 hover:bg-red-600'
      default:
        return 'bg-gray-500 hover:bg-gray-600'
    }
  }

  const getStatusIcon = () => {
    switch (connectionState) {
      case 'connected':
        return <Wifi className="w-5 h-5" />
      case 'connecting':
        return <RefreshCw className="w-5 h-5 animate-spin" />
      case 'disconnected':
        return <WifiOff className="w-5 h-5" />
      default:
        return <AlertTriangle className="w-5 h-5" />
    }
  }

  const getStatusText = () => {
    switch (connectionState) {
      case 'connected':
        return 'Connected'
      case 'connecting':
        return `Connecting${reconnectAttempt > 0 ? ` (attempt ${reconnectAttempt})` : '...'}`
      case 'disconnected':
        return reconnectAttempt > 0 ? `Reconnecting (${reconnectAttempt})` : 'Disconnected'
      default:
        return 'Unknown'
    }
  }

  return (
    <div className={`fixed ${positionClasses[position]} z-50`}>
      <div
        className="relative"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <button
          onClick={reconnect}
          className={`${getStatusColor()} text-white rounded-full p-2 shadow-lg transition-all duration-200 transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2`}
          title={getStatusText()}
        >
          {getStatusIcon()}
        </button>

        {/* Tooltip */}
        {showTooltip && (
          <div className="absolute top-full right-0 mt-2 w-64 bg-gray-900 text-white rounded-lg shadow-xl p-3 text-sm z-50">
            <div className="font-semibold mb-2 flex items-center justify-between">
              <span>Connection Status</span>
              {connectionState === 'connected' && (
                <span className="flex items-center text-green-400">
                  <span className="w-2 h-2 bg-green-400 rounded-full mr-1 animate-pulse"></span>
                  Live
                </span>
              )}
            </div>
            
            <div className="space-y-1 text-gray-300">
              <div className="flex justify-between">
                <span>Status:</span>
                <span className="font-medium">{getStatusText()}</span>
              </div>
              
              {reconnectAttempt > 0 && (
                <div className="flex justify-between">
                  <span>Attempts:</span>
                  <span className="font-medium text-yellow-400">{reconnectAttempt}</span>
                </div>
              )}
              
              {showDetails && stats && (
                <>
                  <div className="flex justify-between">
                    <span>Ready State:</span>
                    <span className="font-medium">
                      {stats.readyState === 0 ? 'Connecting' :
                       stats.readyState === 1 ? 'Open' :
                       stats.readyState === 2 ? 'Closing' :
                       stats.readyState === 3 ? 'Closed' : 'Unknown'}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span>URL:</span>
                    <span className="font-mono truncate ml-2">{stats.url?.split('/').pop() || 'N/A'}</span>
                  </div>
                </>
              )}
            </div>

            {connectionState === 'disconnected' && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  reconnect()
                }}
                className="mt-3 w-full bg-blue-600 hover:bg-blue-700 text-white py-1.5 px-3 rounded text-xs font-medium transition-colors"
              >
                Reconnect Now
              </button>
            )}

            <div className="mt-2 pt-2 border-t border-gray-700 text-xs text-gray-400">
              <div className="flex items-center justify-between">
                <span>Auto-reconnect:</span>
                <span className="text-green-400 font-medium">✓ Enabled</span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span>Heartbeat:</span>
                <span className="text-green-400 font-medium">✓ Active</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ConnectionStatus
