import { useState, useEffect } from 'react'
import { 
  TrendingUp, 
  TrendingDown, 
  RefreshCw,
  DollarSign,
  Briefcase,
  Activity,
  PieChart as PieChartIcon,
  AlertCircle
} from 'lucide-react'

const API_BASE_URL = 'http://localhost:8000'

interface Holding {
  symbol: string
  exchange: string
  quantity: number
  avg_price: number
  ltp: number
  current_value: number
  pnl: number
  security_id: string
  isin: string
}

interface FundData {
  availableCash?: number
  usedMargin?: number
  totalCollateral?: number
  [key: string]: any
}

interface PortfolioSummary {
  totalValue: number
  totalInvestment: number
  totalPnl: number
  pnlPercent: number
  holdingsCount: number
}

const PortfolioPage = () => {
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [funds, setFunds] = useState<FundData | null>(null)
  const [summary, setSummary] = useState<PortfolioSummary>({
    totalValue: 0,
    totalInvestment: 0,
    totalPnl: 0,
    pnlPercent: 0,
    holdingsCount: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  const fetchPortfolio = async () => {
    try {
      setLoading(true)
      setError(null)

      const [portfolioRes, fundsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/portfolio`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE_URL}/api/funds`).then(r => r.ok ? r.json() : null).catch(() => null)
      ])

      if (portfolioRes?.status === 'success') {
        const holdingsData = portfolioRes.holdings || []
        setHoldings(holdingsData)
        
        const totalValue = holdingsData.reduce((sum: number, h: Holding) => sum + h.current_value, 0)
        const totalInvestment = holdingsData.reduce((sum: number, h: Holding) => sum + (h.avg_price * h.quantity), 0)
        const totalPnl = holdingsData.reduce((sum: number, h: Holding) => sum + h.pnl, 0)
        
        setSummary({
          totalValue,
          totalInvestment,
          totalPnl,
          pnlPercent: totalInvestment > 0 ? (totalPnl / totalInvestment) * 100 : 0,
          holdingsCount: holdingsData.length
        })
      }

      if (fundsRes?.status === 'success') {
        setFunds(fundsRes.data)
      }

      setLastUpdate(new Date())
    } catch (err: any) {
      setError(err.message || 'Failed to fetch portfolio')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPortfolio()
    const interval = setInterval(fetchPortfolio, 60000)
    return () => clearInterval(interval)
  }, [])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  return (
    <div className="min-h-screen bg-gray-900 p-3 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between bg-gray-800/50 rounded-lg px-4 py-2 border border-gray-700/50">
        <div className="flex items-center space-x-3">
          <div className="p-1.5 bg-purple-500/20 rounded-lg">
            <Briefcase className="w-4 h-4 text-purple-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Portfolio</h1>
            <p className="text-gray-400 text-xs">Holdings & Fund Balance</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <span className="text-xs text-gray-400">Updated: {lastUpdate.toLocaleTimeString()}</span>
          <button
            onClick={fetchPortfolio}
            disabled={loading}
            className="flex items-center space-x-1 px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-300"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 flex items-center">
          <AlertCircle className="w-4 h-4 text-red-400 mr-2" />
          <span className="text-red-200 text-sm">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">×</button>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-3">
        <div className="bg-gradient-to-br from-gray-800/80 to-gray-800/40 rounded-lg p-3 border border-gray-700/50">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-blue-500/20 rounded"><DollarSign className="w-3 h-3 text-blue-400" /></div>
            <p className="text-xs text-gray-400">Total Value</p>
          </div>
          <p className="text-lg font-bold text-white mt-1">{formatCurrency(summary.totalValue)}</p>
        </div>
        <div className="bg-gradient-to-br from-gray-800/80 to-gray-800/40 rounded-lg p-3 border border-gray-700/50">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-purple-500/20 rounded"><Briefcase className="w-3 h-3 text-purple-400" /></div>
            <p className="text-xs text-gray-400">Investment</p>
          </div>
          <p className="text-lg font-bold text-white mt-1">{formatCurrency(summary.totalInvestment)}</p>
        </div>
        <div className="bg-gradient-to-br from-gray-800/80 to-gray-800/40 rounded-lg p-3 border border-gray-700/50">
          <div className="flex items-center space-x-2">
            <div className={`p-1.5 rounded ${summary.totalPnl >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
              {summary.totalPnl >= 0 ? <TrendingUp className="w-3 h-3 text-green-400" /> : <TrendingDown className="w-3 h-3 text-red-400" />}
            </div>
            <p className="text-xs text-gray-400">Total P&L</p>
          </div>
          <p className={`text-lg font-bold mt-1 ${summary.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {summary.totalPnl >= 0 ? '+' : ''}{formatCurrency(summary.totalPnl)}
          </p>
        </div>
        <div className="bg-gradient-to-br from-gray-800/80 to-gray-800/40 rounded-lg p-3 border border-gray-700/50">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-cyan-500/20 rounded"><PieChartIcon className="w-3 h-3 text-cyan-400" /></div>
            <p className="text-xs text-gray-400">Holdings</p>
          </div>
          <p className="text-lg font-bold text-white mt-1">{summary.holdingsCount}</p>
        </div>
        <div className="bg-gradient-to-br from-gray-800/80 to-gray-800/40 rounded-lg p-3 border border-gray-700/50">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-yellow-500/20 rounded"><Activity className="w-3 h-3 text-yellow-400" /></div>
            <p className="text-xs text-gray-400">Available Cash</p>
          </div>
          <p className="text-lg font-bold text-white mt-1">{funds?.availableCash ? formatCurrency(funds.availableCash) : '—'}</p>
        </div>
      </div>

      {/* Holdings Table */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50">
        <div className="px-4 py-2 border-b border-gray-700/50">
          <h2 className="text-sm font-semibold text-white">Holdings</h2>
        </div>
        {loading && holdings.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <RefreshCw className="w-6 h-6 mx-auto mb-2 animate-spin" />
            <p className="text-sm">Loading portfolio...</p>
          </div>
        ) : holdings.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <Briefcase className="w-6 h-6 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No holdings found</p>
            <p className="text-xs text-gray-500 mt-1">Your portfolio holdings will appear here</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-xs text-gray-400 border-b border-gray-700/50">
                <th className="text-left px-4 py-2">Symbol</th>
                <th className="text-right px-4 py-2">Qty</th>
                <th className="text-right px-4 py-2">Avg Price</th>
                <th className="text-right px-4 py-2">LTP</th>
                <th className="text-right px-4 py-2">Current Value</th>
                <th className="text-right px-4 py-2">P&L</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, i) => (
                <tr key={i} className="border-b border-gray-700/30 hover:bg-gray-700/30">
                  <td className="px-4 py-2">
                    <p className="text-sm font-medium text-white">{h.symbol}</p>
                    <p className="text-xs text-gray-500">{h.exchange}</p>
                  </td>
                  <td className="px-4 py-2 text-right text-sm text-white">{h.quantity}</td>
                  <td className="px-4 py-2 text-right text-sm text-gray-300">₹{h.avg_price.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right text-sm text-white">₹{h.ltp.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right text-sm text-white">{formatCurrency(h.current_value)}</td>
                  <td className="px-4 py-2 text-right">
                    <span className={`text-sm font-medium ${h.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {h.pnl >= 0 ? '+' : ''}₹{h.pnl.toFixed(2)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default PortfolioPage
