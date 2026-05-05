import { useState, useEffect } from 'react'
import { 
  TrendingUp, 
  TrendingDown, 
  RefreshCw,
  AlertCircle,
  Target,
  DollarSign,
  Activity,
  X,
  Clock,
  FileText,
  Layers
} from 'lucide-react'

// Backend API URL
const API_BASE_URL = 'http://localhost:8000'

interface Position {
  id: string
  symbol: string
  exchange: string
  productType: string
  positionType: 'LONG' | 'SHORT'
  quantity: number
  avgPrice: number
  ltp: number
  pnl: number
  pnlPercent: number
  dayPnl: number
  multiplier: number
  securityId?: string
}

interface Order {
  orderId: string
  symbol: string
  exchange: string
  transactionType: 'BUY' | 'SELL'
  productType: string
  orderType: string
  quantity: number
  price: number
  triggerPrice: number
  status: string
  filledQty: number
  remainingQty: number
  createTime: string
  updateTime: string
}

interface PositionSummary {
  totalPositions: number
  totalPnl: number
  totalDayPnl: number
  totalInvestment: number
  longPositions: number
  shortPositions: number
}

type TabType = 'positions' | 'orders'

const PositionsPage = () => {
  const [activeTab, setActiveTab] = useState<TabType>('positions')
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [summary, setSummary] = useState<PositionSummary>({
    totalPositions: 0,
    totalPnl: 0,
    totalDayPnl: 0,
    totalInvestment: 0,
    longPositions: 0,
    shortPositions: 0
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())
  const [positionFilter, setPositionFilter] = useState<'all' | 'long' | 'short'>('all')
  const [orderFilter, setOrderFilter] = useState<'all' | 'pending' | 'traded' | 'cancelled'>('all')

  // Fetch positions from backend (Dhan API)
  const fetchPositions = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch(`${API_BASE_URL}/api/positions`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(10000)
      })

      if (response.ok) {
        const data = await response.json()
        
        // Transform Dhan API response to our Position format
        const rawPositions = data.data || data.positions || []
        const positionsData: Position[] = Array.isArray(rawPositions) ? rawPositions.map((pos: any, idx: number) => ({
          id: pos.securityId || `pos-${idx}`,
          symbol: pos.tradingSymbol || pos.symbol || 'Unknown',
          exchange: pos.exchangeSegment || pos.exchange || 'NSE',
          productType: pos.productType || 'INTRADAY',
          positionType: pos.positionType || (pos.netQty > 0 ? 'LONG' : 'SHORT'),
          quantity: Math.abs(pos.netQty || pos.quantity || 0),
          avgPrice: pos.costPrice || pos.avgPrice || pos.averagePrice || 0,
          ltp: pos.ltp || pos.lastPrice || pos.currentPrice || 0,
          pnl: pos.realizedProfit || pos.pnl || 0,
          pnlPercent: pos.costPrice > 0 
            ? ((pos.ltp - pos.costPrice) / pos.costPrice) * 100 
            : 0,
          dayPnl: pos.dayPnl || pos.unrealizedProfit || 0,
          multiplier: pos.multiplier || 1,
          securityId: pos.securityId
        })) : []

        setPositions(positionsData)

        // Calculate summary
        const totalPnl = positionsData.reduce((sum, p) => sum + p.pnl + p.dayPnl, 0)
        const totalDayPnl = positionsData.reduce((sum, p) => sum + p.dayPnl, 0)
        const totalInvestment = positionsData.reduce((sum, p) => sum + (p.avgPrice * p.quantity * p.multiplier), 0)
        const longPositions = positionsData.filter(p => p.positionType === 'LONG').length
        const shortPositions = positionsData.filter(p => p.positionType === 'SHORT').length

        setSummary({
          totalPositions: positionsData.length,
          totalPnl,
          totalDayPnl,
          totalInvestment,
          longPositions,
          shortPositions
        })
      } else {
        throw new Error('Failed to fetch positions')
      }

      setLastRefresh(new Date())
    } catch (err) {
      console.error('Error fetching positions:', err)
      setError('Unable to fetch positions. Please check if backend is running.')
      
      // Set empty data on error
      setPositions([])
      setSummary({
        totalPositions: 0,
        totalPnl: 0,
        totalDayPnl: 0,
        totalInvestment: 0,
        longPositions: 0,
        shortPositions: 0
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch orders from backend (Dhan API)
  const fetchOrders = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/orders`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(10000)
      })

      if (response.ok) {
        const data = await response.json()
        const rawOrders = data.data || data.orders || data || []
        
        const ordersData: Order[] = Array.isArray(rawOrders) ? rawOrders.map((order: any) => ({
          orderId: order.orderId || order.order_id || '',
          symbol: order.tradingSymbol || order.symbol || 'Unknown',
          exchange: order.exchangeSegment || order.exchange || 'NSE',
          transactionType: order.transactionType || 'BUY',
          productType: order.productType || 'INTRADAY',
          orderType: order.orderType || 'MARKET',
          quantity: order.quantity || 0,
          price: order.price || 0,
          triggerPrice: order.triggerPrice || 0,
          status: order.orderStatus || order.status || 'PENDING',
          filledQty: order.filledQty || 0,
          remainingQty: order.remainingQuantity || (order.quantity - (order.filledQty || 0)),
          createTime: order.createTime || order.created_at || new Date().toISOString(),
          updateTime: order.updateTime || order.updated_at || new Date().toISOString()
        })) : []

        setOrders(ordersData)
      }
    } catch (err) {
      console.error('Error fetching orders:', err)
      setOrders([])
    }
  }

  // Fetch all data
  const fetchAllData = async () => {
    await Promise.all([fetchPositions(), fetchOrders()])
  }

  // Close position
  const closePosition = async (position: Position) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/trading/positions/close`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          securityId: position.securityId,
          symbol: position.symbol,
          exchange: position.exchange,
          quantity: position.quantity,
          positionType: position.positionType
        })
      })

      if (response.ok) {
        // Refresh positions after close
        await fetchPositions()
      } else {
        throw new Error('Failed to close position')
      }
    } catch (err) {
      console.error('Error closing position:', err)
      setError('Failed to close position')
    }
  }

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchAllData()
    const interval = setInterval(fetchAllData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  // Filter positions
  const filteredPositions = positions.filter(pos => {
    if (positionFilter === 'all') return true
    return pos.positionType.toLowerCase() === positionFilter
  })

  // Filter orders
  const filteredOrders = orders.filter(order => {
    if (orderFilter === 'all') return true
    if (orderFilter === 'pending') return ['PENDING', 'TRANSIT', 'PART_TRADED'].includes(order.status)
    if (orderFilter === 'traded') return order.status === 'TRADED'
    if (orderFilter === 'cancelled') return ['CANCELLED', 'REJECTED', 'EXPIRED'].includes(order.status)
    return true
  })

  // Cancel order
  const cancelOrder = async (orderId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/orders/${orderId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
      })
      if (response.ok) {
        await fetchOrders()
      }
    } catch (err) {
      console.error('Error cancelling order:', err)
    }
  }

  // Get order status color
  const getOrderStatusColor = (status: string) => {
    switch (status) {
      case 'TRADED': return 'bg-green-500/20 text-green-400'
      case 'PENDING': case 'TRANSIT': return 'bg-yellow-500/20 text-yellow-400'
      case 'PART_TRADED': return 'bg-blue-500/20 text-blue-400'
      case 'CANCELLED': case 'REJECTED': case 'EXPIRED': return 'bg-red-500/20 text-red-400'
      default: return 'bg-gray-500/20 text-gray-400'
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-xl font-bold text-white">Trading Activity</h1>
          <p className="text-xs text-gray-400">Real-time orders & positions from Dhan</p>
        </div>
        
        <div className="flex items-center space-x-3">
          <span className="text-xs text-gray-500">
            <Clock className="w-3 h-3 inline mr-1" />
            {lastRefresh.toLocaleTimeString()}
          </span>
          
          <button
            onClick={fetchAllData}
            disabled={isLoading}
            className="p-1.5 bg-blue-600 hover:bg-blue-700 rounded transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-4">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <Target className="w-4 h-4 text-blue-400" />
            <div>
              <p className="text-xs text-gray-400">Positions</p>
              <p className="text-lg font-bold text-white">{summary.totalPositions}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <div>
              <p className="text-xs text-gray-400">Long</p>
              <p className="text-lg font-bold text-green-400">{summary.longPositions}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            <div>
              <p className="text-xs text-gray-400">Short</p>
              <p className="text-lg font-bold text-red-400">{summary.shortPositions}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <DollarSign className="w-4 h-4 text-purple-400" />
            <div>
              <p className="text-xs text-gray-400">Investment</p>
              <p className="text-lg font-bold text-white">₹{summary.totalInvestment.toLocaleString()}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <div>
              <p className="text-xs text-gray-400">Day P&L</p>
              <p className={`text-lg font-bold ${summary.totalDayPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {summary.totalDayPnl >= 0 ? '+' : ''}₹{summary.totalDayPnl.toLocaleString()}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            {summary.totalPnl >= 0 ? (
              <TrendingUp className="w-4 h-4 text-green-400" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-400" />
            )}
            <div>
              <p className="text-xs text-gray-400">Total P&L</p>
              <p className={`text-lg font-bold ${summary.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {summary.totalPnl >= 0 ? '+' : ''}₹{summary.totalPnl.toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-4">
          <div className="flex items-center">
            <AlertCircle className="w-4 h-4 text-red-400 mr-2" />
            <span className="text-sm text-red-400">{error}</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center space-x-4 mb-4">
        <button
          onClick={() => setActiveTab('positions')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
            activeTab === 'positions' 
              ? 'bg-blue-600 text-white' 
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Positions ({positions.length})</span>
        </button>
        
        <button
          onClick={() => setActiveTab('orders')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
            activeTab === 'orders' 
              ? 'bg-blue-600 text-white' 
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Orders ({orders.length})</span>
        </button>

        {/* Filter for active tab */}
        {activeTab === 'positions' && (
          <select
            value={positionFilter}
            onChange={(e) => setPositionFilter(e.target.value as 'all' | 'long' | 'short')}
            className="ml-auto bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs"
          >
            <option value="all">All Positions</option>
            <option value="long">Long Only</option>
            <option value="short">Short Only</option>
          </select>
        )}
        
        {activeTab === 'orders' && (
          <select
            value={orderFilter}
            onChange={(e) => setOrderFilter(e.target.value as 'all' | 'pending' | 'traded' | 'cancelled')}
            className="ml-auto bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs"
          >
            <option value="all">All Orders</option>
            <option value="pending">Pending</option>
            <option value="traded">Traded</option>
            <option value="cancelled">Cancelled</option>
          </select>
        )}
      </div>

      {/* Positions Tab */}
      {activeTab === 'positions' && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-400 mx-auto mb-2" />
              <p className="text-sm text-gray-400">Loading positions...</p>
            </div>
          ) : filteredPositions.length === 0 ? (
            <div className="p-8 text-center">
              <Target className="w-8 h-8 text-gray-500 mx-auto mb-2" />
              <p className="text-sm text-gray-400">No open positions</p>
              <p className="text-xs text-gray-500 mt-1">Positions will appear here when you have active trades</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-800/50 border-b border-gray-700/50">
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Symbol</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Type</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Qty</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Avg Price</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">LTP</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">P&L</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">%</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/30">
                  {filteredPositions.map((position) => (
                    <tr key={position.id} className="hover:bg-gray-700/20">
                      <td className="py-2 px-3">
                        <div>
                          <p className="text-white font-medium">{position.symbol}</p>
                          <p className="text-gray-500">{position.exchange} • {position.productType}</p>
                        </div>
                      </td>
                      <td className="py-2 px-3">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                          position.positionType === 'LONG' 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {position.positionType}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-white">{position.quantity}</td>
                      <td className="py-2 px-3 text-gray-300">₹{position.avgPrice.toFixed(2)}</td>
                      <td className="py-2 px-3 text-white font-medium">₹{position.ltp.toFixed(2)}</td>
                      <td className="py-2 px-3">
                        <span className={position.pnl + position.dayPnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                          {position.pnl + position.dayPnl >= 0 ? '+' : ''}₹{(position.pnl + position.dayPnl).toFixed(2)}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <span className={`px-1.5 py-0.5 rounded text-xs ${
                          position.pnlPercent >= 0 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {position.pnlPercent >= 0 ? '+' : ''}{position.pnlPercent.toFixed(2)}%
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <button
                          onClick={() => closePosition(position)}
                          className="p-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded transition-colors"
                          title="Close Position"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Orders Tab */}
      {activeTab === 'orders' && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-400 mx-auto mb-2" />
              <p className="text-sm text-gray-400">Loading orders...</p>
            </div>
          ) : filteredOrders.length === 0 ? (
            <div className="p-8 text-center">
              <FileText className="w-8 h-8 text-gray-500 mx-auto mb-2" />
              <p className="text-sm text-gray-400">No orders today</p>
              <p className="text-xs text-gray-500 mt-1">Orders will appear here when you place trades</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-800/50 border-b border-gray-700/50">
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Time</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Symbol</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Side</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Type</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Qty</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Price</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Filled</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Status</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/30">
                  {filteredOrders.map((order) => (
                    <tr key={order.orderId} className="hover:bg-gray-700/20">
                      <td className="py-2 px-3 text-gray-300">
                        {new Date(order.createTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-2 px-3">
                        <div>
                          <p className="text-white font-medium">{order.symbol}</p>
                          <p className="text-gray-500">{order.exchange} • {order.productType}</p>
                        </div>
                      </td>
                      <td className="py-2 px-3">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                          order.transactionType === 'BUY' 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {order.transactionType}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-gray-300">{order.orderType}</td>
                      <td className="py-2 px-3 text-white">{order.quantity}</td>
                      <td className="py-2 px-3 text-gray-300">
                        {order.price > 0 ? `₹${order.price.toFixed(2)}` : 'MKT'}
                      </td>
                      <td className="py-2 px-3 text-white">
                        {order.filledQty}/{order.quantity}
                      </td>
                      <td className="py-2 px-3">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${getOrderStatusColor(order.status)}`}>
                          {order.status}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        {['PENDING', 'TRANSIT'].includes(order.status) && (
                          <button
                            onClick={() => cancelOrder(order.orderId)}
                            className="p-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded transition-colors"
                            title="Cancel Order"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default PositionsPage
