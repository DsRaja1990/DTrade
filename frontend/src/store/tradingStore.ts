import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { dhanTradingService, DhanOrderRequest, DhanOrderResponse, DhanPosition, DhanHolding } from '../services/dhanTradingService'
import { superTradeService, SuperTradeRequest, SuperTradeResponse, MarketAnalysis } from '../services/superTradeService'
import toast from 'react-hot-toast'

export interface TradingState {
  // Order Management
  orders: DhanOrderResponse[]
  activeOrders: DhanOrderResponse[]
  orderHistory: DhanOrderResponse[]
  
  // Positions & Holdings
  positions: DhanPosition[]
  holdings: DhanHolding[]
  
  // Portfolio Summary
  totalPnL: number
  dayPnL: number
  availableFunds: number
  usedFunds: number
  
  // Current Market Data
  selectedSymbol: string | null
  marketQuote: any | null
  optionChain: any | null
  
  // Trading Settings
  defaultQuantity: number
  defaultProductType: 'INTRADAY' | 'CNC' | 'MARGIN' | 'CO' | 'BO'
  defaultOrderType: 'LIMIT' | 'MARKET' | 'STOP_LOSS' | 'STOP_LOSS_MARKET'
  
  // AI Trading
  aiTradingEnabled: boolean
  isAIActive: boolean
  aiStrategy: string | null
  
  // SuperTrade Engine
  superTradeEnabled: boolean
  currentAnalysis: MarketAnalysis | null
  superTradeHistory: SuperTradeResponse[]
  
  // Loading States
  isLoading: boolean
  isPlacingOrder: boolean
  isLoadingPositions: boolean
  isLoadingOrders: boolean
  isAnalyzing: boolean
  
  // Actions
  placeOrder: (orderData: Omit<DhanOrderRequest, 'dhanClientId' | 'correlationId'>) => Promise<boolean>
  cancelOrder: (orderId: string) => Promise<boolean>
  modifyOrder: (orderId: string, orderData: Partial<DhanOrderRequest>) => Promise<boolean>
  refreshOrders: () => Promise<void>
  refreshPositions: () => Promise<void>
  refreshHoldings: () => Promise<void>
  refreshFunds: () => Promise<void>
  getMarketQuote: (securityId: string, exchangeSegment: string) => Promise<void>
  getOptionChain: (underlying: string) => Promise<void>
  setSelectedSymbol: (symbol: string) => void
  updateTradingSettings: (settings: Partial<Pick<TradingState, 'defaultQuantity' | 'defaultProductType' | 'defaultOrderType'>>) => void
  toggleAITrading: () => void
  setAIStrategy: (strategy: string) => void
  
  // SuperTrade Actions
  executeSuperTrade: (request: SuperTradeRequest) => Promise<SuperTradeResponse>
  analyzeMarket: (request: SuperTradeRequest) => Promise<MarketAnalysis>
  toggleSuperTrade: () => void
  searchEquity: (query: string) => Promise<any[]>
  
  // Reset/Initialize
  initialize: () => Promise<void>
  reset: () => void
}

export const useTradingStore = create<TradingState>()(
  persist(
    (set, get) => ({
      // Initial State
      orders: [],
      activeOrders: [],
      orderHistory: [],
      positions: [],
      holdings: [],
      totalPnL: 0,
      dayPnL: 0,
      availableFunds: 0,
      usedFunds: 0,
      selectedSymbol: null,
      marketQuote: null,
      optionChain: null,
      defaultQuantity: 25,
      defaultProductType: 'INTRADAY',
      defaultOrderType: 'MARKET',
      aiTradingEnabled: false,
      isAIActive: false,
      aiStrategy: null,
      superTradeEnabled: false,
      currentAnalysis: null,
      superTradeHistory: [],
      isLoading: false,
      isPlacingOrder: false,
      isLoadingPositions: false,
      isLoadingOrders: false,
      isAnalyzing: false,

      // Place Order
      placeOrder: async (orderData) => {
        set({ isPlacingOrder: true })
        try {
          const clientId = dhanTradingService.getClientId()
          const correlationId = dhanTradingService.generateCorrelationId()
          
          const fullOrderData: DhanOrderRequest = {
            ...orderData,
            dhanClientId: clientId,
            correlationId,
          }
          
          const response = await dhanTradingService.placeOrder(fullOrderData)
          
          // Update orders list
          const currentOrders = get().orders
          set({ orders: [response, ...currentOrders] })
          
          toast.success(`Order placed successfully: ${response.orderId}`)
          
          // Refresh data
          await get().refreshOrders()
          await get().refreshPositions()
          await get().refreshFunds()
          
          return true
        } catch (error: any) {
          toast.error(error.message || 'Failed to place order')
          return false
        } finally {
          set({ isPlacingOrder: false })
        }
      },

      // Cancel Order
      cancelOrder: async (orderId) => {
        try {
          await dhanTradingService.cancelOrder(orderId)
          toast.success('Order cancelled successfully')
          await get().refreshOrders()
          return true
        } catch (error: any) {
          toast.error(error.message || 'Failed to cancel order')
          return false
        }
      },

      // Modify Order
      modifyOrder: async (orderId, orderData) => {
        try {
          await dhanTradingService.modifyOrder(orderId, orderData)
          toast.success('Order modified successfully')
          await get().refreshOrders()
          return true
        } catch (error: any) {
          toast.error(error.message || 'Failed to modify order')
          return false
        }
      },

      // Refresh Orders
      refreshOrders: async () => {
        set({ isLoadingOrders: true })
        try {
          const ordersResponse = await dhanTradingService.getOrders()
          // Ensure orders is always an array
          const orders = Array.isArray(ordersResponse) ? ordersResponse : []
          
          const activeOrders = orders.filter(order => 
            ['PENDING', 'PART_TRADED', 'TRANSIT'].includes(order.orderStatus)
          )
          const orderHistory = orders.filter(order => 
            !['PENDING', 'PART_TRADED', 'TRANSIT'].includes(order.orderStatus)
          )
          
          set({ orders, activeOrders, orderHistory })
        } catch (error: any) {
          toast.error(error.message || 'Failed to fetch orders')
          set({ orders: [], activeOrders: [], orderHistory: [] })
        } finally {
          set({ isLoadingOrders: false })
        }
      },

      // Refresh Positions
      refreshPositions: async () => {
        set({ isLoadingPositions: true })
        try {
          const positionsResponse = await dhanTradingService.getPositions()
          // Ensure positions is always an array
          const positions = Array.isArray(positionsResponse) ? positionsResponse : []
          
          // Calculate day P&L and total P&L
          const dayPnL = positions.reduce((sum, pos) => sum + pos.unrealizedProfit, 0)
          const totalPnL = positions.reduce((sum, pos) => sum + (pos.realizedProfit + pos.unrealizedProfit), 0)
          
          set({ positions, dayPnL, totalPnL })
        } catch (error: any) {
          toast.error(error.message || 'Failed to fetch positions')
          set({ positions: [], dayPnL: 0, totalPnL: 0 })
        } finally {
          set({ isLoadingPositions: false })
        }
      },

      // Refresh Holdings
      refreshHoldings: async () => {
        try {
          const holdings = await dhanTradingService.getHoldings()
          set({ holdings })
        } catch (error: any) {
          toast.error(error.message || 'Failed to fetch holdings')
        }
      },

      // Refresh Funds
      refreshFunds: async () => {
        try {
          const response = await dhanTradingService.getFunds()
          // Backend returns {status: "success", data: {...}}
          const funds = response.data || response
          set({ 
            availableFunds: funds.availabelBalance || funds.availableFunds || 0,
            usedFunds: funds.utilizedAmount || funds.usedFunds || 0
          })
        } catch (error: any) {
          toast.error(error.message || 'Failed to fetch funds')
        }
      },

      // Get Market Quote
      getMarketQuote: async (securityId, exchangeSegment) => {
        try {
          const quote = await dhanTradingService.getMarketQuote(securityId, exchangeSegment)
          set({ marketQuote: quote })
        } catch (error: any) {
          toast.error(error.message || 'Failed to fetch market quote')
        }
      },

      // Get Option Chain
      getOptionChain: async (underlying) => {
        try {
          const optionChain = await dhanTradingService.getOptionChain(underlying)
          set({ optionChain })
        } catch (error: any) {
          toast.error(error.message || 'Failed to fetch option chain')
        }
      },

      // Set Selected Symbol
      setSelectedSymbol: (symbol) => {
        set({ selectedSymbol: symbol })
      },

      // Update Trading Settings
      updateTradingSettings: (settings) => {
        set(settings)
        toast.success('Trading settings updated')
      },

      // Toggle AI Trading
      toggleAITrading: () => {
        const currentState = get().aiTradingEnabled
        set({ aiTradingEnabled: !currentState })
        
        if (!currentState) {
          toast.success('🤖 AI Trading Enabled')
        } else {
          toast.success('AI Trading Disabled')
          set({ isAIActive: false })
        }
      },

      // Set AI Strategy
      setAIStrategy: (strategy) => {
        set({ aiStrategy: strategy })
        toast.success(`AI Strategy set to: ${strategy}`)
      },

      // Execute SuperTrade
      executeSuperTrade: async (request) => {
        set({ isPlacingOrder: true, isAnalyzing: true })
        try {
          const response = await superTradeService.executeSuperTrade(request)
          
          if (response.success) {
            // Update current analysis
            set({ currentAnalysis: response.analysis })
            
            // Add to SuperTrade history
            const history = get().superTradeHistory
            set({ superTradeHistory: [...history, response] })
            
            // Refresh orders and positions
            await get().refreshOrders()
            await get().refreshPositions()
            
            toast.success(`🚀 SuperTrade executed: ${response.message}`)
          } else {
            toast(`⚡ SuperTrade: ${response.message}`, {
              icon: '⚠️',
              style: { background: '#f59e0b', color: 'white' }
            })
          }
          
          return response
        } catch (error: any) {
          console.error('SuperTrade execution failed:', error)
          toast.error(`SuperTrade failed: ${error.message}`)
          
          return {
            success: false,
            message: error.message || 'SuperTrade execution failed',
            analysis: get().currentAnalysis || {
              trend: 'SIDEWAYS',
              strength: 0,
              volatility: 0,
              pcr: 0,
              maxPain: 0,
              recommendation: 'WAIT',
              confidence: 0,
              reason: 'Error occurred during analysis'
            }
          }
        } finally {
          set({ isPlacingOrder: false, isAnalyzing: false })
        }
      },

      // Analyze Market
      analyzeMarket: async (request) => {
        set({ isAnalyzing: true })
        try {
          const analysis = await superTradeService.analyzeMarket(request)
          set({ currentAnalysis: analysis })
          return analysis
        } catch (error: any) {
          console.error('Market analysis failed:', error)
          toast.error(`Market analysis failed: ${error.message}`)
          
          const fallbackAnalysis: MarketAnalysis = {
            trend: 'SIDEWAYS',
            strength: 0,
            volatility: 0,
            pcr: 0,
            maxPain: 0,
            recommendation: 'WAIT',
            confidence: 0,
            reason: 'Error occurred during analysis'
          }
          
          set({ currentAnalysis: fallbackAnalysis })
          return fallbackAnalysis
        } finally {
          set({ isAnalyzing: false })
        }
      },

      // Toggle SuperTrade
      toggleSuperTrade: () => {
        const state = get()
        set({ superTradeEnabled: !state.superTradeEnabled })
        
        if (!state.superTradeEnabled) {
          toast.success('🧠 SuperTrade Engine Activated')
        } else {
          toast('SuperTrade Engine Deactivated', {
            icon: 'ℹ️',
            style: { background: '#6b7280', color: 'white' }
          })
          set({ currentAnalysis: null })
        }
      },

      // Search Equity
      searchEquity: async (query) => {
        try {
          return await superTradeService.searchEquity(query)
        } catch (error: any) {
          console.error('Equity search failed:', error)
          toast.error(`Search failed: ${error.message}`)
          return []
        }
      },

      // Initialize
      initialize: async () => {
        set({ isLoading: true })
        try {
          await Promise.all([
            get().refreshOrders(),
            get().refreshPositions(),
            get().refreshHoldings(),
            get().refreshFunds(),
          ])
        } catch (error) {
          console.error('Failed to initialize trading data:', error)
        } finally {
          set({ isLoading: false })
        }
      },

      // Reset
      reset: () => {
        set({
          orders: [],
          activeOrders: [],
          orderHistory: [],
          positions: [],
          holdings: [],
          totalPnL: 0,
          dayPnL: 0,
          availableFunds: 0,
          usedFunds: 0,
          selectedSymbol: null,
          marketQuote: null,
          optionChain: null,
          aiTradingEnabled: false,
          isAIActive: false,
          aiStrategy: null,
          superTradeEnabled: false,
          currentAnalysis: null,
          superTradeHistory: [],
        })
      },
    }),
    {
      name: 'dtrade-trading',
      partialize: (state) => ({
        defaultQuantity: state.defaultQuantity,
        defaultProductType: state.defaultProductType,
        defaultOrderType: state.defaultOrderType,
        aiTradingEnabled: state.aiTradingEnabled,
        aiStrategy: state.aiStrategy,
      }),
    }
  )
)
