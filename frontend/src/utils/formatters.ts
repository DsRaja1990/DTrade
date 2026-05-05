// Currency formatting
export const formatCurrency = (amount: number, currency = 'INR'): string => {
  if (isNaN(amount)) return '₹0.00'
  
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

// Number formatting with Indian numbering system
export const formatNumber = (num: number, decimals = 2): string => {
  if (isNaN(num)) return '0'
  
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num)
}

// Percentage formatting
export const formatPercentage = (value: number, decimals = 2): string => {
  if (isNaN(value)) return '0.00%'
  
  return `${value >= 0 ? '+' : ''}${formatNumber(value, decimals)}%`
}

// Compact number formatting (e.g., 1.2K, 1.5M)
export const formatCompactNumber = (num: number): string => {
  if (isNaN(num)) return '0'
  
  const formatter = new Intl.NumberFormat('en-IN', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  })
  
  return formatter.format(num)
}

// Volume formatting
export const formatVolume = (volume: number): string => {
  if (volume >= 10000000) return `${(volume / 10000000).toFixed(1)}Cr`
  if (volume >= 100000) return `${(volume / 100000).toFixed(1)}L`
  if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`
  return volume.toString()
}

// Time formatting
export const formatTime = (timestamp: string | Date): string => {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  return new Intl.DateTimeFormat('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  }).format(date)
}

// Date formatting
export const formatDate = (timestamp: string | Date): string => {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  return new Intl.DateTimeFormat('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

// Date and time formatting
export const formatDateTime = (timestamp: string | Date): string => {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  return new Intl.DateTimeFormat('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }).format(date)
}

// Relative time formatting
export const formatRelativeTime = (timestamp: string | Date): string => {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  
  if (diffInSeconds < 60) return 'Just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`
  
  return formatDate(date)
}

// P&L color helper
export const getPnLColor = (value: number): string => {
  if (value > 0) return 'text-green-400'
  if (value < 0) return 'text-red-400'
  return 'text-gray-400'
}

// Price formatting with tick size
export const formatPrice = (price: number, tickSize = 0.05): string => {
  if (isNaN(price)) return '0.00'
  
  const decimals = tickSize >= 1 ? 0 : tickSize.toString().split('.')[1]?.length || 2
  return formatNumber(price, decimals)
}

// Order status formatting
export const formatOrderStatus = (status: string): string => {
  return status.toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// File size formatting
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Duration formatting
export const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60
  
  return `${hours}h ${minutes}m ${remainingSeconds}s`
}
