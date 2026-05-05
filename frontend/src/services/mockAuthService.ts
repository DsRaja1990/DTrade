/**
 * Mock Authentication Service for Development/Testing
 * This service provides test credentials when the backend is not available
 */

import { 
  User, 
  AuthResponse, 
  LoginRequest, 
  RegisterRequest
} from '../types'

// Test credentials for development
export const TEST_CREDENTIALS = {
  // Demo Trader Account
  demo: {
    email: 'demo@dtrade.com',
    password: 'demo123',
    user: {
      id: '1',
      email: 'demo@dtrade.com',
      username: 'demo_trader',
      full_name: 'Demo Trader',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  },
  
  // Test Trader Account
  test: {
    email: 'test@dtrade.com',
    password: 'test123',
    user: {
      id: '2',
      email: 'test@dtrade.com',
      username: 'test_trader',
      full_name: 'Test Trader',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  },

  // Admin Account
  admin: {
    email: 'admin@dtrade.com',
    password: 'admin123',
    user: {
      id: '3',
      email: 'admin@dtrade.com',
      username: 'admin',
      full_name: 'DTrade Admin',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  },

  // Professional Trader
  trader: {
    email: 'trader@dtrade.com',
    password: 'trader123',
    user: {
      id: '4',
      email: 'trader@dtrade.com',
      username: 'pro_trader',
      full_name: 'Professional Trader',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  },

  // Institutional Account
  institution: {
    email: 'institution@dtrade.com',
    password: 'institution123',
    user: {
      id: '5',
      email: 'institution@dtrade.com',
      username: 'institutional',
      full_name: 'Institutional Trader',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  }
}

class MockAuthService {
  private generateToken(userId: string): string {
    // Generate a mock JWT-like token
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
    const payload = btoa(JSON.stringify({
      sub: userId,
      email: Object.values(TEST_CREDENTIALS).find(cred => cred.user.id === userId)?.user.email,
      exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60), // 24 hours
      iat: Math.floor(Date.now() / 1000),
      iss: 'dtrade-mock'
    }))
    const signature = btoa('mock_signature_' + userId)
    
    return `${header}.${payload}.${signature}`
  }

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    // Add artificial delay to simulate network request
    await new Promise(resolve => setTimeout(resolve, 1000))

    // Find matching test credential
    const testCred = Object.values(TEST_CREDENTIALS).find(
      cred => cred.email === credentials.email && cred.password === credentials.password
    )

    if (!testCred) {
      throw new Error('Invalid email or password')
    }

    const accessToken = this.generateToken(testCred.user.id)

    return {
      access_token: accessToken,
      token_type: 'bearer',
      user: testCred.user,
    }
  }

  async register(data: RegisterRequest): Promise<AuthResponse> {
    // Add artificial delay to simulate network request
    await new Promise(resolve => setTimeout(resolve, 1500))

    // Check if email already exists
    const existingUser = Object.values(TEST_CREDENTIALS).find(
      cred => cred.email === data.email
    )

    if (existingUser) {
      throw new Error('Email already registered')
    }

    // Create new user
    const newUser: User = {
      id: Date.now().toString(),
      email: data.email,
      username: data.username,
      full_name: data.full_name,
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    const accessToken = this.generateToken(newUser.id)

    return {
      access_token: accessToken,
      token_type: 'bearer',
      user: newUser,
    }
  }

  async getCurrentUser(token: string): Promise<User> {
    // Add artificial delay to simulate network request
    await new Promise(resolve => setTimeout(resolve, 500))

    try {
      // Decode mock token to get user ID
      const payload = JSON.parse(atob(token.split('.')[1]))
      const userId = payload.sub

      // Find user by ID
      const testCred = Object.values(TEST_CREDENTIALS).find(
        cred => cred.user.id === userId
      )

      if (!testCred) {
        throw new Error('User not found')
      }

      return testCred.user
    } catch (error) {
      throw new Error('Invalid token')
    }
  }

  async updateUser(token: string, userData: Partial<User>): Promise<User> {
    const currentUser = await this.getCurrentUser(token)
    
    return {
      ...currentUser,
      ...userData,
      updated_at: new Date().toISOString(),
    }
  }

  async changePassword(
    _token: string, 
    _currentPassword: string, 
    _newPassword: string
  ): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 800))
    // Mock implementation - always succeeds
  }

  async requestPasswordReset(_email: string): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 1000))
    // Mock implementation - always succeeds
  }

  async resetPassword(_token: string, _newPassword: string): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 1000))
    // Mock implementation - always succeeds
  }

  async refreshToken(token: string): Promise<{ access_token: string }> {
    const user = await this.getCurrentUser(token)
    const newToken = this.generateToken(user.id)
    
    return {
      access_token: newToken
    }
  }

  async logout(_token: string): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 300))
    // Mock implementation - always succeeds
  }
}

export const mockAuthService = new MockAuthService()
