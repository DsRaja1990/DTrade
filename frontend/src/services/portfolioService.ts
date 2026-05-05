import { Portfolio, Position } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

class PortfolioService {
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

  async getPortfolio(token: string): Promise<Portfolio> {
    return this.authenticatedRequest<Portfolio>('/api/portfolio', token)
  }

  async getPositions(token: string): Promise<Position[]> {
    return this.authenticatedRequest<Position[]>('/api/portfolio/positions', token)
  }

  async getPosition(token: string, positionId: string): Promise<Position> {
    return this.authenticatedRequest<Position>(`/api/portfolio/positions/${positionId}`, token)
  }

  async refreshPortfolio(token: string): Promise<Portfolio> {
    return this.authenticatedRequest<Portfolio>('/api/portfolio/refresh', token, {
      method: 'POST',
    })
  }

  async getPortfolioHistory(
    token: string,
    startDate: string,
    endDate: string
  ): Promise<{ date: string; value: number }[]> {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    })
    
    return this.authenticatedRequest<{ date: string; value: number }[]>(
      `/api/portfolio/history?${params}`,
      token
    )
  }

  async getPerformanceMetrics(token: string): Promise<{
    total_return: number
    annualized_return: number
    sharpe_ratio: number
    max_drawdown: number
    volatility: number
    beta: number
  }> {
    return this.authenticatedRequest('/api/portfolio/metrics', token)
  }
}

export const portfolioService = new PortfolioService()
