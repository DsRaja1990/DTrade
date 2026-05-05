import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, AuthResponse, LoginRequest, RegisterRequest } from '../types'
import { authService } from '../services/authService'
import { getDhanConfig, validateDhanCredentials, isTokenExpired } from '../utils/dhanConfig'
import toast from 'react-hot-toast'

interface DhanCredentials {
  client_id: string;
  access_token: string;
}

interface AuthState {
  user: User | null
  token: string | null
  dhanCredentials: DhanCredentials | null
  isLoading: boolean
  login: (credentials: LoginRequest) => Promise<boolean>
  register: (data: RegisterRequest) => Promise<boolean>
  logout: () => void
  initialize: () => void
  updateUser: (user: User) => void
  setDhanCredentials: (credentials: DhanCredentials) => void
  getDhanClientId: () => string | null
  getDhanAccessToken: () => string | null
  initializeDhanCredentials: () => void
  checkDhanTokenExpiry: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      dhanCredentials: null,
      isLoading: false,

      login: async (credentials: LoginRequest) => {
        set({ isLoading: true })
        try {
          const response: AuthResponse = await authService.login(credentials)
          set({
            user: response.user,
            token: response.access_token,
            isLoading: false,
          })
          
          // Initialize DhanHQ credentials after successful login
          get().initializeDhanCredentials()
          
          toast.success(`Welcome back, ${response.user.full_name}!`)
          return true
        } catch (error: any) {
          set({ isLoading: false })
          toast.error(error.message || 'Login failed')
          return false
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true })
        try {
          const response: AuthResponse = await authService.register(data)
          set({
            user: response.user,
            token: response.access_token,
            isLoading: false,
          })
          
          // Initialize DhanHQ credentials after successful registration
          get().initializeDhanCredentials()
          
          toast.success(`Welcome to DTrade, ${response.user.full_name}!`)
          return true
        } catch (error: any) {
          set({ isLoading: false })
          toast.error(error.message || 'Registration failed')
          return false
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          isLoading: false,
        })
        toast.success('Logged out successfully')
      },

      initialize: () => {
        const state = get()
        
        // Initialize DhanHQ credentials if not already set
        if (!state.dhanCredentials) {
          get().initializeDhanCredentials()
        }
        
        // Only try to get user info if we have a token but no user
        if (state.token && !state.user) {
          authService.getCurrentUser(state.token)
            .then((user: User) => {
              set({ user })
            })
            .catch(() => {
              // Token is invalid, clear it
              console.warn('Failed to get current user, clearing auth state')
              set({ user: null, token: null })
            })
        }
      },

      updateUser: (user: User) => {
        set({ user })
      },

      setDhanCredentials: (credentials: DhanCredentials) => {
        const isValid = validateDhanCredentials(credentials.client_id, credentials.access_token)
        if (!isValid) {
          toast.error('Invalid DhanHQ credentials format')
          return
        }

        const isExpired = isTokenExpired(credentials.access_token)
        if (isExpired) {
          toast.error('DhanHQ token has expired. Please provide a new token.')
          return
        }

        set({ dhanCredentials: credentials })
        toast.success('DhanHQ credentials updated successfully')
      },

      getDhanClientId: () => {
        const state = get()
        return state.dhanCredentials?.client_id || null
      },

      getDhanAccessToken: () => {
        const state = get()
        return state.dhanCredentials?.access_token || null
      },

      initializeDhanCredentials: () => {
        const currentState = get()
        
        // Don't override existing valid credentials
        if (currentState.dhanCredentials?.access_token) {
          const isExpired = isTokenExpired(currentState.dhanCredentials.access_token)
          if (!isExpired) {
            return // Keep existing valid credentials
          }
        }

        // Initialize from environment variables
        const config = getDhanConfig()
        if (config.clientId && config.accessToken) {
          const isValid = validateDhanCredentials(config.clientId, config.accessToken)
          const isExpired = isTokenExpired(config.accessToken)
          
          if (isValid && !isExpired) {
            set({
              dhanCredentials: {
                client_id: config.clientId,
                access_token: config.accessToken
              }
            })
            console.log('✅ DhanHQ credentials initialized from environment')
          } else if (isExpired) {
            console.warn('⚠️ DhanHQ token in environment is expired')
            toast.error('DhanHQ token has expired. Please update your credentials.')
          } else {
            console.warn('⚠️ Invalid DhanHQ credentials in environment')
          }
        }
      },

      checkDhanTokenExpiry: () => {
        const state = get()
        if (!state.dhanCredentials?.access_token) {
          return false
        }

        const isExpired = isTokenExpired(state.dhanCredentials.access_token)
        if (isExpired) {
          toast.error('DhanHQ token has expired. Please update your credentials.')
          return false
        }

        return true
      },
    }),
    {
      name: 'dtrade-auth',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        dhanCredentials: state.dhanCredentials,
      }),
    }
  )
)
