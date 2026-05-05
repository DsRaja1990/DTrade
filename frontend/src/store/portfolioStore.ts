import { create } from 'zustand'
import { Portfolio, Position } from '../types'
import { portfolioService } from '../services/portfolioService'
import { useAuthStore } from './authStore'
import toast from 'react-hot-toast'

interface PortfolioState {
  portfolio: Portfolio | null
  positions: Position[]
  isLoading: boolean
  fetchPortfolio: () => Promise<void>
  fetchPositions: () => Promise<void>
  updatePosition: (position: Position) => void
  addPosition: (position: Position) => void
  removePosition: (positionId: string) => void
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  portfolio: null,
  positions: [],
  isLoading: false,

  fetchPortfolio: async () => {
    const { token } = useAuthStore.getState()
    if (!token) return

    set({ isLoading: true })
    try {
      const portfolio = await portfolioService.getPortfolio(token)
      set({ portfolio, isLoading: false })
    } catch (error: any) {
      set({ isLoading: false })
      toast.error(error.message || 'Failed to fetch portfolio')
    }
  },

  fetchPositions: async () => {
    const { token } = useAuthStore.getState()
    if (!token) return

    set({ isLoading: true })
    try {
      const positions = await portfolioService.getPositions(token)
      set({ positions, isLoading: false })
    } catch (error: any) {
      set({ isLoading: false })
      toast.error(error.message || 'Failed to fetch positions')
    }
  },

  updatePosition: (updatedPosition: Position) => {
    const { positions } = get()
    const updatedPositions = positions.map(position =>
      position.id === updatedPosition.id ? updatedPosition : position
    )
    set({ positions: updatedPositions })
  },

  addPosition: (newPosition: Position) => {
    const { positions } = get()
    set({ positions: [...positions, newPosition] })
  },

  removePosition: (positionId: string) => {
    const { positions } = get()
    const filteredPositions = positions.filter(position => position.id !== positionId)
    set({ positions: filteredPositions })
  },
}))
