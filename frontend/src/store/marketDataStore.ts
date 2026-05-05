import { create } from 'zustand'
import { Quote, MarketFeedData, CandleData, OptionChainData } from '../types'
import { marketDataService } from '../services/marketDataService'
import { useAuthStore } from './authStore'
import toast from 'react-hot-toast'

interface MarketDataState {
  quotes: Record<string, Quote>
  marketFeed: MarketFeedData[]
  candleData: Record<string, CandleData[]>
  optionChain: Record<string, OptionChainData[]>
  watchlist: string[]
  isLoading: boolean

  // Actions
  updateQuote: (quote: Quote) => void
  updateMarketFeed: (data: MarketFeedData) => void
  fetchQuote: (symbol: string, exchange: string) => Promise<void>
  fetchCandleData: (symbol: string, timeframe: string, from?: string, to?: string) => Promise<void>
  fetchOptionChain: (symbol: string, expiry?: string) => Promise<void>
  addToWatchlist: (symbol: string) => void
  removeFromWatchlist: (symbol: string) => void
}

export const useMarketDataStore = create<MarketDataState>((set, get) => ({
  quotes: {},
  marketFeed: [],
  candleData: {},
  optionChain: {},
  watchlist: JSON.parse(localStorage.getItem('dtrade-watchlist') || '["NIFTY", "BANKNIFTY", "RELIANCE", "TCS"]'),
  isLoading: false,

  updateQuote: (quote: Quote) => {
    set(state => ({
      quotes: {
        ...state.quotes,
        [`${quote.symbol}:${quote.exchange}`]: quote,
      },
    }))
  },

  updateMarketFeed: (data: MarketFeedData) => {
    set(state => ({
      marketFeed: [data, ...state.marketFeed.slice(0, 99)], // Keep last 100 updates
    }))
  },

  fetchQuote: async (symbol: string, exchange: string) => {
    const { token } = useAuthStore.getState()
    if (!token) return

    try {
      const quote = await marketDataService.getQuote(token, symbol, exchange)
      get().updateQuote(quote)
    } catch (error: any) {
      toast.error(error.message || 'Failed to fetch quote')
    }
  },

  fetchCandleData: async (symbol: string, timeframe: string, from?: string, to?: string) => {
    const { token } = useAuthStore.getState()
    if (!token) return

    set({ isLoading: true })
    try {
      const data = await marketDataService.getCandleData(token, symbol, timeframe, from, to)
      set(state => ({
        candleData: {
          ...state.candleData,
          [`${symbol}:${timeframe}`]: data,
        },
        isLoading: false,
      }))
    } catch (error: any) {
      set({ isLoading: false })
      toast.error(error.message || 'Failed to fetch candle data')
    }
  },

  fetchOptionChain: async (symbol: string, expiry?: string) => {
    const { token } = useAuthStore.getState()
    if (!token) return

    set({ isLoading: true })
    try {
      const data = await marketDataService.getOptionChain(token, symbol, expiry)
      set(state => ({
        optionChain: {
          ...state.optionChain,
          [`${symbol}:${expiry || 'current'}`]: data,
        },
        isLoading: false,
      }))
    } catch (error: any) {
      set({ isLoading: false })
      toast.error(error.message || 'Failed to fetch option chain')
    }
  },

  addToWatchlist: (symbol: string) => {
    const { watchlist } = get()
    if (!watchlist.includes(symbol)) {
      const newWatchlist = [...watchlist, symbol]
      set({ watchlist: newWatchlist })
      localStorage.setItem('dtrade-watchlist', JSON.stringify(newWatchlist))
    }
  },

  removeFromWatchlist: (symbol: string) => {
    const { watchlist } = get()
    const newWatchlist = watchlist.filter(s => s !== symbol)
    set({ watchlist: newWatchlist })
    localStorage.setItem('dtrade-watchlist', JSON.stringify(newWatchlist))
  },
}))
