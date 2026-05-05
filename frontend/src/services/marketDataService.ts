import { Quote, CandleData, OptionChainData, Instrument } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

class MarketDataService {
  private async authenticatedRequest<T>(
    endpoint: string,
    token: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Network error' }))
      throw new Error(error.message || `HTTP ${response.status}`)
    }

    return response.json()
  }

  async getQuote(token: string, symbol: string, exchange: string): Promise<Quote> {
    const params = new URLSearchParams({ symbol, exchange })
    return this.authenticatedRequest<Quote>(`/api/market-data/quote?${params}`, token)
  }

  async getQuotes(token: string, symbols: string[]): Promise<Quote[]> {
    return this.authenticatedRequest<Quote[]>('/api/market-data/quotes', token, {
      method: 'POST',
      body: JSON.stringify({ symbols }),
    })
  }

  async getCandleData(
    token: string,
    symbol: string,
    timeframe: string,
    from?: string,
    to?: string
  ): Promise<CandleData[]> {
    const params = new URLSearchParams({
      symbol,
      timeframe,
      ...(from && { from }),
      ...(to && { to }),
    })
    
    return this.authenticatedRequest<CandleData[]>(`/api/market-data/candles?${params}`, token)
  }

  async getOptionChain(token: string, symbol: string, expiry?: string): Promise<OptionChainData[]> {
    const params = new URLSearchParams({
      symbol,
      ...(expiry && { expiry }),
    })
    
    return this.authenticatedRequest<OptionChainData[]>(`/api/market-data/option-chain?${params}`, token)
  }

  async getInstruments(token: string, exchange?: string): Promise<Instrument[]> {
    const params = new URLSearchParams({
      ...(exchange && { exchange }),
    })
    
    return this.authenticatedRequest<Instrument[]>(`/api/market-data/instruments?${params}`, token)
  }

  async searchInstruments(token: string, query: string): Promise<Instrument[]> {
    const params = new URLSearchParams({ q: query })
    return this.authenticatedRequest<Instrument[]>(`/api/market-data/search?${params}`, token)
  }

  async getMarketStatus(token: string): Promise<{
    nse: { status: string; timestamp: string }
    bse: { status: string; timestamp: string }
  }> {
    return this.authenticatedRequest('/api/market-data/status', token)
  }

  async getIndices(token: string): Promise<Quote[]> {
    return this.authenticatedRequest<Quote[]>('/api/market-data/indices', token)
  }

  async getTechnicalIndicators(
    token: string,
    symbol: string,
    indicator: string,
    period: number,
    timeframe: string
  ): Promise<{ timestamp: string; value: number }[]> {
    const params = new URLSearchParams({
      symbol,
      indicator,
      period: period.toString(),
      timeframe,
    })
    
    return this.authenticatedRequest(`/api/market-data/indicators?${params}`, token)
  }

  async getTopGainers(token: string, exchange = 'NSE'): Promise<Quote[]> {
    const params = new URLSearchParams({ exchange })
    return this.authenticatedRequest<Quote[]>(`/api/market-data/top-gainers?${params}`, token)
  }

  async getTopLosers(token: string, exchange = 'NSE'): Promise<Quote[]> {
    const params = new URLSearchParams({ exchange })
    return this.authenticatedRequest<Quote[]>(`/api/market-data/top-losers?${params}`, token)
  }

  async getMostActive(token: string, exchange = 'NSE'): Promise<Quote[]> {
    const params = new URLSearchParams({ exchange })
    return this.authenticatedRequest<Quote[]>(`/api/market-data/most-active?${params}`, token)
  }
}

export const marketDataService = new MarketDataService()
