import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, TrendingUp, Shield, Zap, Users } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { LoginRequest } from '../../types'
import { TEST_CREDENTIALS } from '../../services/mockAuthService'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})

type LoginForm = z.infer<typeof loginSchema>

const LoginPage = () => {
  const [showPassword, setShowPassword] = useState(false)
  const [showTestCredentials, setShowTestCredentials] = useState(false)
  const navigate = useNavigate()
  const { login, isLoading } = useAuthStore()

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginForm) => {
    const success = await login(data as LoginRequest)
    if (success) {
      navigate('/dashboard')
    }
  }

  const handleTestCredentialSelect = (credentialKey: string) => {
    const cred = TEST_CREDENTIALS[credentialKey as keyof typeof TEST_CREDENTIALS]
    setValue('email', cred.email)
    setValue('password', cred.password)
    setShowTestCredentials(false)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
      <div className="max-w-4xl w-full grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
        {/* Left side - Features */}
        <div className="text-white space-y-8">
          <div>
            <h1 className="text-4xl font-bold mb-4">
              Welcome to <span className="text-blue-400">DTrade</span>
            </h1>
            <p className="text-xl text-gray-300">
              AI-powered institutional-grade trading platform
            </p>
          </div>

          <div className="space-y-6">
            <div className="flex items-start space-x-4">
              <div className="bg-blue-600 rounded-lg p-3">
                <TrendingUp className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Advanced Analytics</h3>
                <p className="text-gray-400">
                  Real-time market data, technical indicators, and AI-driven insights
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-4">
              <div className="bg-green-600 rounded-lg p-3">
                <Shield className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Risk Management</h3>
                <p className="text-gray-400">
                  Sophisticated risk controls and position management tools
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-4">
              <div className="bg-purple-600 rounded-lg p-3">
                <Zap className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">AI Trading</h3>
                <p className="text-gray-400">
                  Automated trading with machine learning algorithms
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right side - Login form */}
        <div className="bg-gray-800 p-8 rounded-2xl shadow-2xl border border-gray-700">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">Sign In</h2>
            <p className="text-gray-400">Access your trading dashboard</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Email field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                Email Address
              </label>
              <input
                {...register('email')}
                type="email"
                id="email"
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your email"
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-400">{errors.email.message}</p>
              )}
            </div>

            {/* Password field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  className="w-full px-4 py-3 pr-12 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-sm text-red-400">{errors.password.message}</p>
              )}
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center"
            >
              {isLoading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              ) : (
                'Sign In'
              )}
            </button>

            {/* Test Credentials */}
            <div className="mt-4">
              <button
                type="button"
                onClick={() => setShowTestCredentials(!showTestCredentials)}
                className="w-full text-sm text-gray-400 hover:text-gray-300 flex items-center justify-center space-x-2"
              >
                <Users className="h-4 w-4" />
                <span>Use Test Credentials</span>
              </button>

              {showTestCredentials && (
                <div className="mt-3 p-3 bg-gray-700 rounded-lg border border-gray-600">
                  <p className="text-xs text-gray-400 mb-2">Click to auto-fill credentials:</p>
                  <div className="grid grid-cols-1 gap-2">
                    {Object.entries(TEST_CREDENTIALS).map(([key, cred]) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => handleTestCredentialSelect(key)}
                        className="text-left p-2 bg-gray-600 hover:bg-gray-500 rounded text-sm transition-colors"
                      >
                        <div className="font-medium text-white">{cred.user.full_name}</div>
                        <div className="text-xs text-gray-400">{cred.email}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </form>

          <div className="mt-6 text-center">
            <p className="text-gray-400">
              Don't have an account?{' '}
              <Link to="/register" className="text-blue-400 hover:text-blue-300 font-medium">
                Sign up
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
