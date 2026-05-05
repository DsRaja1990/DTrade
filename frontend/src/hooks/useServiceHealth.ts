import { useState, useEffect, useCallback, useRef } from 'react'
import toast from 'react-hot-toast'

const BACKEND_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface ServiceStatus {
  name: string
  port: number
  status: 'running' | 'stopped' | 'unknown'
  last_check?: string
  uptime?: string
}

interface ServicesHealth {
  backend: 'healthy' | 'unhealthy' | 'checking'
  services: ServiceStatus[]
  lastUpdate: Date | null
}

const SERVICE_HEALTH_CONFIG = {
  CHECK_INTERVAL: 30000,     // Check every 30 seconds
  RETRY_INTERVAL: 5000,      // Retry failed checks after 5 seconds
  TIMEOUT: 5000,             // 5 second timeout for health checks
  CRITICAL_SERVICES: ['DhanHQ_Service', 'AIScalpingService', 'GeminiTradeService'],
}

export const useServiceHealth = () => {
  const [health, setHealth] = useState<ServicesHealth>({
    backend: 'checking',
    services: [],
    lastUpdate: null,
  })
  const [isMonitoring, setIsMonitoring] = useState(true)
  const checkIntervalRef = useRef<number | null>(null)
  const retryTimeoutRef = useRef<number | null>(null)
  const previousHealthRef = useRef<ServicesHealth | null>(null)

  // Check backend health
  const checkBackendHealth = useCallback(async (): Promise<'healthy' | 'unhealthy'> => {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), SERVICE_HEALTH_CONFIG.TIMEOUT)

      const response = await fetch(`${BACKEND_URL}/health`, {
        signal: controller.signal,
      })
      
      clearTimeout(timeoutId)

      if (response.ok) {
        const data = await response.json()
        return data.status === 'healthy' ? 'healthy' : 'unhealthy'
      }
      return 'unhealthy'
    } catch (error) {
      console.error('❌ Backend health check failed:', error)
      return 'unhealthy'
    }
  }, [])

  // Check all services status
  const checkServicesStatus = useCallback(async (): Promise<ServiceStatus[]> => {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), SERVICE_HEALTH_CONFIG.TIMEOUT)

      const response = await fetch(`${BACKEND_URL}/api/services/status`, {
        signal: controller.signal,
      })
      
      clearTimeout(timeoutId)

      if (response.ok) {
        const data = await response.json()
        if (data.status === 'success' && Array.isArray(data.services)) {
          return data.services
        }
      }
      return []
    } catch (error) {
      console.error('❌ Services status check failed:', error)
      return []
    }
  }, [])

  // Detect and notify service status changes
  const notifyStatusChanges = useCallback((newHealth: ServicesHealth) => {
    const prevHealth = previousHealthRef.current

    if (!prevHealth) {
      previousHealthRef.current = newHealth
      return
    }

    // Check backend status change
    if (prevHealth.backend !== newHealth.backend) {
      if (newHealth.backend === 'healthy') {
        toast.success('✅ Backend service restored', { 
          duration: 3000,
          icon: '🔌',
        })
      } else if (newHealth.backend === 'unhealthy') {
        toast.error('❌ Backend service down!', {
          duration: 5000,
          icon: '🔴',
        })
      }
    }

    // Check individual service status changes
    newHealth.services.forEach((service) => {
      const prevService = prevHealth.services.find(s => s.name === service.name)
      
      if (prevService && prevService.status !== service.status) {
        const isCritical = SERVICE_HEALTH_CONFIG.CRITICAL_SERVICES.includes(service.name)
        
        if (service.status === 'running') {
          toast.success(`✅ ${service.name} restored`, {
            duration: 3000,
            icon: isCritical ? '🚨' : '✅',
          })
        } else if (service.status === 'stopped') {
          toast.error(`❌ ${service.name} stopped!`, {
            duration: isCritical ? 10000 : 5000,
            icon: isCritical ? '🚨' : '⚠️',
          })
        }
      }
    })

    previousHealthRef.current = newHealth
  }, [])

  // Perform health check
  const performHealthCheck = useCallback(async () => {
    console.log('🏥 Performing health check...')
    
    const [backendHealth, servicesStatus] = await Promise.all([
      checkBackendHealth(),
      checkServicesStatus(),
    ])

    const newHealth: ServicesHealth = {
      backend: backendHealth,
      services: servicesStatus,
      lastUpdate: new Date(),
    }

    setHealth(newHealth)
    notifyStatusChanges(newHealth)

    // If backend is unhealthy, retry sooner
    if (backendHealth === 'unhealthy') {
      console.warn('⚠️ Backend unhealthy, scheduling retry...')
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current)
      }
      retryTimeoutRef.current = window.setTimeout(performHealthCheck, SERVICE_HEALTH_CONFIG.RETRY_INTERVAL)
    }
  }, [checkBackendHealth, checkServicesStatus, notifyStatusChanges])

  // Start monitoring
  const startMonitoring = useCallback(() => {
    if (checkIntervalRef.current) {
      clearInterval(checkIntervalRef.current)
    }
    
    setIsMonitoring(true)
    performHealthCheck() // Initial check
    
    checkIntervalRef.current = window.setInterval(
      performHealthCheck,
      SERVICE_HEALTH_CONFIG.CHECK_INTERVAL
    )
    
    console.log('✅ Service health monitoring started')
  }, [performHealthCheck])

  // Stop monitoring
  const stopMonitoring = useCallback(() => {
    if (checkIntervalRef.current) {
      clearInterval(checkIntervalRef.current)
      checkIntervalRef.current = null
    }
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
    setIsMonitoring(false)
    console.log('🛑 Service health monitoring stopped')
  }, [])

  // Manual health check
  const refreshHealth = useCallback(() => {
    console.log('🔄 Manual health check triggered')
    performHealthCheck()
  }, [performHealthCheck])

  // Get service by name
  const getService = useCallback((serviceName: string) => {
    return health.services.find(s => s.name === serviceName)
  }, [health.services])

  // Check if all critical services are running
  const areAllCriticalServicesRunning = useCallback(() => {
    return SERVICE_HEALTH_CONFIG.CRITICAL_SERVICES.every(name => {
      const service = health.services.find(s => s.name === name)
      return service && service.status === 'running'
    })
  }, [health.services])

  // Auto-start monitoring on mount
  useEffect(() => {
    startMonitoring()
    
    return () => {
      stopMonitoring()
    }
  }, [startMonitoring, stopMonitoring])

  return {
    health,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    refreshHealth,
    getService,
    areAllCriticalServicesRunning,
    isHealthy: health.backend === 'healthy' && areAllCriticalServicesRunning(),
  }
}

export default useServiceHealth
