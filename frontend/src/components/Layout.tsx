import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import { useWebSocket } from '../hooks/useWebSocket'

const Layout = () => {
  
  // Initialize WebSocket connection for real-time updates
  useWebSocket()

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header />
        
        {/* Page content */}
        <main className="flex-1 overflow-auto bg-gray-950 p-6">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout
