import { useState, useEffect, useCallback } from 'react';
import { 
  RefreshCw, AlertTriangle, Zap, Settings, 
  Globe, TestTube, Shield, Rocket
} from 'lucide-react';

// ============ SERVICE ENDPOINTS ============
const SERVICE_URLS = {
  scalping: 'http://localhost:4002',
  hedger: 'http://localhost:4003',
  equity: 'http://localhost:5080'
};

// ============ INTERFACES ============
interface ScalpingStatus {
  running: boolean;
  strategy_enabled: boolean;
  mode: string;
  daily_trades: number;
  positions: {
    unrealized_pnl: number;
    realized_pnl: number;
    total_pnl: number;
    position_count: number;
    capital: number;
  };
  timestamp: string;
}

interface HedgerStatus {
  running: boolean;
  strategy_enabled: boolean;
  mode: string;
  positions: any;
  signals: any;
  is_trading_time: boolean;
  timestamp: string;
}

interface EquityStatus {
  success: boolean;
  strategy_enabled: boolean;
  running: boolean;
  mode: string;
  is_trading_time: boolean;
  timestamp: string;
  database_connected: boolean;
  gemini_connected: boolean;
  engine?: {
    is_running: boolean;
    is_paused: boolean;
  };
}

interface ServiceConfig {
  capital: number;
  max_daily_loss: number;
  paper_trading: boolean;
  dhan_access_token?: string;
}

type TradingMode = 'paper' | 'live';
type StrategyTab = 'ai-scalping' | 'ai-hedger' | 'elite-equity';

const StrategiesPage = () => {
  // Tab and mode state
  const [activeTab, setActiveTab] = useState<StrategyTab>('ai-scalping');
  const [tradingMode, setTradingMode] = useState<TradingMode>('paper');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ===== AI SCALPING STATE =====
  const [scalpingStatus, setScalpingStatus] = useState<ScalpingStatus | null>(null);
  const [scalpingOnline, setScalpingOnline] = useState(false);
  const [scalpingConfig, setScalpingConfig] = useState<ServiceConfig>({
    capital: 100000,
    max_daily_loss: 0.05,
    paper_trading: true,
    dhan_access_token: ''
  });

  // ===== AI HEDGER STATE =====
  const [hedgerStatus, setHedgerStatus] = useState<HedgerStatus | null>(null);
  const [hedgerOnline, setHedgerOnline] = useState(false);
  const [hedgerConfig, setHedgerConfig] = useState<ServiceConfig>({
    capital: 500000,
    max_daily_loss: 0.03,
    paper_trading: true,
    dhan_access_token: ''
  });

  // ===== ELITE EQUITY STATE =====
  const [equityStatus, setEquityStatus] = useState<EquityStatus | null>(null);
  const [equityOnline, setEquityOnline] = useState(false);
  const [equityConfig, setEquityConfig] = useState<ServiceConfig>({
    capital: 500000,
    max_daily_loss: 0.05,
    paper_trading: true,
    dhan_access_token: ''
  });

  // ===== SCALPING FUNCTIONS =====
  const fetchScalpingHealth = useCallback(async () => {
    try {
      const response = await fetch(`${SERVICE_URLS.scalping}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const data = await response.json();
        setScalpingOnline(data.status === 'healthy');
      } else {
        setScalpingOnline(false);
      }
    } catch {
      setScalpingOnline(false);
    }
  }, []);

  const fetchScalpingStatus = useCallback(async () => {
    try {
      const response = await fetch(`${SERVICE_URLS.scalping}/status`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const data = await response.json();
        setScalpingStatus(data);
      }
    } catch {
      console.error('Scalping status fetch failed');
    }
  }, []);

  const saveScalpingConfig = async () => {
    if (!scalpingOnline) {
      setError('AI Scalping service is offline.');
      return;
    }
    setActionLoading('scalping-config');
    try {
      const response = await fetch(`${SERVICE_URLS.scalping}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          capital: scalpingConfig.capital,
          max_daily_loss: scalpingConfig.max_daily_loss
        })
      });
      if (!response.ok) throw new Error('Failed to save configuration');
      setError(null);
      alert('Configuration saved successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setActionLoading(null);
    }
  };

  const toggleScalpingStrategy = async () => {
    if (!scalpingOnline) {
      setError('AI Scalping service is offline. Please start the Windows service.');
      return;
    }
    setActionLoading('scalping');
    try {
      // Check strategy_enabled state (persistent), not running state
      const endpoint = scalpingStatus?.strategy_enabled ? '/stop' : '/start';
      const response = await fetch(`${SERVICE_URLS.scalping}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: tradingMode,
          capital: scalpingConfig.capital,
          max_daily_loss: scalpingConfig.max_daily_loss,
          dhan_access_token: scalpingConfig.dhan_access_token
        })
      });
      if (!response.ok) throw new Error('Operation failed');
      await fetchScalpingStatus();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle strategy');
    } finally {
      setActionLoading(null);
    }
  };

  // ===== HEDGER FUNCTIONS =====
  const fetchHedgerHealth = useCallback(async () => {
    try {
      const response = await fetch(`${SERVICE_URLS.hedger}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const data = await response.json();
        setHedgerOnline(data.status === 'healthy');
      } else {
        setHedgerOnline(false);
      }
    } catch {
      setHedgerOnline(false);
    }
  }, []);

  const fetchHedgerStatus = useCallback(async () => {
    try {
      const response = await fetch(`${SERVICE_URLS.hedger}/status`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const data = await response.json();
        setHedgerStatus(data);
      }
    } catch {
      console.error('Hedger status fetch failed');
    }
  }, []);

  const saveHedgerConfig = async () => {
    if (!hedgerOnline) {
      setError('AI Options Hedger service is offline.');
      return;
    }
    setActionLoading('hedger-config');
    try {
      const response = await fetch(`${SERVICE_URLS.hedger}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          capital: hedgerConfig.capital,
          max_daily_loss: hedgerConfig.max_daily_loss
        })
      });
      if (!response.ok) throw new Error('Failed to save configuration');
      setError(null);
      alert('Configuration saved successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setActionLoading(null);
    }
  };

  const toggleHedgerStrategy = async () => {
    if (!hedgerOnline) {
      setError('AI Options Hedger service is offline. Please start the Windows service.');
      return;
    }
    setActionLoading('hedger');
    try {
      // Check strategy_enabled state (persistent), not running state
      const endpoint = hedgerStatus?.strategy_enabled ? '/stop' : '/start';
      const response = await fetch(`${SERVICE_URLS.hedger}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: tradingMode,
          capital: hedgerConfig.capital,
          max_daily_loss: hedgerConfig.max_daily_loss,
          dhan_access_token: hedgerConfig.dhan_access_token
        })
      });
      if (!response.ok) throw new Error('Operation failed');
      await fetchHedgerStatus();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle strategy');
    } finally {
      setActionLoading(null);
    }
  };

  // ===== ELITE EQUITY FUNCTIONS =====
  const fetchEquityHealth = useCallback(async () => {
    try {
      const response = await fetch(`${SERVICE_URLS.equity}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const data = await response.json();
        setEquityStatus(data);
        setEquityOnline(data.status === 'healthy');
      } else {
        setEquityOnline(false);
      }
    } catch {
      setEquityOnline(false);
    }
  }, []);

  const fetchEquityStatus = useCallback(async () => {
    try {
      const response = await fetch(`${SERVICE_URLS.equity}/api/status`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const data = await response.json();
        setEquityStatus(data);
      }
    } catch {
      console.error('Equity status fetch failed');
    }
  }, []);

  const saveEquityConfig = async () => {
    if (!equityOnline) {
      setError('Elite Equity service is offline.');
      return;
    }
    setActionLoading('equity-config');
    try {
      const response = await fetch(`${SERVICE_URLS.equity}/api/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          capital: equityConfig.capital,
          max_daily_loss: equityConfig.max_daily_loss
        })
      });
      if (!response.ok) throw new Error('Failed to save configuration');
      setError(null);
      alert('Configuration saved successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setActionLoading(null);
    }
  };

  const toggleEquityStrategy = async () => {
    if (!equityOnline) {
      setError('Elite Equity service is offline. Please start the Windows service.');
      return;
    }
    setActionLoading('equity');
    try {
      // Check strategy_enabled state (persistent), not running state
      const endpoint = equityStatus?.strategy_enabled ? '/api/stop' : '/api/start';
      const response = await fetch(`${SERVICE_URLS.equity}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: tradingMode,
          capital: equityConfig.capital,
          max_daily_loss: equityConfig.max_daily_loss,
          dhan_access_token: equityConfig.dhan_access_token
        })
      });
      if (!response.ok) throw new Error('Operation failed');
      await fetchEquityStatus();  // Refresh status to get strategy_enabled
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle strategy');
    } finally {
      setActionLoading(null);
    }
  };

  // ===== EFFECTS =====
  useEffect(() => {
    fetchScalpingHealth();
    fetchHedgerHealth();
    fetchEquityHealth();
    fetchScalpingStatus();
    fetchHedgerStatus();
    fetchEquityStatus();

    const interval = setInterval(() => {
      fetchScalpingHealth();
      fetchHedgerHealth();
      fetchEquityHealth();
      if (activeTab === 'ai-scalping') fetchScalpingStatus();
      if (activeTab === 'ai-hedger') fetchHedgerStatus();
      if (activeTab === 'elite-equity') fetchEquityStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, [activeTab, fetchScalpingHealth, fetchHedgerHealth, fetchEquityHealth, fetchScalpingStatus, fetchHedgerStatus, fetchEquityStatus]);

  // ===== HELPERS =====
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const refreshAll = async () => {
    setLoading(true);
    await Promise.all([
      fetchScalpingHealth(),
      fetchHedgerHealth(),
      fetchEquityHealth(),
      fetchScalpingStatus(),
      fetchHedgerStatus()
    ]);
    setLoading(false);
  };

  // ===== RENDER =====
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
      {/* Header */}
      <div className="bg-gray-900/95 backdrop-blur-sm border-b border-gray-700/50 px-4 py-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                AI Trading Strategies
              </h1>
              <p className="text-gray-400 text-xs">Connected to Windows Services</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {/* Trading Mode Toggle */}
            <div className="flex items-center space-x-2 bg-gray-800/50 rounded-lg px-3 py-1.5 border border-gray-700/30">
              <span className="text-xs text-gray-400 font-medium">Mode:</span>
              <button
                onClick={() => setTradingMode(tradingMode === 'paper' ? 'live' : 'paper')}
                className={`relative w-12 h-6 rounded-full transition-all duration-300 ${
                  tradingMode === 'live' 
                    ? 'bg-gradient-to-r from-red-500 to-red-600' 
                    : 'bg-gradient-to-r from-blue-500 to-blue-600'
                }`}
              >
                <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-transform duration-300 ${
                  tradingMode === 'live' ? 'translate-x-6' : 'translate-x-0.5'
                }`} />
              </button>
              <div className="flex items-center space-x-1">
                {tradingMode === 'paper' ? (
                  <>
                    <TestTube className="h-3 w-3 text-blue-400" />
                    <span className="text-blue-400 font-medium text-xs">Paper</span>
                  </>
                ) : (
                  <>
                    <Globe className="h-3 w-3 text-red-400" />
                    <span className="text-red-400 font-medium text-xs">Live</span>
                  </>
                )}
              </div>
            </div>
            
            <button
              onClick={refreshAll}
              disabled={loading}
              className="px-3 py-1.5 bg-gray-700/50 border border-gray-600/30 text-white rounded-lg hover:bg-gray-600/50 disabled:opacity-50 flex items-center space-x-1 transition-all"
            >
              <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
              <span className="text-xs">Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-4">
        {/* Strategy Tabs */}
        <div className="mb-4">
          <div className="flex space-x-1 bg-gray-800/50 backdrop-blur-sm rounded-xl p-1 border border-gray-700/30">
            {[
              { id: 'ai-scalping', name: 'AI Scalping', icon: Zap, gradient: 'from-orange-500 to-red-500', online: scalpingOnline, port: 4002 },
              { id: 'ai-hedger', name: 'AI Options Hedger', icon: Shield, gradient: 'from-green-500 to-emerald-500', online: hedgerOnline, port: 4003 },
              { id: 'elite-equity', name: 'Elite Equity', icon: Rocket, gradient: 'from-purple-500 to-pink-500', online: equityOnline, port: 5080 }
            ].map((tab) => {
              const TabIcon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as StrategyTab)}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-300 relative overflow-hidden ${
                    activeTab === tab.id
                      ? `bg-gradient-to-r ${tab.gradient} text-white shadow-lg`
                      : 'text-gray-300 hover:text-white hover:bg-gray-700/50'
                  } flex items-center justify-center space-x-2`}
                >
                  <TabIcon className="h-4 w-4" />
                  <span className="font-medium">{tab.name}</span>
                  <div className={`w-2 h-2 rounded-full ${tab.online ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
                  <span className="text-xs opacity-60">:{tab.port}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 bg-red-900/20 border border-red-500/30 rounded-lg p-3 flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            <span className="text-red-200 text-sm">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300 text-lg">×</button>
          </div>
        )}

        {/* ===== AI SCALPING TAB ===== */}
        {activeTab === 'ai-scalping' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
              <div className="xl:col-span-3 bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 overflow-hidden">
                <div className="p-4 border-b border-gray-700/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg">
                        <Zap className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-white">AI Scalping Service</h3>
                        <p className="text-gray-400 text-sm">High-frequency index scalping with AI</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-4">
                      <span className={`text-sm font-medium ${scalpingStatus?.strategy_enabled ? 'text-green-400' : 'text-gray-400'}`}>
                        {scalpingStatus?.strategy_enabled ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                      
                      {!scalpingOnline && (
                        <div className="flex items-center space-x-1 px-2 py-1 bg-red-900/30 rounded-md border border-red-500/30">
                          <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" />
                          <span className="text-red-400 text-xs font-medium">Service Down</span>
                        </div>
                      )}
                      
                      <button
                        onClick={toggleScalpingStrategy}
                        disabled={actionLoading !== null || !scalpingOnline}
                        className={`relative w-14 h-7 rounded-full transition-all duration-500 ${
                          scalpingStatus?.strategy_enabled
                            ? 'bg-gradient-to-r from-green-400 to-green-600 shadow-lg shadow-green-500/50' 
                            : 'bg-gradient-to-r from-gray-600 to-gray-800'
                        } disabled:opacity-50 border-2 border-white/20`}
                      >
                        <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-all duration-500 ${
                          scalpingStatus?.strategy_enabled ? 'translate-x-7' : 'translate-x-0.5'
                        }`} />
                        {actionLoading === 'scalping' && (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          </div>
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Metrics */}
                <div className="p-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Capital</p>
                    <p className="text-white font-bold text-sm">{formatCurrency(scalpingConfig.capital)}</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Daily P&L</p>
                    <p className={`font-bold text-sm ${(scalpingStatus?.positions?.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(scalpingStatus?.positions?.total_pnl || 0)}
                    </p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Positions</p>
                    <p className="text-white font-bold text-sm">{scalpingStatus?.positions?.position_count || 0}</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Daily Trades</p>
                    <p className="text-white font-bold text-sm">{scalpingStatus?.daily_trades || 0}</p>
                  </div>
                </div>

                <div className="p-4 border-t border-gray-700/30">
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-400">Running:</span>
                      <span className={`ml-2 font-bold ${scalpingStatus?.running ? 'text-green-400' : 'text-gray-400'}`}>
                        {scalpingStatus?.running ? 'Yes' : 'No'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">Service Mode:</span>
                      <span className="ml-2 text-blue-400 font-bold">{scalpingStatus?.mode?.toUpperCase() || 'PAPER'}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Trading Mode:</span>
                      <span className={`ml-2 font-bold ${tradingMode === 'live' ? 'text-red-400' : 'text-blue-400'}`}>
                        {tradingMode.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Config Panel */}
              <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4">
                <h4 className="text-sm font-semibold text-white mb-4 flex items-center space-x-2">
                  <Settings className="h-4 w-4" />
                  <span>Configuration</span>
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Capital (₹)</label>
                    <input
                      type="number"
                      value={scalpingConfig.capital}
                      onChange={(e) => setScalpingConfig(prev => ({ ...prev, capital: Number(e.target.value) }))}
                      className="w-full bg-gray-700/50 border border-gray-600/30 rounded-md px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Max Daily Loss (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={scalpingConfig.max_daily_loss * 100}
                      onChange={(e) => setScalpingConfig(prev => ({ ...prev, max_daily_loss: Number(e.target.value) / 100 }))}
                      className="w-full bg-gray-700/50 border border-gray-600/30 rounded-md px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Dhan Access Token</label>
                    <input
                      type="password"
                      value={scalpingConfig.dhan_access_token || ''}
                      onChange={(e) => setScalpingConfig(prev => ({ ...prev, dhan_access_token: e.target.value }))}
                      className="w-full bg-gray-700/50 border border-gray-600/30 rounded-md px-2 py-1.5 text-white text-sm"
                      placeholder="Enter token"
                    />
                  </div>
                  <button
                    onClick={saveScalpingConfig}
                    disabled={actionLoading !== null || !scalpingOnline}
                    className="w-full mt-3 px-3 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm transition-all"
                  >
                    {actionLoading === 'scalping-config' ? 'Saving...' : 'Save Configuration'}
                  </button>
                  
                  {/* Connection Status */}
                  <div className="pt-3 mt-3 border-t border-gray-700/30">
                    <h5 className="text-xs font-semibold text-gray-400 mb-2">Connections</h5>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Service</span>
                        <div className="flex items-center space-x-1">
                          <div className={`w-1.5 h-1.5 rounded-full ${scalpingOnline ? 'bg-green-400' : 'bg-red-400'}`} />
                          <span className={scalpingOnline ? 'text-green-400' : 'text-red-400'}>
                            {scalpingOnline ? 'Online' : 'Offline'}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Port</span>
                        <span className="text-gray-300">4002</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ===== AI HEDGER TAB ===== */}
        {activeTab === 'ai-hedger' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
              <div className="xl:col-span-3 bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 overflow-hidden">
                <div className="p-4 border-b border-gray-700/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                        <Shield className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-white">AI Options Hedger</h3>
                        <p className="text-gray-400 text-sm">Intelligent options hedging with AI risk management</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-4">
                      <span className={`text-sm font-medium ${hedgerStatus?.strategy_enabled ? 'text-green-400' : 'text-gray-400'}`}>
                        {hedgerStatus?.strategy_enabled ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                      
                      {!hedgerOnline && (
                        <div className="flex items-center space-x-1 px-2 py-1 bg-red-900/30 rounded-md border border-red-500/30">
                          <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" />
                          <span className="text-red-400 text-xs font-medium">Service Down</span>
                        </div>
                      )}
                      
                      <button
                        onClick={toggleHedgerStrategy}
                        disabled={actionLoading !== null || !hedgerOnline}
                        className={`relative w-14 h-7 rounded-full transition-all duration-500 ${
                          hedgerStatus?.strategy_enabled
                            ? 'bg-gradient-to-r from-green-400 to-green-600 shadow-lg shadow-green-500/50' 
                            : 'bg-gradient-to-r from-gray-600 to-gray-800'
                        } disabled:opacity-50 border-2 border-white/20`}
                      >
                        <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-all duration-500 ${
                          hedgerStatus?.strategy_enabled ? 'translate-x-7' : 'translate-x-0.5'
                        }`} />
                        {actionLoading === 'hedger' && (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          </div>
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Metrics */}
                <div className="p-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Capital</p>
                    <p className="text-white font-bold text-sm">{formatCurrency(hedgerConfig.capital)}</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Mode</p>
                    <p className="text-white font-bold text-sm">{hedgerStatus?.mode?.toUpperCase() || 'PAPER'}</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Positions</p>
                    <p className="text-white font-bold text-sm">{hedgerStatus?.positions?.position_count || 0}</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Trading Time</p>
                    <p className={`font-bold text-sm ${hedgerStatus?.is_trading_time ? 'text-green-400' : 'text-gray-400'}`}>
                      {hedgerStatus?.is_trading_time ? 'Yes' : 'No'}
                    </p>
                  </div>
                </div>

                <div className="p-4 border-t border-gray-700/30">
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-400">Running:</span>
                      <span className={`ml-2 font-bold ${hedgerStatus?.running ? 'text-green-400' : 'text-gray-400'}`}>
                        {hedgerStatus?.running ? 'Yes' : 'No'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">Service Mode:</span>
                      <span className="ml-2 text-green-400 font-bold">{hedgerStatus?.mode?.toUpperCase() || 'PAPER'}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Trading Mode:</span>
                      <span className={`ml-2 font-bold ${tradingMode === 'live' ? 'text-red-400' : 'text-blue-400'}`}>
                        {tradingMode.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Config Panel */}
              <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4">
                <h4 className="text-sm font-semibold text-white mb-4 flex items-center space-x-2">
                  <Settings className="h-4 w-4" />
                  <span>Configuration</span>
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Capital (₹)</label>
                    <input
                      type="number"
                      value={hedgerConfig.capital}
                      onChange={(e) => setHedgerConfig(prev => ({ ...prev, capital: Number(e.target.value) }))}
                      className="w-full bg-gray-700/50 border border-gray-600/30 rounded-md px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Max Daily Loss (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={hedgerConfig.max_daily_loss * 100}
                      onChange={(e) => setHedgerConfig(prev => ({ ...prev, max_daily_loss: Number(e.target.value) / 100 }))}
                      className="w-full bg-gray-700/50 border border-gray-600/30 rounded-md px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Dhan Access Token</label>
                    <input
                      type="password"
                      value={hedgerConfig.dhan_access_token || ''}
                      onChange={(e) => setHedgerConfig(prev => ({ ...prev, dhan_access_token: e.target.value }))}
                      className="w-full bg-gray-700/50 border border-gray-600/30 rounded-md px-2 py-1.5 text-white text-sm"
                      placeholder="Enter token"
                    />
                  </div>
                  <button
                    onClick={saveHedgerConfig}
                    disabled={actionLoading !== null || !hedgerOnline}
                    className="w-full mt-3 px-3 py-2 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm transition-all"
                  >
                    {actionLoading === 'hedger-config' ? 'Saving...' : 'Save Configuration'}
                  </button>
                  
                  {/* Connection Status */}
                  <div className="pt-3 mt-3 border-t border-gray-700/30">
                    <h5 className="text-xs font-semibold text-gray-400 mb-2">Connections</h5>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Service</span>
                        <div className="flex items-center space-x-1">
                          <div className={`w-1.5 h-1.5 rounded-full ${hedgerOnline ? 'bg-green-400' : 'bg-red-400'}`} />
                          <span className={hedgerOnline ? 'text-green-400' : 'text-red-400'}>
                            {hedgerOnline ? 'Online' : 'Offline'}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Port</span>
                        <span className="text-gray-300">4003</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ===== ELITE EQUITY TAB ===== */}
        {activeTab === 'elite-equity' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
              <div className="xl:col-span-3 bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 overflow-hidden">
                <div className="p-4 border-b border-gray-700/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
                        <Rocket className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-white">Elite Equity Service</h3>
                        <p className="text-gray-400 text-sm">High-velocity F&O stock trading with Gemini AI</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-4">
                      <span className={`text-sm font-medium ${equityStatus?.strategy_enabled ? 'text-green-400' : 'text-gray-400'}`}>
                        {equityStatus?.strategy_enabled ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                      
                      {!equityOnline && (
                        <div className="flex items-center space-x-1 px-2 py-1 bg-red-900/30 rounded-md border border-red-500/30">
                          <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" />
                          <span className="text-red-400 text-xs font-medium">Service Down</span>
                        </div>
                      )}
                      
                      <button
                        onClick={toggleEquityStrategy}
                        disabled={actionLoading !== null || !equityOnline}
                        className={`relative w-14 h-7 rounded-full transition-all duration-500 ${
                          equityStatus?.strategy_enabled
                            ? 'bg-gradient-to-r from-green-400 to-green-600 shadow-lg shadow-green-500/50' 
                            : 'bg-gradient-to-r from-gray-600 to-gray-800'
                        } disabled:opacity-50 border-2 border-white/20`}
                      >
                        <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-all duration-500 ${
                          equityStatus?.strategy_enabled ? 'translate-x-7' : 'translate-x-0.5'
                        }`} />
                        {actionLoading === 'equity' && (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          </div>
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Metrics */}
                <div className="p-4 grid grid-cols-2 lg:grid-cols-3 gap-3">
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Capital</p>
                    <p className="text-white font-bold text-sm">{formatCurrency(equityConfig.capital)}</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Mode</p>
                    <p className="text-white font-bold text-sm uppercase">{equityStatus?.mode || 'paper'}</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                    <p className="text-gray-400 text-xs">Trading Time</p>
                    <p className={`font-bold text-sm ${equityStatus?.is_trading_time ? 'text-green-400' : 'text-gray-400'}`}>
                      {equityStatus?.is_trading_time ? 'Yes' : 'No'}
                    </p>
                  </div>
                </div>

                <div className="p-4 border-t border-gray-700/30">
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-400">Running:</span>
                      <span className={`ml-2 font-bold ${equityStatus?.running ? 'text-green-400' : 'text-gray-400'}`}>
                        {equityStatus?.running ? 'Yes' : 'No'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">Database:</span>
                      <span className={`ml-2 font-bold ${equityStatus?.database_connected ? 'text-green-400' : 'text-red-400'}`}>
                        {equityStatus?.database_connected ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">Gemini AI:</span>
                      <span className={`ml-2 font-bold ${equityStatus?.gemini_connected ? 'text-green-400' : 'text-yellow-400'}`}>
                        {equityStatus?.gemini_connected ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Config Panel */}
              <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-700/30 p-4">
                <h4 className="text-sm font-semibold text-white mb-4 flex items-center space-x-2">
                  <Settings className="h-4 w-4" />
                  <span>Configuration</span>
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Capital (₹)</label>
                    <input
                      type="number"
                      value={equityConfig.capital}
                      onChange={(e) => setEquityConfig(prev => ({ ...prev, capital: Number(e.target.value) }))}
                      className="w-full bg-gray-700/50 border border-gray-600/30 rounded-md px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Max Daily Loss (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={equityConfig.max_daily_loss * 100}
                      onChange={(e) => setEquityConfig(prev => ({ ...prev, max_daily_loss: Number(e.target.value) / 100 }))}
                      className="w-full bg-gray-700/50 border border-gray-600/30 rounded-md px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Dhan Access Token</label>
                    <input
                      type="password"
                      value={equityConfig.dhan_access_token || ''}
                      onChange={(e) => setEquityConfig(prev => ({ ...prev, dhan_access_token: e.target.value }))}
                      className="w-full bg-gray-700/50 border border-gray-600/30 rounded-md px-2 py-1.5 text-white text-sm"
                      placeholder="Enter token"
                    />
                  </div>
                  <button
                    onClick={saveEquityConfig}
                    disabled={actionLoading !== null || !equityOnline}
                    className="w-full mt-3 px-3 py-2 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg hover:from-purple-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm transition-all"
                  >
                    {actionLoading === 'equity-config' ? 'Saving...' : 'Save Configuration'}
                  </button>
                  
                  {/* Connection Status */}
                  <div className="pt-3 mt-3 border-t border-gray-700/30">
                    <h5 className="text-xs font-semibold text-gray-400 mb-2">Connections</h5>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Service</span>
                        <div className="flex items-center space-x-1">
                          <div className={`w-1.5 h-1.5 rounded-full ${equityOnline ? 'bg-green-400' : 'bg-red-400'}`} />
                          <span className={equityOnline ? 'text-green-400' : 'text-red-400'}>
                            {equityOnline ? 'Online' : 'Offline'}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Database</span>
                        <div className="flex items-center space-x-1">
                          <div className={`w-1.5 h-1.5 rounded-full ${equityStatus?.database_connected ? 'bg-green-400' : 'bg-red-400'}`} />
                          <span className={equityStatus?.database_connected ? 'text-green-400' : 'text-red-400'}>
                            {equityStatus?.database_connected ? 'Connected' : 'Disconnected'}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Gemini AI</span>
                        <div className="flex items-center space-x-1">
                          <div className={`w-1.5 h-1.5 rounded-full ${equityStatus?.gemini_connected ? 'bg-green-400' : 'bg-yellow-400'}`} />
                          <span className={equityStatus?.gemini_connected ? 'text-green-400' : 'text-yellow-400'}>
                            {equityStatus?.gemini_connected ? 'Connected' : 'Disconnected'}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Port</span>
                        <span className="text-gray-300">5080</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StrategiesPage;
