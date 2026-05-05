import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import TradingPage from './pages/TradingPage'
import PortfolioPage from './pages/PortfolioPage'
import PositionsPage from './pages/PositionsPage'
import StrategiesPage from './pages/StrategiesPage'
import SettingsPage from './pages/SettingsPage'
import SignalAnalyticsPage from './pages/SignalAnalyticsPage'
import ConnectionStatus from './components/ConnectionStatus'
import { useEffect } from 'react'

function App() {
  const { user, initialize } = useAuthStore()

  useEffect(() => {
    initialize()
  }, [initialize])

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Connection Status Indicator - Always visible for trading app */}
      {user && <ConnectionStatus position="top-right" showDetails={true} />}
      
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
        <Route path="/register" element={user ? <Navigate to="/dashboard" replace /> : <RegisterPage />} />
        
        {/* Protected routes */}
        <Route path="/" element={user ? <Layout /> : <Navigate to="/login" replace />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="trading" element={<TradingPage />} />
          <Route path="positions" element={<PositionsPage />} />
          <Route path="portfolio" element={<PortfolioPage />} />
          <Route path="signals" element={<SignalAnalyticsPage />} />
          <Route path="strategies" element={<StrategiesPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to={user ? "/dashboard" : "/login"} replace />} />
      </Routes>
    </div>
  )
}

export default App
