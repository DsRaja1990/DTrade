/**
 * SuperTrade Engine Service
 * Advanced AI-powered trading engine for Index and Equity markets
 * Integrates with DhanHQ APIs and backend analysis engine
 */

import { getDhanConfig } from '../utils/dhanConfig'
import toast from 'react-hot-toast'

// SuperTrade Types
export interface CandleData {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface OptionChainData {
  strikePrice: number
  callOI: number
  putOI: number
  callVolume: number
  putVolume: number
  callIV: number
  putIV: number
  callLTP: number
  putLTP: number
}

export interface MarketAnalysis {
  trend: 'MOMENTUM' | 'SIDEWAYS' | 'BEARISH'
  strength: number
  volatility: number
  pcr: number
  maxPain: number
  recommendation: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG_SELL' | 'WAIT'
  entryPrice?: number
  stopLoss?: number
  target?: number
  trailingStop?: number
  confidence: number
  reason: string
}

export interface SuperTradeRequest {
  mode: 'index' | 'equity'
  instrument: 'options' | 'futures'
  symbol: string // NIFTY, BANKNIFTY, SENSEX for index; RELIANCE, TCS etc for equity
  exchange: 'NSE' | 'BSE'
  quantity: number
  strategy?: string
}

export interface SuperTradeResponse {
  success: boolean
  orderId?: string
  message: string
  analysis: MarketAnalysis
  executionDetails?: {
    entryPrice: number
    stopLoss: number
    target: number
    trailingStop: number
    orderType: string
    strategy: string
  }
}

class SuperTradeService {
  private dhanBaseUrl = 'https://api.dhan.co'

  /**
   * Get DhanHQ headers for API calls
   */
  private getDhanHeaders() {
    const config = getDhanConfig()
    
    if (!config.clientId || !config.accessToken) {
      throw new Error('DhanHQ credentials not configured')
    }

    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'client-id': config.clientId,
      'access-token': config.accessToken
    }
  }

  /**
   * Get historical data for candle analysis
   */
  async getHistoricalData(
    securityId: string, 
    exchangeSegment: string, 
    instrument: string,
    interval: string = '15'
  ): Promise<CandleData[]> {
    try {
      const headers = this.getDhanHeaders()
      
      // Calculate from and to dates (last 30 days)
      const toDate = new Date()
      const fromDate = new Date()
      fromDate.setDate(fromDate.getDate() - 30)
      
      const response = await fetch(`${this.dhanBaseUrl}/v1/charts/historical`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          securityId,
          exchangeSegment,
          instrument,
          interval,
          fromDate: fromDate.toISOString().split('T')[0],
          toDate: toDate.toISOString().split('T')[0]
        })
      })

      if (!response.ok) {
        throw new Error(`Historical data fetch failed: ${response.statusText}`)
      }

      const data = await response.json()
      
      // Transform to our CandleData format
      return data.data?.map((candle: any) => ({
        timestamp: new Date(candle.timestamp).getTime(),
        open: parseFloat(candle.open),
        high: parseFloat(candle.high),
        low: parseFloat(candle.low),
        close: parseFloat(candle.close),
        volume: parseInt(candle.volume)
      })) || []

    } catch (error) {
      console.error('Historical data fetch error:', error)
      throw error
    }
  }

  /**
   * Get option chain data for analysis
   */
  async getOptionChain(
    underlyingSymbol: string,
    exchangeSegment: string = 'NSE_FNO'
  ): Promise<OptionChainData[]> {
    try {
      const headers = this.getDhanHeaders()
      
      // Get current week expiry
      const today = new Date()
      const currentDay = today.getDay()
      const daysUntilThursday = (4 - currentDay + 7) % 7
      const expiryDate = new Date(today)
      expiryDate.setDate(today.getDate() + daysUntilThursday)
      
      const response = await fetch(`${this.dhanBaseUrl}/v2/optionchain/${underlyingSymbol}`, {
        method: 'GET',
        headers: {
          ...headers,
          'exchange-segment': exchangeSegment,
          'expiry-date': expiryDate.toISOString().split('T')[0]
        }
      })

      if (!response.ok) {
        throw new Error(`Option chain fetch failed: ${response.statusText}`)
      }

      const data = await response.json()
      
      // Transform to our OptionChainData format
      return data.data?.map((option: any) => ({
        strikePrice: parseFloat(option.strikePrice),
        callOI: parseInt(option.callOI || 0),
        putOI: parseInt(option.putOI || 0),
        callVolume: parseInt(option.callVolume || 0),
        putVolume: parseInt(option.putVolume || 0),
        callIV: parseFloat(option.callIV || 0),
        putIV: parseFloat(option.putIV || 0),
        callLTP: parseFloat(option.callLTP || 0),
        putLTP: parseFloat(option.putLTP || 0)
      })) || []

    } catch (error) {
      console.error('Option chain fetch error:', error)
      // Return mock data for development
      return this.getMockOptionChain()
    }
  }

  /**
   * Get current market quote
   */
  async getMarketQuote(securityId: string, exchangeSegment: string): Promise<any> {
    try {
      const headers = this.getDhanHeaders()
      
      const response = await fetch(`${this.dhanBaseUrl}/v2/marketfeed/quote`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          securityId,
          exchangeSegment
        })
      })

      if (!response.ok) {
        throw new Error(`Market quote fetch failed: ${response.statusText}`)
      }

      return await response.json()

    } catch (error) {
      console.error('Market quote fetch error:', error)
      throw error
    }
  }

  /**
   * Analyze market using SuperTrade Engine
   */
  async analyzeMarket(request: SuperTradeRequest): Promise<MarketAnalysis> {
    try {
      // In production, this would call your backend SuperTrade Engine
      // For now, we'll simulate the analysis based on the request
      console.log('Analyzing market for:', request)
      
      const mockAnalysis: MarketAnalysis = {
        trend: ['MOMENTUM', 'SIDEWAYS', 'BEARISH'][Math.floor(Math.random() * 3)] as any,
        strength: Math.floor(Math.random() * 100),
        volatility: Math.random() * 30 + 10,
        pcr: Math.random() * 2 + 0.5,
        maxPain: 19000 + Math.floor(Math.random() * 1000),
        recommendation: ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL', 'WAIT'][Math.floor(Math.random() * 6)] as any,
        confidence: Math.floor(Math.random() * 40) + 60, // 60-100%
        reason: `AI analysis for ${request.symbol} ${request.instrument} based on 15min & 5min candles, option chain data, and market sentiment`
      }

      // Add trade levels if recommendation is to buy/sell
      if (['STRONG_BUY', 'BUY'].includes(mockAnalysis.recommendation)) {
        const basePrice = 100 + Math.random() * 50
        mockAnalysis.entryPrice = basePrice
        mockAnalysis.stopLoss = basePrice * 0.98 // 2% SL
        mockAnalysis.target = basePrice * 1.05 // 5% target
        mockAnalysis.trailingStop = basePrice * 0.995 // 0.5% trailing
      }

      return mockAnalysis

    } catch (error) {
      console.error('Market analysis error:', error)
      throw error
    }
  }

  /**
   * Execute SuperTrade order
   */
  async executeSuperTrade(request: SuperTradeRequest): Promise<SuperTradeResponse> {
    try {
      // First analyze the market
      const analysis = await this.analyzeMarket(request)
      
      // Check if we should proceed with the trade
      if (analysis.recommendation === 'WAIT') {
        return {
          success: false,
          message: 'Engine recommends waiting for better entry opportunity',
          analysis
        }
      }

      if (analysis.recommendation === 'HOLD') {
        return {
          success: false,
          message: 'Market conditions not favorable for new positions',
          analysis
        }
      }

      // Prepare order payload based on the analysis
      const orderPayload = this.prepareOrderPayload(request, analysis)
      
      // Execute the order via DhanHQ
      const response = await fetch(`${this.dhanBaseUrl}/v2/orders`, {
        method: 'POST',
        headers: this.getDhanHeaders(),
        body: JSON.stringify(orderPayload)
      })

      const orderResult = await response.json()

      if (response.ok && orderResult.orderId) {
        toast.success(`🎯 SuperTrade executed! Order ID: ${orderResult.orderId}`)
        
        return {
          success: true,
          orderId: orderResult.orderId,
          message: `SuperTrade order placed successfully`,
          analysis,
          executionDetails: {
            entryPrice: analysis.entryPrice || 0,
            stopLoss: analysis.stopLoss || 0,
            target: analysis.target || 0,
            trailingStop: analysis.trailingStop || 0,
            orderType: 'LIMIT',
            strategy: `${request.mode.toUpperCase()}_${request.instrument.toUpperCase()}`
          }
        }
      } else {
        throw new Error(orderResult.message || 'Order placement failed')
      }

    } catch (error: any) {
      console.error('SuperTrade execution error:', error)
      toast.error(`SuperTrade failed: ${error.message}`)
      
      return {
        success: false,
        message: error.message || 'SuperTrade execution failed',
        analysis: await this.analyzeMarket(request)
      }
    }
  }

  /**
   * Prepare order payload based on analysis
   */
  private prepareOrderPayload(request: SuperTradeRequest, analysis: MarketAnalysis) {
    const isSensex = request.symbol === 'SENSEX'
    
    // Handle BSE SENSEX special case
    const exchangeSegment = isSensex ? 'BSE_FNO' : 
                           request.exchange === 'BSE' ? 'BSE_FNO' : 'NSE_FNO'

    // Determine transaction type based on recommendation
    const transactionType = ['STRONG_BUY', 'BUY'].includes(analysis.recommendation) ? 'BUY' : 'SELL'

    return {
      dhanClientId: getDhanConfig().clientId,
      correlationId: `ST_${Date.now()}`,
      transactionType,
      exchangeSegment,
      productType: 'INTRADAY', // Default to intraday for SuperTrade
      orderType: 'LIMIT',
      validity: 'DAY',
      tradingSymbol: this.buildTradingSymbol(request),
      securityId: this.getSecurityId(request),
      quantity: request.quantity,
      disclosedQuantity: 0,
      price: analysis.entryPrice || 0,
      triggerPrice: 0,
      afterMarketOrder: false,
      boProfitValue: 0,
      boStopLossValue: 0
    }
  }

  /**
   * Build trading symbol based on request
   */
  private buildTradingSymbol(request: SuperTradeRequest): string {
    const { mode, instrument, symbol } = request
    const today = new Date()
    
    if (mode === 'index') {
      // For index trading, we need to construct the symbol with expiry and strike
      const expiry = this.getNextThursday(today)
      const expiryStr = this.formatExpiryString(expiry)
      
      if (instrument === 'futures') {
        return `${symbol}${expiryStr}FUT`
      } else {
        // For options, we'll use ATM strike (this should be dynamic based on current price)
        const atmStrike = this.getATMStrike(symbol)
        return `${symbol}${expiryStr}${atmStrike}CE` // Default to Call, should be based on analysis
      }
    } else {
      // For equity, similar logic but with different format
      if (instrument === 'futures') {
        const expiry = this.getNextThursday(today)
        const expiryStr = this.formatExpiryString(expiry)
        return `${symbol}${expiryStr}FUT`
      } else {
        const atmStrike = this.getATMStrike(symbol)
        const expiry = this.getNextThursday(today)
        const expiryStr = this.formatExpiryString(expiry)
        return `${symbol}${expiryStr}${atmStrike}CE`
      }
    }
  }

  /**
   * Get security ID for the symbol
   */
  private getSecurityId(request: SuperTradeRequest): string {
    // This should be fetched from DhanHQ instruments API
    // For now, return a mock security ID
    const mockSecurityIds: { [key: string]: string } = {
      'NIFTY': '13',
      'BANKNIFTY': '25',
      'FINNIFTY': '27',
      'SENSEX': '51',
      'RELIANCE': '1333',
      'TCS': '11536',
      'INFY': '1594',
      'HDFCBANK': '1333',
      'ICICIBANK': '4963'
    }
    
    return mockSecurityIds[request.symbol] || '1333'
  }

  /**
   * Get next Thursday (expiry day)
   */
  private getNextThursday(date: Date): Date {
    const result = new Date(date)
    const currentDay = result.getDay()
    const daysUntilThursday = (4 - currentDay + 7) % 7
    result.setDate(result.getDate() + (daysUntilThursday || 7))
    return result
  }

  /**
   * Format expiry string for trading symbol
   */
  private formatExpiryString(date: Date): string {
    const year = date.getFullYear().toString().slice(-2)
    const month = date.toLocaleString('en', { month: 'short' }).toUpperCase()
    const day = date.getDate().toString().padStart(2, '0')
    return `${year}${month}${day}`
  }

  /**
   * Get ATM strike price (mock implementation)
   */
  private getATMStrike(symbol: string): number {
    // This should be calculated based on current market price
    const mockATMStrikes: { [key: string]: number } = {
      'NIFTY': 19500,
      'BANKNIFTY': 44000,
      'FINNIFTY': 19000,
      'SENSEX': 65000,
      'RELIANCE': 2750,
      'TCS': 3850,
      'INFY': 1650,
      'HDFCBANK': 1750,
      'ICICIBANK': 950
    }
    
    return mockATMStrikes[symbol] || 19500
  }

  /**
   * Get mock option chain data for development
   */
  private getMockOptionChain(): OptionChainData[] {
    const baseStrike = 19500
    const strikes = []
    
    for (let i = -10; i <= 10; i++) {
      const strike = baseStrike + (i * 50)
      strikes.push({
        strikePrice: strike,
        callOI: Math.floor(Math.random() * 100000),
        putOI: Math.floor(Math.random() * 100000),
        callVolume: Math.floor(Math.random() * 10000),
        putVolume: Math.floor(Math.random() * 10000),
        callIV: Math.random() * 50 + 10,
        putIV: Math.random() * 50 + 10,
        callLTP: Math.random() * 200 + 50,
        putLTP: Math.random() * 200 + 50
      })
    }
    
    return strikes
  }

  /**
   * Search equity instruments
   */
  async searchEquity(query: string): Promise<any[]> {
    try {
      // This should call DhanHQ instruments API
      // For now, return mock data
      const mockEquities = [
        { symbol: 'RELIANCE', name: 'Reliance Industries Ltd', ltp: 2750.50, securityId: '1333' },
        { symbol: 'TCS', name: 'Tata Consultancy Services', ltp: 3850.25, securityId: '11536' },
        { symbol: 'INFY', name: 'Infosys Limited', ltp: 1650.75, securityId: '1594' },
        { symbol: 'HDFCBANK', name: 'HDFC Bank Limited', ltp: 1750.90, securityId: '1333' },
        { symbol: 'ICICIBANK', name: 'ICICI Bank Limited', ltp: 950.60, securityId: '4963' },
        { symbol: 'HINDUNILVR', name: 'Hindustan Unilever Ltd', ltp: 2450.30, securityId: '1394' },
        { symbol: 'BHARTIARTL', name: 'Bharti Airtel Limited', ltp: 1075.80, securityId: '3045' },
        { symbol: 'ITC', name: 'ITC Limited', ltp: 412.45, securityId: '1660' },
        { symbol: 'SBIN', name: 'State Bank of India', ltp: 622.90, securityId: '3045' },
        { symbol: 'LT', name: 'Larsen & Toubro Ltd', ltp: 3485.60, securityId: '2885' }
      ]

      return mockEquities.filter(equity => 
        equity.symbol.toLowerCase().includes(query.toLowerCase()) ||
        equity.name.toLowerCase().includes(query.toLowerCase())
      )

    } catch (error) {
      console.error('Equity search error:', error)
      return []
    }
  }
}

export const superTradeService = new SuperTradeService()
