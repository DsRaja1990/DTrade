import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  BarChart3,
  TrendingUp,
  Briefcase,
  Bot,
  Settings,
  Target,
  Activity,
  ChevronLeft,
  ChevronRight,
  Signal,
} from 'lucide-react'
import { cn } from '../utils/cn'

const Sidebar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const location = useLocation()

  const navigationItems = [
    {
      title: 'Dashboard',
      href: '/dashboard',
      icon: BarChart3,
      description: 'Overview',
    },
    {
      title: 'Trading',
      href: '/trading',
      icon: TrendingUp,
      description: 'Place orders',
    },
    {
      title: 'Positions',
      href: '/positions',
      icon: Target,
      description: 'Open positions',
    },
    {
      title: 'Portfolio',
      href: '/portfolio',
      icon: Briefcase,
      description: 'Holdings & P&L',
    },
    {
      title: 'Signals',
      href: '/signals',
      icon: Signal,
      description: 'Signal analytics',
    },
    {
      title: 'Strategies',
      href: '/strategies',
      icon: Bot,
      description: 'AI strategies',
    },
    {
      title: 'Settings',
      href: '/settings',
      icon: Settings,
      description: 'Settings',
    },
  ]

  const isActive = (href: string) => location.pathname === href

  return (
    <div
      className={cn(
        'bg-gray-800 border-r border-gray-700 transition-all duration-300 flex flex-col',
        isCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex items-center space-x-2">
              <div className="h-8 w-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Activity className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-xl font-bold text-white">DTrade</h1>
            </div>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 rounded-md hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navigationItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.href)

          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                'flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors group relative',
                active
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              )}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && (
                <>
                  <div className="flex-1">
                    <p className="font-medium">{item.title}</p>
                    <p className="text-xs opacity-75">{item.description}</p>
                  </div>
                </>
              )}

              {/* Tooltip for collapsed state */}
              {isCollapsed && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-sm rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                  {item.title}
                </div>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        {!isCollapsed && (
          <div className="text-xs text-gray-500 text-center">
            <p>DTrade v1.0.0</p>
            <p className="mt-1">AI-Powered Trading</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Sidebar
