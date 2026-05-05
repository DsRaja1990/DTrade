/**
 * DhanHQ Configuration Utilities
 * This file handles DhanHQ API configuration and initialization
 */

export interface DhanConfig {
  clientId: string
  accessToken: string
  baseUrl: string
}

/**
 * Get DhanHQ configuration from environment variables or defaults
 */
export const getDhanConfig = (): DhanConfig => {
  return {
    clientId: import.meta.env.VITE_DHAN_CLIENT_ID || "1101317572",
    accessToken: import.meta.env.VITE_DHAN_ACCESS_TOKEN || "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzUzNjE0MzgyLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwMTMxNzU3MiJ9.8Yc6ocmXMwVDOnQn351_ePKwxat76ozpKMoULK0a20-ycLlMC0pQzxPVQ7mMdKGM_cO19-JmNQM52Y2acTyisg",
    baseUrl: "https://api.dhan.co"
  }
}

/**
 * Validate DhanHQ credentials
 */
export const validateDhanCredentials = (clientId: string, accessToken: string): boolean => {
  if (!clientId || !accessToken) {
    return false
  }

  // Basic validation - check if client ID is numeric and access token looks like a JWT
  const clientIdIsValid = /^\d+$/.test(clientId)
  const tokenIsValid = accessToken.split('.').length === 3 // JWT has 3 parts

  return clientIdIsValid && tokenIsValid
}

/**
 * Parse client ID from JWT token
 */
export const parseClientIdFromToken = (accessToken: string): string | null => {
  try {
    const payload = accessToken.split('.')[1]
    const decoded = JSON.parse(atob(payload))
    return decoded.dhanClientId || null
  } catch (error) {
    console.error('Error parsing client ID from token:', error)
    return null
  }
}

/**
 * Check if token is expired
 */
export const isTokenExpired = (accessToken: string): boolean => {
  try {
    const payload = accessToken.split('.')[1]
    const decoded = JSON.parse(atob(payload))
    const expTime = decoded.exp * 1000 // Convert to milliseconds
    return Date.now() > expTime
  } catch (error) {
    console.error('Error checking token expiration:', error)
    return true
  }
}

/**
 * Get token expiration date
 */
export const getTokenExpirationDate = (accessToken: string): Date | null => {
  try {
    const payload = accessToken.split('.')[1]
    const decoded = JSON.parse(atob(payload))
    return new Date(decoded.exp * 1000)
  } catch (error) {
    console.error('Error getting token expiration:', error)
    return null
  }
}
