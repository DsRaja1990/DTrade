import { useAuthStore } from '../store/authStore'

export interface DhanOrderRequest {
  dhanClientId: string;
  correlationId: string;
  transactionType: 'BUY' | 'SELL';
  exchangeSegment: 'NSE_EQ' | 'NSE_FNO' | 'BSE_EQ' | 'BSE_FNO' | 'MCX_COMM' | 'NSE_CURRENCY' | 'BSE_CURRENCY';
  productType: 'INTRADAY' | 'CNC' | 'MARGIN' | 'CO' | 'BO';
  orderType: 'LIMIT' | 'MARKET' | 'STOP_LOSS' | 'STOP_LOSS_MARKET';
  validity: 'DAY' | 'IOC';
  securityId: string;
  quantity: number;
  disclosedQuantity?: number;
  price?: number;
  triggerPrice?: number;
  afterMarketOrder?: boolean;
  amoTime?: 'OPEN' | 'OPEN_PLUS_1' | 'OPEN_PLUS_2' | 'OPEN_PLUS_3' | 'OPEN_PLUS_4' | 'OPEN_PLUS_5';
  boProfitValue?: number;
  boStopLossValue?: number;
}

export interface DhanOrderResponse {
  orderId: string;
  dhanClientId: string;
  orderStatus: string;
  transactionType: string;
  exchangeSegment: string;
  productType: string;
  orderType: string;
  validity: string;
  tradingSymbol: string;
  securityId: string;
  quantity: number;
  disclosedQuantity: number;
  price: number;
  triggerPrice: number;
  afterMarketOrder: boolean;
  boProfitValue: number;
  boStopLossValue: number;
  orderTime: string;
  createTime: string;
  updateTime: string;
  exchangeTime: string;
  drvExpiryDate: string | null;
  drvOptionType: string | null;
  drvStrikePrice: number;
  omsErrorCode: string | null;
  omsErrorDescription: string | null;
}

export interface DhanPosition {
  dhanClientId: string;
  exchangeSegment: string;
  productType: string;
  securityId: string;
  tradingSymbol: string;
  positionType: 'LONG' | 'SHORT' | 'CLOSED';
  quantity: number;
  costPrice: number;
  buyAvg: number;
  buyQty: number;
  sellAvg: number;
  sellQty: number;
  netQty: number;
  realizedProfit: number;
  unrealizedProfit: number;
  rbiReferenceRate: number;
  multiplier: number;
  carryForwardFlag: string;
  drvExpiryDate: string | null;
  drvOptionType: string | null;
  drvStrikePrice: number;
}

export interface DhanHolding {
  isin: string;
  tradingSymbol: string;
  exchangeSegment: string;
  quantity: number;
  t1Quantity: number;
  averagePrice: number;
  collateralQuantity: number;
  dpQty: number;
  sellableQty: number;
}

// Use our backend instead of direct Dhan API calls
const BACKEND_API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

class DhanTradingService {
  private getHeaders() {
    return {
      'Content-Type': 'application/json',
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    // Remove /v2 prefix and use backend API
    const cleanEndpoint = endpoint.replace('/v2', '')
    const url = `${BACKEND_API_URL}/api${cleanEndpoint}`
    
    const response = await fetch(url, {
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Network error' }))
      throw new Error(error.message || `HTTP ${response.status}`)
    }

    const result = await response.json()
    
    // Backend wraps responses in {status, data, ...}
    // Extract data if it exists, otherwise return result
    if (result && typeof result === 'object' && 'data' in result) {
      return result.data as T
    }
    
    return result
  }

  // Place Order
  async placeOrder(orderData: DhanOrderRequest): Promise<DhanOrderResponse> {
    return this.request<DhanOrderResponse>('/v2/orders', {
      method: 'POST',
      body: JSON.stringify(orderData),
    })
  }

  // Get Orders
  async getOrders(): Promise<DhanOrderResponse[]> {
    return this.request<DhanOrderResponse[]>('/v2/orders')
  }

  // Get Order by ID
  async getOrder(orderId: string): Promise<DhanOrderResponse> {
    return this.request<DhanOrderResponse>(`/v2/orders/${orderId}`)
  }

  // Modify Order
  async modifyOrder(orderId: string, orderData: Partial<DhanOrderRequest>): Promise<DhanOrderResponse> {
    return this.request<DhanOrderResponse>(`/v2/orders/${orderId}`, {
      method: 'PUT',
      body: JSON.stringify(orderData),
    })
  }

  // Cancel Order
  async cancelOrder(orderId: string): Promise<DhanOrderResponse> {
    return this.request<DhanOrderResponse>(`/v2/orders/${orderId}`, {
      method: 'DELETE',
    })
  }

  // Get Positions
  async getPositions(): Promise<DhanPosition[]> {
    return this.request<DhanPosition[]>('/v2/positions')
  }

  // Get Holdings
  async getHoldings(): Promise<DhanHolding[]> {
    return this.request<DhanHolding[]>('/v2/holdings')
  }

  // Get Funds
  async getFunds(): Promise<any> {
    return this.request<any>('/v2/fundlimit')
  }

  // Get Market Quote
  async getMarketQuote(securityId: string, exchangeSegment: string): Promise<any> {
    return this.request<any>(`/v2/marketfeed/quote`, {
      method: 'POST',
      body: JSON.stringify({
        securityId,
        exchangeSegment,
      }),
    })
  }

  // Get Option Chain
  async getOptionChain(underlying: string): Promise<any> {
    return this.request<any>(`/v2/optionchain/${underlying}`)
  }

  // Get Historical Data
  async getHistoricalData(params: {
    securityId: string;
    exchangeSegment: string;
    instrument: string;
    fromDate: string;
    toDate: string;
  }): Promise<any> {
    const queryParams = new URLSearchParams(params as any).toString()
    return this.request<any>(`/v2/charts/historical?${queryParams}`)
  }

  // Get Intraday Data
  async getIntradayData(params: {
    securityId: string;
    exchangeSegment: string;
    instrument: string;
  }): Promise<any> {
    const queryParams = new URLSearchParams(params as any).toString()
    return this.request<any>(`/v2/charts/intraday?${queryParams}`)
  }

  // Helper method to create correlation ID
  generateCorrelationId(): string {
    return `dtrade_${Date.now()}_${Math.random().toString(36).substring(7)}`
  }

  // Helper method to get client ID
  getClientId(): string {
    return useAuthStore.getState().getDhanClientId() || ''
  }
}

export const dhanTradingService = new DhanTradingService()
