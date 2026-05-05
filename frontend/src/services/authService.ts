import { 
  User, 
  AuthResponse, 
  LoginRequest, 
  RegisterRequest
} from '../types'
import { mockAuthService } from './mockAuthService'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const USE_MOCK_AUTH = import.meta.env.VITE_USE_MOCK_AUTH === 'true'

class AuthService {
  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
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

  private async authenticatedRequest<T>(
    endpoint: string,
    token: string,
    options: RequestInit = {}
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    })
  }

  private async isBackendAvailable(): Promise<boolean> {
    if (USE_MOCK_AUTH) {
      return false
    }

    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        timeout: 3000,
      } as RequestInit)
      return response.ok
    } catch {
      return false
    }
  }

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    // Check if backend is available or if we should use mock auth
    const backendAvailable = await this.isBackendAvailable()
    
    if (!backendAvailable) {
      console.log('🔄 Using mock authentication (backend not available)')
      return mockAuthService.login(credentials)
    }

    // Convert to form data as FastAPI OAuth2 expects form data
    const formData = new FormData()
    formData.append('username', credentials.email)
    formData.append('password', credentials.password)

    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    const tokenData = await response.json()
    
    // Get user info with the token
    const user = await this.getCurrentUser(tokenData.access_token)
    
    return {
      access_token: tokenData.access_token,
      token_type: tokenData.token_type,
      user,
    }
  }

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const backendAvailable = await this.isBackendAvailable()
    
    if (!backendAvailable) {
      console.log('🔄 Using mock authentication (backend not available)')
      return mockAuthService.register(data)
    }

    await this.request<User>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })

    // Auto-login after registration
    return this.login({
      email: data.email,
      password: data.password,
    })
  }

  async getCurrentUser(token: string): Promise<User> {
    const backendAvailable = await this.isBackendAvailable()
    
    if (!backendAvailable) {
      return mockAuthService.getCurrentUser(token)
    }

    return this.authenticatedRequest<User>('/api/users/me', token)
  }

  async updateUser(token: string, userData: Partial<User>): Promise<User> {
    const backendAvailable = await this.isBackendAvailable()
    
    if (!backendAvailable) {
      return mockAuthService.updateUser(token, userData)
    }

    return this.authenticatedRequest<User>('/api/users/me', token, {
      method: 'PUT',
      body: JSON.stringify(userData),
    })
  }

  async changePassword(
    token: string, 
    currentPassword: string, 
    newPassword: string
  ): Promise<void> {
    const backendAvailable = await this.isBackendAvailable()
    
    if (!backendAvailable) {
      return mockAuthService.changePassword(token, currentPassword, newPassword)
    }

    await this.authenticatedRequest('/api/users/change-password', token, {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    })
  }

  async requestPasswordReset(email: string): Promise<void> {
    const backendAvailable = await this.isBackendAvailable()
    
    if (!backendAvailable) {
      return mockAuthService.requestPasswordReset(email)
    }

    await this.request('/api/auth/password-reset-request', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }

  async resetPassword(token: string, newPassword: string): Promise<void> {
    const backendAvailable = await this.isBackendAvailable()
    
    if (!backendAvailable) {
      return mockAuthService.resetPassword(token, newPassword)
    }

    await this.request('/api/auth/password-reset-confirm', {
      method: 'POST',
      body: JSON.stringify({
        token,
        new_password: newPassword,
      }),
    })
  }

  async refreshToken(token: string): Promise<{ access_token: string }> {
    const backendAvailable = await this.isBackendAvailable()
    
    if (!backendAvailable) {
      return mockAuthService.refreshToken(token)
    }

    return this.authenticatedRequest('/api/auth/refresh', token, {
      method: 'POST',
    })
  }

  async logout(token: string): Promise<void> {
    const backendAvailable = await this.isBackendAvailable()
    
    if (!backendAvailable) {
      return mockAuthService.logout(token)
    }

    try {
      await this.authenticatedRequest('/api/auth/logout', token, {
        method: 'POST',
      })
    } catch (error) {
      // Ignore logout errors - token might already be invalid
      console.warn('Logout request failed:', error)
    }
  }
}

export const authService = new AuthService()
