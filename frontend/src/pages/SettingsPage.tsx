import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Key, Shield, User, Bell, Clock, CheckCircle, AlertTriangle, Activity, RefreshCw } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { getTokenExpirationDate, isTokenExpired } from '../utils/dhanConfig'
import toast from 'react-hot-toast'

// Service endpoints
const SERVICE_URLS = {
  scalping: 'http://localhost:4002',
  hedger: 'http://localhost:4003',
  equity: 'http://localhost:5080',
  signal: 'http://localhost:4090',
  gemini: 'http://localhost:4080',
  backend: 'http://localhost:8000'
}

interface ServiceStatus {
  name: string
  port: number
  status: 'connected' | 'disconnected' | 'checking'
  url: string
}

const dhanCredentialsSchema = z.object({
  client_id: z.string().min(1, 'Client ID is required'),
  access_token: z.string().min(1, 'Access Token is required'),
})

type DhanCredentialsForm = z.infer<typeof dhanCredentialsSchema>

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('dhan')
  const [isUpdatingToken, setIsUpdatingToken] = useState(false)
  const [serviceStatuses, setServiceStatuses] = useState<ServiceStatus[]>([
    { name: 'AI Scalping', port: 4002, status: 'checking', url: SERVICE_URLS.scalping },
    { name: 'AI Options Hedger', port: 4003, status: 'checking', url: SERVICE_URLS.hedger },
    { name: 'Elite Equity HV', port: 5080, status: 'checking', url: SERVICE_URLS.equity },
    { name: 'AI Signal Engine', port: 4090, status: 'checking', url: SERVICE_URLS.signal },
    { name: 'Gemini Trade', port: 4080, status: 'checking', url: SERVICE_URLS.gemini },
    { name: 'DhanHQ Backend', port: 8000, status: 'checking', url: SERVICE_URLS.backend }
  ])
  const { dhanCredentials, setDhanCredentials } = useAuthStore()

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<DhanCredentialsForm>({
    resolver: zodResolver(dhanCredentialsSchema),
    defaultValues: {
      client_id: dhanCredentials?.client_id || '',
      access_token: dhanCredentials?.access_token || '',
    },
  })

  // Check service connectivity
  const checkServiceHealth = async (service: ServiceStatus): Promise<'connected' | 'disconnected'> => {
    try {
      const response = await fetch(`${service.url}/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(3000)
      })
      return response.ok ? 'connected' : 'disconnected'
    } catch {
      return 'disconnected'
    }
  }

  // Check all services
  const checkAllServices = async () => {
    const updatedStatuses = await Promise.all(
      serviceStatuses.map(async (service) => ({
        ...service,
        status: await checkServiceHealth(service)
      }))
    )
    setServiceStatuses(updatedStatuses)
  }

  // Check services on mount and periodically
  useEffect(() => {
    checkAllServices()
    const interval = setInterval(checkAllServices, 30000) // Check every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const onSubmitDhanCredentials = async (data: DhanCredentialsForm) => {
    setDhanCredentials(data)
    setIsUpdatingToken(true)
    
    try {
      // Update token in all services via API
      const updatePromises = [
        fetch(`${SERVICE_URLS.scalping}/update-token`, { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ access_token: data.access_token })
        }),
        fetch(`${SERVICE_URLS.hedger}/update-token`, { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ access_token: data.access_token })
        }),
        fetch(`${SERVICE_URLS.equity}/api/update-token`, { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ access_token: data.access_token })
        })
      ]
      
      await Promise.allSettled(updatePromises)
      toast.success('Token updated! Please restart Windows services to apply changes.')
      
      // Recheck service health
      setTimeout(checkAllServices, 2000)
    } catch (error) {
      toast.error('Failed to update some services. Please restart them manually.')
      console.error('Token update error:', error)
    } finally {
      setIsUpdatingToken(false)
    }
  }

  const tabs = [
    { id: 'dhan', label: 'DhanHQ Setup', icon: Key },
    { id: 'services', label: 'Services Status', icon: Activity },
    { id: 'account', label: 'Account', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ]

  // Token validation info
  const tokenExpiryDate = dhanCredentials?.access_token ? getTokenExpirationDate(dhanCredentials.access_token) : null
  const tokenExpired = dhanCredentials?.access_token ? isTokenExpired(dhanCredentials.access_token) : false
  
  // Test Dhan API connection
  const testDhanConnection = async () => {
    try {
      const response = await fetch(`${SERVICE_URLS.backend}/api/funds`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (response.ok) {
        const data = await response.json()
        toast.success(`Dhan API Connected! Balance: ₹${data.data?.availabelBalance || 0}`)
      } else {
        const error = await response.json()
        toast.error(`Dhan API Error: ${error.detail || 'Authentication failed'}`)
      }
    } catch (error) {
      toast.error('Failed to connect to backend service')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Settings</h1>
      
      {/* Tab Navigation */}
      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="flex space-x-1 p-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'dhan' && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-lg font-semibold text-white mb-4">DhanHQ API Configuration</h2>
          <p className="text-gray-400 mb-6">
            Configure your DhanHQ API credentials to enable live trading and market data.
          </p>

          <form onSubmit={handleSubmit(onSubmitDhanCredentials)} className="space-y-4">
            <div>
              <label htmlFor="client_id" className="block text-sm font-medium text-gray-300 mb-2">
                Client ID
              </label>
              <input
                {...register('client_id')}
                type="text"
                id="client_id"
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your DhanHQ Client ID"
              />
              {errors.client_id && (
                <p className="mt-1 text-sm text-red-400">{errors.client_id.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="access_token" className="block text-sm font-medium text-gray-300 mb-2">
                Access Token
              </label>
              <textarea
                {...register('access_token')}
                id="access_token"
                rows={4}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your DhanHQ Access Token"
              />
              {errors.access_token && (
                <p className="mt-1 text-sm text-red-400">{errors.access_token.message}</p>
              )}
            </div>

            <div className="space-y-4">
              <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4">
                <h3 className="text-sm font-medium text-blue-300 mb-2">How to get DhanHQ credentials:</h3>
                <ol className="text-sm text-blue-200 space-y-1 list-decimal list-inside">
                  <li>Log in to your DhanHQ account</li>
                  <li>Go to API Management section</li>
                  <li>Create a new API key and get your Client ID</li>
                  <li>Generate an Access Token for API access</li>
                  <li>Copy and paste the credentials here</li>
                </ol>
              </div>

              <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-4">
                <h3 className="text-sm font-medium text-yellow-300 mb-2">⚠️ Important: After Updating Token</h3>
                <p className="text-sm text-yellow-200 mb-2">
                  Windows services must be restarted to use the new token:
                </p>
                <ol className="text-sm text-yellow-200 space-y-1 list-decimal list-inside mb-3">
                  <li>Run <code className="bg-yellow-800/30 px-1 py-0.5 rounded">Restart-All-Services.ps1</code> as Administrator</li>
                  <li>Or use <code className="bg-yellow-800/30 px-1 py-0.5 rounded">Update-DhanToken.bat</code> to update and restart automatically</li>
                </ol>
                <p className="text-xs text-yellow-200/80">
                  Check the "Services Status" tab to verify all services are connected.
                </p>
              </div>
            </div>

            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={isUpdatingToken}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors duration-200 flex items-center space-x-2"
              >
                {isUpdatingToken && <RefreshCw className="h-4 w-4 animate-spin" />}
                <span>{isUpdatingToken ? 'Updating...' : 'Save & Update All Services'}</span>
              </button>
              <button
                type="button"
                onClick={testDhanConnection}
                className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors duration-200"
              >
                Test Connection
              </button>
              <button
                type="button"
                onClick={() => reset()}
                disabled={isUpdatingToken}
                className="px-6 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors duration-200"
              >
                Reset
              </button>
            </div>
          </form>

          {/* Current Status */}
          <div className="mt-6 pt-6 border-t border-gray-700">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Current Status:</h3>
            
            <div className="space-y-3">
              {/* Connection Status */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${dhanCredentials?.access_token ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="text-sm text-gray-400">
                    DhanHQ Connection
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  {dhanCredentials?.access_token ? (
                    <CheckCircle className="h-4 w-4 text-green-400" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-red-400" />
                  )}
                  <span className={`text-sm ${dhanCredentials?.access_token ? 'text-green-400' : 'text-red-400'}`}>
                    {dhanCredentials?.access_token ? 'Connected' : 'Not Connected'}
                  </span>
                </div>
              </div>

              {/* Client ID */}
              {dhanCredentials?.client_id && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Client ID</span>
                  <span className="text-sm text-gray-300">{dhanCredentials.client_id}</span>
                </div>
              )}

              {/* Token Expiry */}
              {tokenExpiryDate && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-400">Token Expires</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {tokenExpired ? (
                      <AlertTriangle className="h-4 w-4 text-red-400" />
                    ) : (
                      <CheckCircle className="h-4 w-4 text-green-400" />
                    )}
                    <span className={`text-sm ${tokenExpired ? 'text-red-400' : 'text-green-400'}`}>
                      {tokenExpired ? 'Expired' : tokenExpiryDate.toLocaleDateString()}
                    </span>
                  </div>
                </div>
              )}

              {/* Token Status Warning */}
              {tokenExpired && (
                <div className="bg-red-900/20 border border-red-700 rounded-lg p-3">
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="h-4 w-4 text-red-400" />
                    <span className="text-sm text-red-300 font-medium">Token Expired</span>
                  </div>
                  <p className="text-xs text-red-200 mt-1">
                    Your DhanHQ access token has expired. Please generate a new token and update your credentials.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'services' && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Services Connection Status</h2>
            <button
              onClick={checkAllServices}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Refresh</span>
            </button>
          </div>
          <p className="text-gray-400 mb-6">
            Monitor the connection status of all trading services in real-time.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {serviceStatuses.map((service) => (
              <div
                key={service.name}
                className="bg-gray-900/50 border border-gray-700 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-white">{service.name}</h3>
                  <div className="flex items-center space-x-2">
                    {service.status === 'checking' ? (
                      <RefreshCw className="h-4 w-4 text-gray-400 animate-spin" />
                    ) : service.status === 'connected' ? (
                      <CheckCircle className="h-4 w-4 text-green-400" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-red-400" />
                    )}
                    <span
                      className={`text-sm font-medium ${
                        service.status === 'checking'
                          ? 'text-gray-400'
                          : service.status === 'connected'
                          ? 'text-green-400'
                          : 'text-red-400'
                      }`}
                    >
                      {service.status === 'checking'
                        ? 'Checking...'
                        : service.status === 'connected'
                        ? 'Connected'
                        : 'Disconnected'}
                    </span>
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Port</span>
                    <span className="text-gray-300 font-mono">{service.port}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">URL</span>
                    <span className="text-gray-300 font-mono text-xs">{service.url}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Status Indicator</span>
                    <div
                      className={`w-3 h-3 rounded-full ${
                        service.status === 'checking'
                          ? 'bg-gray-500 animate-pulse'
                          : service.status === 'connected'
                          ? 'bg-green-500'
                          : 'bg-red-500'
                      }`}
                    />
                  </div>
                </div>

                {service.status === 'disconnected' && (
                  <div className="mt-3 bg-red-900/20 border border-red-700 rounded-lg p-2">
                    <p className="text-xs text-red-300">
                      Service is not responding. Check if it's running or restart it.
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="mt-6 pt-6 border-t border-gray-700">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Summary</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-green-900/20 border border-green-700 rounded-lg p-3">
                <div className="flex items-center space-x-2 mb-1">
                  <CheckCircle className="h-4 w-4 text-green-400" />
                  <span className="text-xs text-green-300 font-medium">Connected</span>
                </div>
                <p className="text-2xl font-bold text-green-400">
                  {serviceStatuses.filter((s) => s.status === 'connected').length}
                </p>
              </div>
              <div className="bg-red-900/20 border border-red-700 rounded-lg p-3">
                <div className="flex items-center space-x-2 mb-1">
                  <AlertTriangle className="h-4 w-4 text-red-400" />
                  <span className="text-xs text-red-300 font-medium">Disconnected</span>
                </div>
                <p className="text-2xl font-bold text-red-400">
                  {serviceStatuses.filter((s) => s.status === 'disconnected').length}
                </p>
              </div>
              <div className="bg-gray-700/20 border border-gray-600 rounded-lg p-3">
                <div className="flex items-center space-x-2 mb-1">
                  <Activity className="h-4 w-4 text-gray-400" />
                  <span className="text-xs text-gray-300 font-medium">Total Services</span>
                </div>
                <p className="text-2xl font-bold text-gray-300">{serviceStatuses.length}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'account' && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-lg font-semibold text-white mb-4">Account Settings</h2>
          <p className="text-gray-400">Account management features will be available here...</p>
        </div>
      )}

      {activeTab === 'security' && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-lg font-semibold text-white mb-4">Security Settings</h2>
          <p className="text-gray-400">Security and privacy settings will be available here...</p>
        </div>
      )}

      {activeTab === 'notifications' && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-lg font-semibold text-white mb-4">Notification Preferences</h2>
          <p className="text-gray-400">Notification settings will be available here...</p>
        </div>
      )}
    </div>
  )
}

export default SettingsPage
