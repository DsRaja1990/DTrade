import { useState, useEffect, useRef } from 'react'
import { 
  RefreshCw, 
  DollarSign,
  Activity,
  Target,
  Zap,
  Brain,
  Search,
  BarChart3,
  X,
  TrendingUp,
  TrendingDown,
  Sparkles,
  Eye
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useTradingStore } from '../store/tradingStore'
import { 
  useRealTimeMarketData, 
  formatSignalType, 
  getSignalColor, 
  getConfidenceColor,
  getTrendDirection 
} from '../services/signalEngine'
import toast from 'react-hot-toast'

// Trading Modes and Engine Types
type TradingMode = 'NTrade' | 'STrade_Index' | 'STrade_Equity'
type InstrumentType = 'Options' | 'Futures'
type IndexType = 'NIFTY' | 'BANKNIFTY' | 'FINNIFTY' | 'SENSEX'
type TradingDirection = 'BUYER' | 'SELLER'

// Market Analysis Types
interface MarketAnalysis {
  trend: 'MOMENTUM' | 'SIDEWAYS' | 'BEARISH'
  strength: number // 0-100
  volatility: number
  pcr: number
  maxPain: number
  recommendation: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG_SELL' | 'WAIT'
}

// SuperTrade Engine State
interface SuperTradeState {
  isActive: boolean
  isAnalyzing: boolean
  currentCandle: any
  last15MinCandles: any[]
  last5MinCandles: any[]
  optionChainData: any
  recommendation: any
  entrySignal: boolean
  stopLoss: number | null
  target: number | null
  trailingStop: number | null
}

const TradingPage = () => {
  // State Management
  const [selectedMode, setSelectedMode] = useState<TradingMode>('STrade_Index')
  const [selectedInstrument, setSelectedInstrument] = useState<InstrumentType>('Options')
  const [selectedIndex, setSelectedIndex] = useState<IndexType>('NIFTY')
  const [tradingDirection, setTradingDirection] = useState<TradingDirection>('BUYER')
  const [equitySearchQuery, setEquitySearchQuery] = useState('')
  const [equitySearchResults, setEquitySearchResults] = useState<any[]>([])
  const [showEquityDropdown, setShowEquityDropdown] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())
  
  // Futuristic Overlay State
  const [showTradingOverlay, setShowTradingOverlay] = useState(false)
  
  // Signal Engine Integration
  const { 
    marketData, 
    signals: liveSignals, 
    lastUpdate, 
    connectionStatus
  } = useRealTimeMarketData()
  
  // SuperTrade Engine State
  const [superTradeState, setSuperTradeState] = useState<SuperTradeState>({
    isActive: false,
    isAnalyzing: false,
    currentCandle: null,
    last15MinCandles: [],
    last5MinCandles: [],
    optionChainData: null,
    recommendation: null,
    entrySignal: false,
    stopLoss: null,
    target: null,
    trailingStop: null
  })

  // Market Analysis State - Updated from Signal Engine
  const [marketAnalysis, setMarketAnalysis] = useState<MarketAnalysis>({
    trend: 'SIDEWAYS',
    strength: 65,
    volatility: 18.5,
    pcr: 1.2,
    maxPain: 19500,
    recommendation: 'HOLD'
  })

  const { dhanCredentials } = useAuthStore()
  const { 
    refreshOrders, 
    refreshPositions, 
    refreshFunds,
    orders,
    positions,
    availableFunds,
    isLoading
  } = useTradingStore()

  const equitySearchRef = useRef<HTMLDivElement>(null)

  // Initialize trading data
  useEffect(() => {
    if (dhanCredentials) {
      refreshOrders()
      refreshPositions()
      refreshFunds()
    }
  }, [dhanCredentials, refreshOrders, refreshPositions, refreshFunds])

  // Update market analysis when signal engine data changes
  useEffect(() => {
    if (marketData) {
      const trendDirection = getTrendDirection(marketData.trend)
      const strength = Math.min(100, Math.max(0, 
        trendDirection === 'MOMENTUM' ? 75 + Math.random() * 20 : 
        trendDirection === 'BEARISH' ? 15 + Math.random() * 20 : 45 + Math.random() * 20
      ))
      
      // Map trend to recommendation based on real market data
      const getRecommendation = (trend: string, pcr: number, iv: number): MarketAnalysis['recommendation'] => {
        if (trend === 'BULLISH' && pcr < 0.8 && iv < 0.15) return 'STRONG_BUY'
        if (trend === 'BULLISH' && pcr < 1.0) return 'BUY'
        if (trend === 'BEARISH' && pcr > 1.5 && iv > 0.25) return 'STRONG_SELL'
        if (trend === 'BEARISH' && pcr > 1.2) return 'SELL'
        if (pcr > 0.8 && pcr < 1.2 && iv < 0.20) return 'HOLD'
        return 'WAIT'
      }

      setMarketAnalysis({
        trend: trendDirection,
        strength: Math.round(strength),
        volatility: marketData.avg_iv * 100, // Convert to percentage
        pcr: marketData.pcr,
        maxPain: marketData.max_pain,
        recommendation: getRecommendation(marketData.trend, marketData.pcr, marketData.avg_iv)
      })
    }
  }, [marketData])

  // Real-time clock update
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Handle futuristic trading mode toggle
  const toggleTradingMode = (mode: TradingMode) => {
    if (selectedMode === mode) {
      // If clicking the same mode, toggle overlay
      setShowTradingOverlay(!showTradingOverlay)
    } else {
      // If clicking different mode, switch mode and show overlay
      setSelectedMode(mode)
      setShowTradingOverlay(true)
    }
  }

  // Close overlay
  const closeTradingOverlay = () => {
    setShowTradingOverlay(false)
  }

  // Handle equity search
  const handleEquitySearch = async (query: string) => {
    setEquitySearchQuery(query)
    if (query.length > 2) {
      try {
        // Simulate API call - replace with actual DhanHQ instruments API
        const mockResults = [
          { symbol: 'RELIANCE', name: 'Reliance Industries Ltd', ltp: 2750.50 },
          { symbol: 'TCS', name: 'Tata Consultancy Services', ltp: 3850.25 },
          { symbol: 'INFY', name: 'Infosys Limited', ltp: 1650.75 },
          { symbol: 'HDFCBANK', name: 'HDFC Bank Limited', ltp: 1580.90 },
          { symbol: 'ICICIBANK', name: 'ICICI Bank Limited', ltp: 950.30 }
        ].filter(stock => 
          stock.symbol.toLowerCase().includes(query.toLowerCase()) ||
          stock.name.toLowerCase().includes(query.toLowerCase())
        )
        setEquitySearchResults(mockResults)
        setShowEquityDropdown(true)
      } catch (error) {
        console.error('Failed to search equities:', error)
      }
    } else {
      setEquitySearchResults([])
      setShowEquityDropdown(false)
    }
  }

  // Handle click outside equity dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (equitySearchRef.current && !equitySearchRef.current.contains(event.target as Node)) {
        setShowEquityDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Toggle SuperTrade Engine
  const toggleSuperTrade = () => {
    if (!superTradeState.isActive) {
      setSuperTradeState(prev => ({
        ...prev,
        isActive: true,
        isAnalyzing: true
      }))
      
      const directionText = tradingDirection === 'BUYER' ? 'BUY Mode' : 'SELL Mode'
      toast(`SuperTrade Engine Activated - ${directionText}`, {
        icon: '🧠',
        style: { background: '#8b5cf6', color: 'white' }
      })
      
      // Use real market data for analysis
      setTimeout(() => {
        const actionType = tradingDirection === 'BUYER' ? 'BUY' : 'SELL'
        
        // Use real data to determine option type based on market conditions
        let optionType: string
        if (marketData) {
          // Use PCR and trend to determine optimal option type
          if (tradingDirection === 'BUYER') {
            optionType = marketData.pcr > 1.2 ? 'PE' : 'CE' // High PCR suggests buying PE
          } else {
            optionType = marketData.pcr < 0.8 ? 'CE' : 'PE' // Low PCR suggests selling CE
          }
        } else {
          optionType = tradingDirection === 'BUYER' 
            ? (Math.random() > 0.5 ? 'PE' : 'CE') 
            : (Math.random() > 0.5 ? 'CE' : 'PE')
        }
        
        // Calculate confidence based on real market indicators
        let confidence = 70
        if (marketData) {
          if (marketAnalysis.trend === 'MOMENTUM') confidence += 10
          if (marketAnalysis.trend === 'BEARISH' && tradingDirection === 'SELLER') confidence += 15
          if (marketData.pcr > 1.5 || marketData.pcr < 0.7) confidence += 10
          if (marketAnalysis.volatility > 20) confidence += 5
          confidence = Math.min(95, confidence + Math.floor(Math.random() * 10))
        }
        
        // Use real strike prices based on current market
        const currentPrice = marketData?.nifty_price || 19500
        const atmStrike = Math.round(currentPrice / 50) * 50
        
        setSuperTradeState(prev => ({
          ...prev,
          isAnalyzing: false,
          recommendation: {
            action: actionType,
            optionType: optionType,
            confidence: confidence,
            entry: atmStrike,
            target: tradingDirection === 'BUYER' ? atmStrike + 100 : atmStrike - 100,
            stopLoss: tradingDirection === 'BUYER' ? atmStrike - 75 : atmStrike + 75,
            reasoning: `Based on PCR: ${marketData?.pcr.toFixed(2) || 'N/A'}, Trend: ${marketAnalysis.trend}, IV: ${marketAnalysis.volatility.toFixed(1)}%`
          }
        }))
        
        toast(`AI Analysis Complete - ${actionType} ${optionType} Signal Generated (${confidence}% confidence)`, {
          icon: tradingDirection === 'BUYER' ? '📈' : '📉',
          style: { 
            background: tradingDirection === 'BUYER' ? '#10b981' : '#ef4444', 
            color: 'white' 
          }
        })
      }, 2000)
    } else {
      setSuperTradeState(prev => ({
        ...prev,
        isActive: false,
        isAnalyzing: false,
        recommendation: null
      }))
      toast('SuperTrade Engine Deactivated', {
        icon: 'ℹ️',
        style: { background: '#6b7280', color: 'white' }
      })
    }
  }

  // Get trend color
  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'MOMENTUM': return 'text-green-400'
      case 'BEARISH': return 'text-red-400'
      default: return 'text-yellow-400'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white overflow-x-hidden">
      {/* Compact Professional Trading Header */}
      <div className="bg-gray-900/95 backdrop-blur-sm border-b border-gray-700/50 px-4 py-2">
        <div className="flex justify-between items-center max-w-full overflow-x-hidden">
          <div className="flex items-center space-x-4">
            <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              DTrade Neural Hub
            </h1>
            
            {/* Real-time Clock */}
            <div className="flex items-center space-x-2 text-sm bg-gray-800/50 rounded-lg px-2 py-1 border border-gray-700/30">
              <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse"></div>
              <span className="text-cyan-400 font-mono text-xs">
                {currentTime.toLocaleTimeString('en-US', { 
                  hour12: false, 
                  hour: '2-digit', 
                  minute: '2-digit', 
                  second: '2-digit' 
                })}
              </span>
            </div>
          </div>
          
          {/* Compact Market Status */}
          <div className="flex items-center space-x-3 text-xs">
            {/* Signal Engine Status */}
            <div className="flex items-center space-x-1">
              <div className={`w-1.5 h-1.5 rounded-full ${
                connectionStatus === 'connected' ? 'bg-green-400 animate-pulse' : 
                connectionStatus === 'connecting' ? 'bg-yellow-400 animate-pulse' : 'bg-red-400'
              }`}></div>
              <span className="text-gray-300">Engine:</span>
              <span className={`font-medium ${
                connectionStatus === 'connected' ? 'text-green-400' : 
                connectionStatus === 'connecting' ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {connectionStatus === 'connected' ? 'LIVE' : 
                 connectionStatus === 'connecting' ? 'CONN' : 'OFF'}
              </span>
            </div>
            
            <div className="h-3 w-px bg-gray-600"></div>
            
            <div className="flex items-center space-x-1">
              <div className={`w-1.5 h-1.5 rounded-full ${
                marketAnalysis.trend === 'MOMENTUM' ? 'bg-green-400' :
                marketAnalysis.trend === 'BEARISH' ? 'bg-red-400' : 'bg-yellow-400'
              }`}></div>
              <span className="text-gray-300">Trend:</span>
              <span className={`font-medium ${getTrendColor(marketAnalysis.trend)}`}>
                {marketAnalysis.trend}
              </span>
            </div>
            
            <div className="h-3 w-px bg-gray-600"></div>
            
            <div className="text-gray-300">
              <span>Strength: </span>
              <span className="font-medium text-blue-400">{marketAnalysis.strength}%</span>
            </div>
            
            <div className="text-gray-300">
              <span>PCR: </span>
              <span className="font-medium text-purple-400">{marketAnalysis.pcr.toFixed(2)}</span>
            </div>
            
            <div className="text-gray-300">
              <span>Max Pain: </span>
              <span className="font-medium text-cyan-400">₹{marketAnalysis.maxPain.toLocaleString()}</span>
            </div>
            
            {/* Live Nifty Price */}
            {marketData && (
              <div className="text-gray-300">
                <span>Nifty: </span>
                <span className="font-medium text-yellow-400">₹{marketData.nifty_price.toFixed(2)}</span>
              </div>
            )}
            
            <div className={`px-2 py-1 rounded-full text-xs font-medium border ${
              marketAnalysis.recommendation === 'STRONG_BUY' ? 'bg-green-500/10 text-green-400 border-green-500/30' :
              marketAnalysis.recommendation === 'BUY' ? 'bg-green-500/10 text-green-300 border-green-500/30' :
              marketAnalysis.recommendation === 'HOLD' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30' :
              marketAnalysis.recommendation === 'SELL' ? 'bg-red-500/10 text-red-300 border-red-500/30' :
              'bg-red-500/10 text-red-400 border-red-500/30'
            }`}>
              {marketAnalysis.recommendation}
            </div>
          </div>
        </div>
      </div>

      <div className="p-3 max-w-full overflow-x-hidden">
        {/* Ultra Compact Summary Cards */}
        <div className="grid grid-cols-4 gap-2 mb-3">
          <div className="bg-gray-800/40 backdrop-blur-sm rounded-lg border border-gray-700/30 p-2.5 hover:bg-gray-800/60 transition-all duration-300">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 bg-green-500/10 rounded-lg">
                <DollarSign className="w-3.5 h-3.5 text-green-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-gray-400 leading-none">Available Funds</p>
                <p className="text-sm font-bold text-white leading-tight mt-0.5">
                  ₹{(availableFunds || 0) > 100000 ? `${Math.floor((availableFunds || 0) / 1000)}K` : (availableFunds?.toLocaleString() || '0')}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800/40 backdrop-blur-sm rounded-lg border border-gray-700/30 p-2.5 hover:bg-gray-800/60 transition-all duration-300">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 bg-blue-500/10 rounded-lg">
                <Activity className="w-3.5 h-3.5 text-blue-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-gray-400 leading-none">Active Orders</p>
                <p className="text-sm font-bold text-white leading-tight mt-0.5">{orders.length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800/40 backdrop-blur-sm rounded-lg border border-gray-700/30 p-2.5 hover:bg-gray-800/60 transition-all duration-300">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 bg-purple-500/10 rounded-lg">
                <Target className="w-3.5 h-3.5 text-purple-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-gray-400 leading-none">Open Positions</p>
                <p className="text-sm font-bold text-white leading-tight mt-0.5">{positions.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-gray-800/40 backdrop-blur-sm rounded-lg border border-gray-700/30 p-2.5 hover:bg-gray-800/60 transition-all duration-300">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 bg-cyan-500/10 rounded-lg">
                <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-gray-400 leading-none">Today's P&L</p>
                <p className={`text-sm font-bold leading-tight mt-0.5 ${
                  positions.reduce((sum, pos) => sum + (pos.unrealizedProfit || 0), 0) >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {positions.reduce((sum, pos) => sum + (pos.unrealizedProfit || 0), 0) >= 0 ? '+' : ''}₹{Math.abs(positions.reduce((sum, pos) => sum + (pos.unrealizedProfit || 0), 0)).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Futuristic 2-Panel Layout */}
        <div className="grid grid-cols-12 gap-4 h-[calc(100vh-170px)] overflow-hidden max-w-full">
          
          {/* Left Panel - AI Trading Modes with Configuration Overlay (Col 1-4) */}
          <div className="col-span-12 lg:col-span-4 relative overflow-hidden">
            
            {/* Default AI Trading Mode Selector */}
            <div className={`bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 h-full transition-all duration-500 overflow-y-auto ${
              showTradingOverlay ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
            }`}>
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center">
                <div className="w-2 h-2 bg-cyan-400 rounded-full mr-2 animate-pulse"></div>
                AI Trading Modes
              </h3>
              
              <div className="space-y-3">
                {[
                  { 
                    id: 'STrade_Index', 
                    name: 'STrade Index', 
                    icon: Brain, 
                    desc: 'AI-powered index options & futures', 
                    color: 'purple',
                    bgGradient: 'from-purple-600/20 to-pink-600/20',
                    borderColor: 'border-purple-500/50',
                    shadowColor: 'shadow-purple-500/20'
                  },
                  { 
                    id: 'STrade_Equity', 
                    name: 'STrade Equity', 
                    icon: Zap, 
                    desc: 'AI-powered equity options & futures', 
                    color: 'blue',
                    bgGradient: 'from-blue-600/20 to-cyan-600/20',
                    borderColor: 'border-blue-500/50',
                    shadowColor: 'shadow-blue-500/20'
                  }
                ].map((mode) => (
                  <button
                    key={mode.id}
                    onClick={() => toggleTradingMode(mode.id as TradingMode)}
                    className={`w-full p-4 rounded-xl transition-all duration-300 border relative overflow-hidden group ${
                      selectedMode === mode.id
                        ? `bg-gradient-to-r ${mode.bgGradient} ${mode.borderColor} shadow-lg ${mode.shadowColor} transform scale-[1.02]`
                        : 'bg-gray-700/30 border-gray-600/50 hover:bg-gray-600/40 hover:border-gray-500/50 hover:scale-[1.01]'
                    }`}
                  >
                    {/* Animated gradient overlay */}
                    <div className={`absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent transform translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000`}></div>
                    
                    <div className="flex items-center space-x-3 relative z-10">
                      <div className={`p-3 rounded-lg transition-all duration-300 ${
                        selectedMode === mode.id 
                          ? `bg-${mode.color}-500/20 border border-${mode.color}-400/30` 
                          : 'bg-gray-600/20 hover:bg-gray-500/30'
                      }`}>
                        <mode.icon className={`w-6 h-6 transition-all duration-300 ${
                          selectedMode === mode.id ? `text-${mode.color}-400` : 'text-gray-400 group-hover:text-gray-300'
                        }`} />
                      </div>
                      <div className="text-left flex-1">
                        <p className={`text-sm font-bold transition-colors duration-300 ${
                          selectedMode === mode.id ? 'text-white' : 'text-gray-300 group-hover:text-white'
                        }`}>{mode.name}</p>
                        <p className="text-xs text-gray-400 group-hover:text-gray-300 transition-colors duration-300">{mode.desc}</p>
                      </div>
                      <div className="flex items-center space-x-2">
                        {selectedMode === mode.id && (
                          <>
                            <div className={`w-2 h-2 bg-${mode.color}-400 rounded-full animate-pulse`}></div>
                            {showTradingOverlay && (
                              <div className="flex items-center space-x-1">
                                <Sparkles className="w-3 h-3 text-cyan-400 animate-pulse" />
                                <div className="text-xs text-cyan-400 font-medium">CONFIG</div>
                              </div>
                            )}
                          </>
                        )}
                        {selectedMode !== mode.id && (
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                            <Eye className="w-4 h-4 text-gray-400" />
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {/* Active Mode Status - Futuristic Design */}
              <div className="mt-6 p-4 bg-gradient-to-r from-gray-900/80 to-gray-800/80 rounded-xl border border-cyan-500/30 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
                    <span className="text-sm text-cyan-400 font-medium">Active Mode</span>
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                    showTradingOverlay ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'
                  }`}>
                    {showTradingOverlay ? 'CONFIGURING' : 'READY'}
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Brain className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-medium text-white">{selectedMode}</span>
                </div>
                
                <p className="text-xs text-gray-400 mt-1">
                  {selectedMode === 'STrade_Index' ? 'AI-powered index options/futures trading' : 'AI-powered equity options/futures trading'}
                </p>
                
                {/* SuperTrade Engine Status */}
                {superTradeState.isActive && (
                  <div className="mt-2 p-2 bg-purple-900/30 rounded-lg border border-purple-500/30">
                    <div className="flex items-center space-x-2">
                      <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse"></div>
                      <span className="text-xs text-purple-400">SuperTrade Engine: Active</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Configuration Overlay - Only in Left Panel */}
            <div className={`absolute inset-0 bg-gradient-to-br from-gray-900/95 via-gray-800/95 to-black/95 backdrop-blur-lg rounded-xl border border-cyan-500/30 transform transition-all duration-700 ease-in-out ${
              showTradingOverlay 
                ? 'translate-x-0 opacity-100 scale-100' 
                : 'translate-x-full opacity-0 scale-95'
            }`}>
              
              {/* Compact Header */}
              <div className="p-2 border-b border-cyan-500/20">
                <div className="flex items-center justify-end">
                  <button
                    onClick={closeTradingOverlay}
                    className="p-1.5 hover:bg-gray-700/50 rounded-lg transition-colors group"
                  >
                    <X className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
                  </button>
                </div>
              </div>

              {/* Compact Configuration Panel */}
              <div className="p-3 space-y-3 h-[calc(100%-60px)] overflow-y-auto">
                
                {/* Instrument Type - Ultra Compact Design */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-cyan-400 flex items-center">
                    <div className="w-1 h-1 bg-cyan-400 rounded-full mr-1.5"></div>
                    Instrument Type
                  </label>
                  <div className="grid grid-cols-2 gap-1.5">
                    {['Options', 'Futures'].map((type) => (
                      <button
                        key={type}
                        onClick={() => setSelectedInstrument(type as InstrumentType)}
                        className={`p-1.5 rounded-lg text-xs font-medium transition-all border relative overflow-hidden group ${
                          selectedInstrument === type
                            ? 'bg-gradient-to-r from-cyan-600/30 to-blue-600/30 border-cyan-400/60 text-cyan-200 shadow-lg shadow-cyan-500/20'
                            : 'bg-gray-700/30 border-gray-600/50 text-gray-300 hover:bg-gray-600/40'
                        }`}
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/15 to-transparent transform translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
                        <span className="relative z-10">{type}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Index/Equity Selector - Matching Instrument Type Style */}
                {selectedMode === 'STrade_Index' ? (
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-purple-400 flex items-center">
                      <div className="w-1 h-1 bg-purple-400 rounded-full mr-1.5"></div>
                      Select Index
                    </label>
                    <div className="grid grid-cols-2 gap-1.5">
                      {[
                        { id: 'NIFTY', name: 'NIFTY', short: 'N50' },
                        { id: 'BANKNIFTY', name: 'BANK', short: 'BNF' },
                        { id: 'FINNIFTY', name: 'FIN', short: 'FNF' },
                        { id: 'SENSEX', name: 'BSE', short: 'SX' }
                      ].map((index) => (
                        <button
                          key={index.id}
                          onClick={() => setSelectedIndex(index.id as IndexType)}
                          className={`p-1.5 rounded-lg text-xs font-medium transition-all border relative overflow-hidden group ${
                            selectedIndex === index.id
                              ? 'bg-gradient-to-r from-indigo-600/30 to-purple-600/30 border-indigo-400/60 text-indigo-200 shadow-lg shadow-indigo-500/20'
                              : 'bg-gray-700/30 border-gray-600/50 text-gray-300 hover:bg-gray-600/40'
                          }`}
                        >
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-indigo-400/15 to-transparent transform translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
                          <span className="relative z-10">{index.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-1.5" ref={equitySearchRef}>
                    <label className="text-xs font-medium text-blue-400 flex items-center">
                      <div className="w-1 h-1 bg-blue-400 rounded-full mr-1.5"></div>
                      Search Equity
                    </label>
                    <div className="relative">
                      <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-3 h-3 text-gray-400" />
                      <input
                        type="text"
                        value={equitySearchQuery}
                        onChange={(e) => handleEquitySearch(e.target.value)}
                        placeholder="Search stocks..."
                        className="w-full pl-8 pr-3 py-1.5 bg-gray-700/30 border border-gray-600/50 rounded-lg text-white placeholder-gray-400 focus:border-blue-500/50 focus:outline-none text-xs"
                      />
                      
                      {showEquityDropdown && equitySearchResults.length > 0 && (
                        <div className="absolute z-10 w-full mt-1 bg-gray-800/95 backdrop-blur-sm border border-gray-600/50 rounded-lg shadow-2xl max-h-20 overflow-y-auto">
                          {equitySearchResults.map((stock, index) => (
                            <button
                              key={index}
                              onClick={() => {
                                setEquitySearchQuery(stock.symbol)
                                setShowEquityDropdown(false)
                              }}
                              className="w-full px-2 py-1 text-left hover:bg-gray-700/50 focus:bg-gray-700/50 focus:outline-none border-b border-gray-700/30 last:border-b-0"
                            >
                              <div className="flex justify-between items-center">
                                <div>
                                  <p className="text-xs font-medium text-white">{stock.symbol}</p>
                                  <p className="text-xs text-gray-400 truncate">{stock.name}</p>
                                </div>
                                <p className="text-xs text-green-400 font-medium">₹{stock.ltp}</p>
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* SuperTrade Engine - Compact & Centered */}
                <div className="bg-gradient-to-br from-violet-900/50 via-indigo-900/40 to-purple-900/50 rounded-xl p-2.5 border border-violet-400/40 backdrop-blur-md shadow-xl shadow-violet-500/20">
                  {/* Header Section */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <div className="relative">
                        <Brain className="w-4 h-4 text-violet-300" />
                        <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse shadow-lg shadow-cyan-400/50"></div>
                      </div>
                      <span className="text-sm font-bold text-violet-200 tracking-wide">SUPERTRADE</span>
                    </div>
                    
                    <div className={`px-2 py-1 rounded-full text-xs font-bold border transition-all duration-300 ${
                      superTradeState.isActive 
                        ? 'bg-emerald-500/30 text-emerald-300 border-emerald-400/50 shadow-lg shadow-emerald-500/20' 
                        : 'bg-slate-500/20 text-slate-400 border-slate-500/40'
                    }`}>
                      {superTradeState.isActive ? 'ACTIVE' : 'INACTIVE'}
                    </div>
                  </div>
                  
                  {/* Simplified Description */}
                  <div className="text-xs text-violet-200/80 mb-2 text-center">
                    Advanced Neural AI Engine
                  </div>
                  
                  {/* Centered Toggle Button */}
                  <div className="flex flex-col items-center space-y-2 mb-2">
                    <button
                      onClick={toggleSuperTrade}
                      className={`relative inline-flex h-6 w-14 items-center rounded-full transition-all duration-700 shadow-xl transform hover:scale-105 ${
                        superTradeState.isActive 
                          ? 'bg-gradient-to-r from-emerald-500 via-cyan-500 to-violet-500 shadow-emerald-500/40' 
                          : 'bg-gradient-to-r from-gray-600 to-gray-700 shadow-gray-600/30'
                      }`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-all duration-700 shadow-lg ${
                        superTradeState.isActive ? 'translate-x-9 rotate-180 bg-gradient-to-r from-white to-cyan-100' : 'translate-x-1'
                      }`} />
                      
                      {/* Toggle Labels */}
                      <div className="absolute inset-0 flex items-center justify-between px-1 pointer-events-none">
                        <span className={`text-xs font-bold transition-all duration-300 ${
                          !superTradeState.isActive ? 'text-white opacity-100' : 'text-white/50 opacity-0'
                        }`}>
                          OFF
                        </span>
                        <span className={`text-xs font-bold transition-all duration-300 ${
                          superTradeState.isActive ? 'text-white opacity-100' : 'text-white/50 opacity-0'
                        }`}>
                          ON
                        </span>
                      </div>
                    </button>
                    <span className="text-xs text-violet-300 font-medium">
                      {superTradeState.isActive ? 'Engine Running' : 'Click to Activate'}
                    </span>
                  </div>
                  
                  {/* Status Display */}
                  {superTradeState.isActive && (
                    <div className="flex items-center justify-center space-x-2 p-1.5 bg-gradient-to-r from-emerald-900/50 via-cyan-900/50 to-violet-900/50 rounded-lg border border-emerald-400/30 backdrop-blur-sm shadow-inner">
                      {superTradeState.isAnalyzing ? (
                        <>
                          <div className="flex space-x-1">
                            <div className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse shadow-lg shadow-amber-400/50"></div>
                            <div className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse shadow-lg shadow-amber-400/50" style={{animationDelay: '0.2s'}}></div>
                            <div className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse shadow-lg shadow-amber-400/50" style={{animationDelay: '0.4s'}}></div>
                          </div>
                          <span className="text-xs text-amber-300 font-bold">ANALYZING...</span>
                        </>
                      ) : superTradeState.recommendation ? (
                        <>
                          <div className="w-2 h-2 bg-emerald-400 rounded-full shadow-lg shadow-emerald-400/50 animate-pulse"></div>
                          <span className="text-xs text-emerald-300 font-bold">
                            {superTradeState.recommendation.action} {superTradeState.recommendation.optionType} - {superTradeState.recommendation.confidence}%
                          </span>
                        </>
                      ) : (
                        <>
                          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse shadow-lg shadow-cyan-400/50"></div>
                          <span className="text-xs text-cyan-300 font-bold">READY</span>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Trading Direction Toggle - Ultra Compact */}
                <div className="bg-gradient-to-br from-gray-900/60 via-gray-800/60 to-gray-900/60 rounded-xl p-2 border border-gray-700/50 backdrop-blur-sm">
                  <h4 className="text-xs font-bold text-gray-300 mb-2 flex items-center tracking-wide">
                    <Zap className="w-3 h-3 mr-1 text-yellow-400" />
                    TRADING MODE
                  </h4>
                  
                  {/* Buyer/Seller Toggle */}
                  <div className="relative">
                    <div className="flex bg-gray-800/60 rounded-xl p-0.5 border border-gray-600/30">
                      <button
                        onClick={() => setTradingDirection('BUYER')}
                        className={`flex-1 relative px-2 py-1.5 rounded-lg text-xs font-bold transition-all duration-500 ${
                          tradingDirection === 'BUYER'
                            ? 'bg-gradient-to-r from-green-500 via-emerald-500 to-green-600 text-white shadow-lg shadow-green-500/30 transform scale-105'
                            : 'text-gray-400 hover:text-gray-300'
                        }`}
                      >
                        <div className="flex items-center justify-center space-x-1">
                          <TrendingUp className="w-3 h-3" />
                          <span>BUYER</span>
                        </div>
                        {tradingDirection === 'BUYER' && (
                          <div className="absolute inset-0 bg-gradient-to-r from-green-400/20 to-emerald-400/20 rounded-lg animate-pulse"></div>
                        )}
                      </button>
                      
                      <button
                        onClick={() => setTradingDirection('SELLER')}
                        className={`flex-1 relative px-2 py-1.5 rounded-lg text-xs font-bold transition-all duration-500 ${
                          tradingDirection === 'SELLER'
                            ? 'bg-gradient-to-r from-red-500 via-rose-500 to-red-600 text-white shadow-lg shadow-red-500/30 transform scale-105'
                            : 'text-gray-400 hover:text-gray-300'
                        }`}
                      >
                        <div className="flex items-center justify-center space-x-1">
                          <TrendingDown className="w-3 h-3" />
                          <span>SELLER</span>
                        </div>
                        {tradingDirection === 'SELLER' && (
                          <div className="absolute inset-0 bg-gradient-to-r from-red-400/20 to-rose-400/20 rounded-lg animate-pulse"></div>
                        )}
                      </button>
                    </div>
                  </div>
                  
                  {/* Direction Info - Compact */}
                  <div className="mt-2 p-1.5 bg-gradient-to-r from-gray-800/40 to-gray-900/40 rounded-lg border border-gray-700/30">
                    <div className="flex items-center space-x-1.5">
                      <div className={`w-1 h-1 rounded-full ${
                        tradingDirection === 'BUYER' ? 'bg-green-400' : 'bg-red-400'
                      }`}></div>
                      <span className="text-xs text-gray-300">Mode:</span>
                      <span className={`text-xs font-bold ${
                        tradingDirection === 'BUYER' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {tradingDirection === 'BUYER' ? 'BUY PE/CE' : 'SELL CE/PE'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1 leading-tight">
                      {tradingDirection === 'BUYER' 
                        ? 'AI optimizes for buy entries'
                        : 'AI optimizes for sell entries'
                      }
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel - Live Signals and Positions (Col 5-12) */}
          <div className="col-span-12 lg:col-span-8 space-y-4 overflow-hidden">
            
            {/* Live Signals Section */}
            <div className="bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 min-w-0">
              <div className="flex items-center justify-between mb-3 min-w-0">
                <h3 className="text-sm font-semibold text-white flex items-center truncate">
                  <Zap className="w-4 h-4 mr-2 text-yellow-400 flex-shrink-0" />
                  Live Signals
                  <span className="ml-2 text-xs text-gray-400">({liveSignals.length})</span>
                  {connectionStatus === 'connected' && (
                    <div className="ml-2 w-2 h-2 bg-green-400 rounded-full animate-pulse flex-shrink-0"></div>
                  )}
                </h3>
                {lastUpdate && (
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    Updated: {new Date(lastUpdate).toLocaleTimeString()}
                  </span>
                )}
              </div>

              <div className="space-y-2 max-h-32 overflow-y-auto scrollbar-thin min-w-0">
                {liveSignals.length === 0 ? (
                  <div className="text-center py-4">
                    <div className="text-gray-400 text-sm">
                      {connectionStatus === 'connected' ? 'Waiting for signals...' : 'Connect to Signal Engine'}
                    </div>
                  </div>
                ) : (
                  liveSignals.slice(0, 3).map((signal) => (
                    <div key={signal.id} className="bg-gray-700/30 rounded-lg p-3 border border-gray-600/30">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center space-x-2">
                          <span className={`text-sm font-bold ${getSignalColor(signal.signal_type)}`}>
                            {formatSignalType(signal.signal_type)}
                          </span>
                          <span className="text-white font-medium">₹{signal.strike}</span>
                          <span className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(signal.confidence)} bg-gray-800/50`}>
                            {signal.confidence}%
                          </span>
                        </div>
                        <span className="text-xs text-gray-400">
                          {new Date(signal.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="text-xs text-gray-300 mb-1">
                        Entry: ₹{signal.entry_price} | Target: ₹{signal.target} | SL: ₹{signal.stop_loss}
                      </div>
                      <div className="text-xs text-gray-400 truncate">
                        {signal.reasoning}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
            
            {/* Open Positions Section */}
            <div className="bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 flex-1 min-w-0">
              <div className="flex items-center justify-between mb-4 min-w-0">
                <h3 className="text-sm font-semibold text-white flex items-center truncate">
                  <BarChart3 className="w-4 h-4 mr-2 text-purple-400 flex-shrink-0" />
                  Open Positions
                  <span className="ml-2 text-xs text-gray-400">({positions.length})</span>
                </h3>
                <button
                  onClick={() => {
                    refreshOrders()
                    refreshPositions()
                    refreshFunds()
                  }}
                  className="p-2 bg-gray-700/50 hover:bg-gray-600/50 rounded-lg transition-colors group flex-shrink-0"
                >
                  <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-300" />
                </button>
              </div>

              {isLoading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-gray-400">Loading positions...</p>
                  </div>
                </div>
              ) : positions.length === 0 ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <Target className="w-16 h-16 text-gray-500 mx-auto mb-4" />
                    <h4 className="text-lg font-medium text-gray-300 mb-2">No Open Positions</h4>
                    <p className="text-gray-500">Start trading to see your positions here</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 overflow-y-auto h-[calc(100%-60px)] scrollbar-thin">
                  {positions.map((position, index) => (
                    <div key={index} className="bg-gray-900/40 rounded-lg p-4 border border-gray-700/30 hover:bg-gray-900/60 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <h4 className="font-medium text-white text-lg">{position.tradingSymbol}</h4>
                          <div className="flex items-center space-x-4 text-sm text-gray-400 mt-1">
                            <span>Qty: <span className="text-white font-medium">{position.netQty}</span></span>
                            <span>Avg: <span className="text-white font-medium">₹{position.costPrice}</span></span>
                            <span>LTP: <span className="text-white font-medium">₹{position.costPrice}</span></span>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className={`text-lg font-bold ${
                            position.unrealizedProfit >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {position.unrealizedProfit >= 0 ? '+' : ''}₹{position.unrealizedProfit.toLocaleString()}
                          </p>
                          <p className={`text-sm font-medium ${
                            position.unrealizedProfit >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {position.unrealizedProfit >= 0 ? '+' : ''}{((position.unrealizedProfit / (position.costPrice * position.netQty)) * 100).toFixed(2)}%
                          </p>
                        </div>
                      </div>
                      
                      {/* Position Actions */}
                      <div className="flex items-center justify-between pt-2 border-t border-gray-700/30">
                        <div className="flex items-center space-x-2 text-xs text-gray-500">
                          <span>Market Value: ₹{(position.costPrice * position.netQty).toLocaleString()}</span>
                        </div>
                        <div className="flex space-x-2">
                          <button className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded text-xs font-medium transition-colors">
                            Exit
                          </button>
                          <button className="px-3 py-1 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded text-xs font-medium transition-colors">
                            Modify
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TradingPage
