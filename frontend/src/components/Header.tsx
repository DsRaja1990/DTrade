import { useState, useEffect } from 'react'
import { 
  Bell, 
  Settings, 
  User, 
  LogOut, 
  Shield,
  Activity,
  TrendingUp,
  DollarSign,
  Wifi,
  WifiOff,
  RefreshCw
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { formatCurrency } from '../utils/formatters'

const API_BASE = 'http://localhost:8000'

interface PortfolioData {
  availableBalance: number
  portfolioValue: number
  dayPnl: number
  totalPnl: number
  holdingsValue: number
}

const Header = () => {
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const [portfolioData, setPortfolioData] = useState<PortfolioData>({
    availableBalance: 0,
    portfolioValue: 0,
    dayPnl: 0,
    totalPnl: 0,
    holdingsValue: 0
  })
  const [isLoading, setIsLoading] = useState(false)
  const { user, logout, dhanCredentials } = useAuthStore()

  const isDhanConnected = !!dhanCredentials?.access_token

  // Fetch portfolio data from Dhan API via backend
  const fetchPortfolioData = async () => {
    try {
      setIsLoading(true)
      
      // Fetch funds, holdings, and positions in parallel
      const [fundsRes, holdingsRes, positionsRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/funds`, { signal: AbortSignal.timeout(5000) }),
        fetch(`${API_BASE}/api/holdings`, { signal: AbortSignal.timeout(5000) }),
        fetch(`${API_BASE}/api/positions`, { signal: AbortSignal.timeout(5000) })
      ])
      
      let availableBalance = 0
      let holdingsValue = 0
      let dayPnl = 0
      let totalPnl = 0
      
      // Parse funds
      if (fundsRes.status === 'fulfilled' && fundsRes.value.ok) {
        const fundsData = await fundsRes.value.json()
        const funds = fundsData.data || fundsData
        availableBalance = funds.availabelBalance || funds.availableBalance || 0
      }
      
      // Parse holdings
      if (holdingsRes.status === 'fulfilled' && holdingsRes.value.ok) {
        const holdingsData = await holdingsRes.value.json()
        const holdings = holdingsData.data || holdingsData || []
        if (Array.isArray(holdings)) {
          holdingsValue = holdings.reduce((sum: number, h: any) => {
            const qty = h.totalQty || h.quantity || 0
            const price = h.avgCostPrice || h.averagePrice || 0
            return sum + (qty * price)
          }, 0)
        }
      }
      
      // Parse positions
      if (positionsRes.status === 'fulfilled' && positionsRes.value.ok) {
        const positionsData = await positionsRes.value.json()
        const positions = positionsData.data || positionsData || []
        if (Array.isArray(positions)) {
          positions.forEach((pos: any) => {
            dayPnl += pos.unrealizedProfit || pos.dayPnl || 0
            totalPnl += (pos.realizedProfit || 0) + (pos.unrealizedProfit || 0)
          })
        }
      }
      
      const portfolioValue = availableBalance + holdingsValue
      
      setPortfolioData({
        availableBalance,
        portfolioValue,
        dayPnl,
        totalPnl,
        holdingsValue
      })
      
    } catch (error) {
      console.error('Error fetching portfolio data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchPortfolioData()
    const interval = setInterval(fetchPortfolioData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const handleLogout = () => {
    logout()
    setShowProfileMenu(false)
  }

  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'text-green-400'
    if (pnl < 0) return 'text-red-400'
    return 'text-gray-400'
  }

  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Portfolio Summary */}
        <div className="flex items-center space-x-8">
          <div className="flex items-center space-x-2">
            <DollarSign className="h-5 w-5 text-blue-400" />
            <div>
              <p className="text-sm text-gray-400">Portfolio Value</p>
              <p className="text-lg font-semibold text-white">
                {isLoading ? '...' : formatCurrency(portfolioData.portfolioValue)}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5 text-blue-400" />
            <div>
              <p className="text-sm text-gray-400">Day P&L</p>
              <p className={`text-lg font-semibold ${getPnLColor(portfolioData.dayPnl)}`}>
                {isLoading ? '...' : formatCurrency(portfolioData.dayPnl)}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5 text-blue-400" />
            <div>
              <p className="text-sm text-gray-400">Total P&L</p>
              <p className={`text-lg font-semibold ${getPnLColor(portfolioData.totalPnl)}`}>
                {isLoading ? '...' : formatCurrency(portfolioData.totalPnl)}
              </p>
            </div>
          </div>
          
          {/* Refresh Button */}
          <button 
            onClick={fetchPortfolioData}
            className={`p-1.5 rounded hover:bg-gray-700 transition-colors ${isLoading ? 'animate-spin' : ''}`}
            disabled={isLoading}
          >
            <RefreshCw className="h-4 w-4 text-gray-400" />
          </button>
        </div>

        {/* Right side actions */}
        <div className="flex items-center space-x-4">
          {/* DhanHQ Connection Status */}
          <div className="flex items-center space-x-2">
            {isDhanConnected ? (
              <>
                <Wifi className="h-4 w-4 text-green-400" />
                <span className="text-xs text-green-400">DhanHQ</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-red-400" />
                <span className="text-xs text-red-400">DhanHQ</span>
              </>
            )}
          </div>

          {/* Notifications */}
          <button className="relative p-2 text-gray-400 hover:text-white transition-colors">
            <Bell className="h-5 w-5" />
            <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full"></span>
          </button>

          {/* Settings */}
          <button className="p-2 text-gray-400 hover:text-white transition-colors">
            <Settings className="h-5 w-5" />
          </button>

          {/* Profile Menu */}
          <div className="relative">
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-700 transition-colors"
            >
              <div className="h-8 w-8 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-white" />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-white">{user?.full_name}</p>
                <p className="text-xs text-gray-400">{user?.email}</p>
              </div>
            </button>

            {/* Profile Dropdown */}
            {showProfileMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
                <div className="py-1">
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 flex items-center space-x-2">
                    <User className="h-4 w-4" />
                    <span>Profile</span>
                  </button>
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 flex items-center space-x-2">
                    <Settings className="h-4 w-4" />
                    <span>Settings</span>
                  </button>
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 flex items-center space-x-2">
                    <Shield className="h-4 w-4" />
                    <span>Security</span>
                  </button>
                  <hr className="border-gray-700 my-1" />
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-gray-700 flex items-center space-x-2"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
