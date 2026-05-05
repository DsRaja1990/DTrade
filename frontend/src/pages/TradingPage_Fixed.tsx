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
import toast from 'react-hot-toast'

// Trading Modes and Engine Types
type TradingMode = 'NTrade' | 'STrade_Index' | 'STrade_Equity'
type InstrumentType = 'Options' | 'Futures'
type IndexType = 'NIFTY' | 'BANKNIFTY' | 'FINNIFTY' | 'SENSEX'

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
  const [equitySearchQuery, setEquitySearchQuery] = useState('')
  const [equitySearchResults, setEquitySearchResults] = useState<any[]>([])
  const [showEquityDropdown, setShowEquityDropdown] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())
  
  // Futuristic Overlay State
  const [showTradingOverlay, setShowTradingOverlay] = useState(false)
  
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

  // Market Analysis State
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
      initializeMarketAnalysis()
    }
  }, [dhanCredentials, refreshOrders, refreshPositions, refreshFunds])

  // Real-time clock update
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Initialize market analysis
  const initializeMarketAnalysis = async () => {
    try {
      // Simulate market analysis - in real implementation, call backend API
      setMarketAnalysis({
        trend: Math.random() > 0.5 ? 'MOMENTUM' : 'SIDEWAYS',
        strength: Math.floor(Math.random() * 100),
        volatility: Math.random() * 30 + 10,
        pcr: Math.random() * 2 + 0.5,
        maxPain: 19000 + Math.floor(Math.random() * 1000),
        recommendation: ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'][Math.floor(Math.random() * 5)] as any
      })
    } catch (error) {
      console.error('Failed to initialize market analysis:', error)
    }
  }

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
      
      toast('SuperTrade Engine Activated', {
        icon: '🧠',
        style: { background: '#8b5cf6', color: 'white' }
      })
      
      // Simulate analysis process
      setTimeout(() => {
        setSuperTradeState(prev => ({
          ...prev,
          isAnalyzing: false,
          recommendation: {
            action: 'BUY',
            confidence: 85,
            entry: 19500,
            target: 19650,
            stopLoss: 19400
          }
        }))
        toast('AI Analysis Complete - BUY Signal Generated', {
          icon: 'ℹ️',
          style: { background: '#3b82f6', color: 'white' }
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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
      {/* Compact Professional Trading Header */}
      <div className="bg-gray-900/95 backdrop-blur-sm border-b border-gray-700/50 px-4 py-2">
        <div className="flex justify-between items-center">
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
              <span className="font-medium text-purple-400">{marketAnalysis.pcr}</span>
            </div>
            
            <div className="text-gray-300">
              <span>Max Pain: </span>
              <span className="font-medium text-cyan-400">₹{marketAnalysis.maxPain}</span>
            </div>
            
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

      <div className="p-4">
        {/* Enhanced Summary Cards */}
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 hover:bg-gray-800/60 transition-all duration-300">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-green-500/10 rounded-lg">
                <DollarSign className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">Available Funds</p>
                <p className="text-xl font-bold text-white">
                  ₹{(availableFunds || 0) > 100000 ? `${Math.floor((availableFunds || 0) / 1000)}K` : (availableFunds?.toLocaleString() || '0')}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 hover:bg-gray-800/60 transition-all duration-300">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <Activity className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">Active Orders</p>
                <p className="text-xl font-bold text-white">{orders.length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 hover:bg-gray-800/60 transition-all duration-300">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-purple-500/10 rounded-lg">
                <Target className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">Open Positions</p>
                <p className="text-xl font-bold text-white">{positions.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 hover:bg-gray-800/60 transition-all duration-300">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-cyan-500/10 rounded-lg">
                <TrendingUp className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">Today's P&L</p>
                <p className="text-xl font-bold text-green-400">+₹2,450</p>
              </div>
            </div>
          </div>
        </div>

        {/* Futuristic 2-Panel Layout */}
        <div className="grid grid-cols-12 gap-4 h-[calc(100vh-200px)]">
          
          {/* Left Panel - AI Trading Modes with Configuration Overlay (Col 1-4) */}
          <div className="col-span-4 relative">
            
            {/* Default AI Trading Mode Selector */}
            <div className={`bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 h-full transition-all duration-500 ${
              showTradingOverlay ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
            }`}>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
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
              
              {/* Futuristic Header */}
              <div className="p-4 border-b border-cyan-500/20">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
                    <h3 className="text-lg font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                      {selectedMode === 'STrade_Index' ? 'AI Index Config' : 'AI Equity Config'}
                    </h3>
                  </div>
                  <button
                    onClick={closeTradingOverlay}
                    className="p-1.5 hover:bg-gray-700/50 rounded-lg transition-colors group"
                  >
                    <X className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-1">Configure AI trading parameters</p>
              </div>

              {/* Compact Configuration Panel */}
              <div className="p-4 space-y-4 h-[calc(100%-80px)] overflow-y-auto">
                
                {/* Instrument Type - Compact Design */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-cyan-400 flex items-center">
                    <div className="w-1 h-1 bg-cyan-400 rounded-full mr-1.5"></div>
                    Instrument Type
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {['Options', 'Futures'].map((type) => (
                      <button
                        key={type}
                        onClick={() => setSelectedInstrument(type as InstrumentType)}
                        className={`p-2 rounded-lg text-xs font-medium transition-all border relative overflow-hidden group ${
                          selectedInstrument === type
                            ? 'bg-gradient-to-r from-cyan-600/20 to-blue-600/20 border-cyan-500/50 text-cyan-300'
                            : 'bg-gray-700/30 border-gray-600/50 text-gray-300 hover:bg-gray-600/40'
                        }`}
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/10 to-transparent transform translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
                        <span className="relative z-10">{type}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Index/Equity Selector - Compact */}
                {selectedMode === 'STrade_Index' ? (
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-purple-400 flex items-center">
                      <div className="w-1 h-1 bg-purple-400 rounded-full mr-1.5"></div>
                      Select Index
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { id: 'NIFTY', name: 'NIFTY', full: 'NIFTY 50' },
                        { id: 'BANKNIFTY', name: 'BANK', full: 'BANK NIFTY' },
                        { id: 'FINNIFTY', name: 'FIN', full: 'FIN NIFTY' },
                        { id: 'SENSEX', name: 'BSE', full: 'SENSEX' }
                      ].map((index) => (
                        <button
                          key={index.id}
                          onClick={() => setSelectedIndex(index.id as IndexType)}
                          className={`p-2 rounded-lg text-xs font-medium transition-all border relative overflow-hidden group ${
                            selectedIndex === index.id
                              ? 'bg-gradient-to-r from-purple-600/20 to-pink-600/20 border-purple-500/50 text-purple-300'
                              : 'bg-gray-700/30 border-gray-600/50 text-gray-300 hover:bg-gray-600/40'
                          }`}
                        >
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-400/10 to-transparent transform translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
                          <div className="relative z-10 text-center">
                            <p className="font-medium">{index.name}</p>
                            <p className="text-xs text-gray-500">{index.full}</p>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2" ref={equitySearchRef}>
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
                        className="w-full pl-8 pr-3 py-2 bg-gray-700/30 border border-gray-600/50 rounded-lg text-white placeholder-gray-400 focus:border-blue-500/50 focus:outline-none text-xs"
                      />
                      
                      {showEquityDropdown && equitySearchResults.length > 0 && (
                        <div className="absolute z-10 w-full mt-1 bg-gray-800/95 backdrop-blur-sm border border-gray-600/50 rounded-lg shadow-2xl max-h-24 overflow-y-auto">
                          {equitySearchResults.map((stock, index) => (
                            <button
                              key={index}
                              onClick={() => {
                                setEquitySearchQuery(stock.symbol)
                                setShowEquityDropdown(false)
                              }}
                              className="w-full px-2 py-1.5 text-left hover:bg-gray-700/50 focus:bg-gray-700/50 focus:outline-none border-b border-gray-700/30 last:border-b-0"
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

                {/* SuperTrade Engine - Compact */}
                <div className="bg-gradient-to-r from-purple-900/30 to-cyan-900/30 rounded-lg p-3 border border-purple-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <Brain className="w-4 h-4 text-purple-400" />
                      <span className="text-xs font-medium text-purple-300">SuperTrade Engine</span>
                    </div>
                    <button
                      onClick={toggleSuperTrade}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-all duration-300 ${
                        superTradeState.isActive 
                          ? 'bg-gradient-to-r from-cyan-500 to-purple-500' 
                          : 'bg-gray-600'
                      }`}
                    >
                      <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform duration-300 ${
                        superTradeState.isActive ? 'translate-x-5' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>
                  
                  <p className="text-xs text-gray-400 mb-2">
                    Neural AI analyzes market patterns for optimal entries
                  </p>
                  
                  {superTradeState.isActive && (
                    <div className="flex items-center space-x-2 p-2 bg-gray-800/50 rounded-lg border border-cyan-500/20">
                      {superTradeState.isAnalyzing ? (
                        <>
                          <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse"></div>
                          <span className="text-xs text-yellow-400">Analyzing...</span>
                        </>
                      ) : superTradeState.recommendation ? (
                        <>
                          <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>
                          <span className="text-xs text-green-400">
                            {superTradeState.recommendation.action} - {superTradeState.recommendation.confidence}%
                          </span>
                        </>
                      ) : (
                        <>
                          <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse"></div>
                          <span className="text-xs text-cyan-400">Ready</span>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Quick Actions */}
                <div className="bg-gradient-to-r from-gray-900/50 to-gray-800/50 rounded-lg p-3 border border-gray-700/50">
                  <h4 className="text-xs font-medium text-gray-300 mb-2 flex items-center">
                    <Zap className="w-3 h-3 mr-1.5 text-yellow-400" />
                    Quick Actions
                  </h4>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button className="p-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg text-xs font-medium transition-all duration-300 hover:scale-105 flex items-center justify-center space-x-1">
                      <TrendingUp className="w-3 h-3" />
                      <span>BUY</span>
                    </button>
                    <button className="p-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-xs font-medium transition-all duration-300 hover:scale-105 flex items-center justify-center space-x-1">
                      <TrendingDown className="w-3 h-3" />
                      <span>SELL</span>
                    </button>
                    <button className="p-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg text-xs font-medium transition-all duration-300 hover:scale-105 flex items-center justify-center space-x-1">
                      <Eye className="w-3 h-3" />
                      <span>Watch</span>
                    </button>
                    <button className="p-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg text-xs font-medium transition-all duration-300 hover:scale-105 flex items-center justify-center space-x-1">
                      <Brain className="w-3 h-3" />
                      <span>Predict</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel - Open Positions (Col 5-12) */}
          <div className="col-span-8">
            <div className="bg-gray-800/40 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4 h-full">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center">
                  <BarChart3 className="w-5 h-5 mr-2 text-purple-400" />
                  Open Positions
                  <span className="ml-2 text-sm text-gray-400">({positions.length})</span>
                </h3>
                <button
                  onClick={() => {
                    refreshOrders()
                    refreshPositions()
                    refreshFunds()
                  }}
                  className="p-2 bg-gray-700/50 hover:bg-gray-600/50 rounded-lg transition-colors group"
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
                <div className="space-y-3 overflow-y-auto h-[calc(100%-60px)] pr-2">
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
