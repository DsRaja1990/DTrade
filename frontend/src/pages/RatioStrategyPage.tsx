import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Progress } from '../components/ui/progress';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  Shield,
  AlertTriangle,
  Settings,
  BarChart3,
  Zap
} from 'lucide-react';

interface RatioStrategyData {
  active: boolean;
  current_phase: string;
  market_hours: boolean;
  position_sizes: Record<string, number>;
  premium_targets: Record<string, any>;
  positions: Record<string, any>;
  daily_stats: {
    trades_executed: number;
    total_pnl: number;
    win_count: number;
    loss_count: number;
  };
}

interface DashboardData {
  monitoring_active: boolean;
  premium_data: Record<string, any>;
  performance_metrics: Record<string, any>;
  position_tracking: Record<string, any>;
  recent_alerts: Array<any>;
  market_status: string;
}

interface RiskMetrics {
  daily_pnl: number;
  capital_utilization: number;
  position_concentration: Record<string, number>;
  halt_trading: boolean;
}

const RatioStrategyPage: React.FC = () => {
  const [strategyData, setStrategyData] = useState<RatioStrategyData | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Configuration state
  const [configMode, setConfigMode] = useState(false);
  const [tempConfig, setTempConfig] = useState({
    nifty_lots: 20,
    banknifty_lots: 30,
    sensex_lots: 50,
    capital: 10000000
  });

  const API_BASE = 'http://localhost:8000/api';

  const fetchStrategyStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/ratio_strategy/status`);
      const result = await response.json();
      
      if (result.success) {
        setStrategyData(result.data);
      } else {
        setError('Failed to fetch strategy status');
      }
    } catch (err) {
      setError('Error fetching strategy status');
      console.error(err);
    }
  }, []);

  const fetchDashboardData = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/ratio_strategy/dashboard`);
      const result = await response.json();
      
      if (result.success) {
        setDashboardData(result.data);
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    }
  }, []);

  const fetchRiskMetrics = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/ratio_strategy/risk_metrics`);
      const result = await response.json();
      
      if (result.success) {
        setRiskMetrics(result.data);
      }
    } catch (err) {
      console.error('Error fetching risk metrics:', err);
    }
  }, []);

  const toggleStrategy = async () => {
    if (!strategyData) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const endpoint = strategyData.active ? 'disable' : 'enable';
      const response = await fetch(`${API_BASE}/ratio_strategy/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const result = await response.json();
      
      if (result.success || result.status === 'success') {
        await fetchStrategyStatus();
      } else {
        setError(result.message || 'Failed to toggle strategy');
      }
    } catch (err) {
      setError('Error toggling strategy');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const executeStrategy = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/ratio_strategy/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const result = await response.json();
      
      if (result.success) {
        await fetchStrategyStatus();
        await fetchDashboardData();
      } else {
        setError('Failed to execute strategy');
      }
    } catch (err) {
      setError('Error executing strategy');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const updateConfiguration = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Update capital
      await fetch(`${API_BASE}/ratio_strategy/capital`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capital: tempConfig.capital })
      });

      // Update position sizes
      const configPayload = {
        position_sizes: {
          NIFTY: tempConfig.nifty_lots,
          BANKNIFTY: tempConfig.banknifty_lots,
          SENSEX: tempConfig.sensex_lots
        }
      };

      const response = await fetch(`${API_BASE}/ratio_strategy/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configPayload)
      });
      
      const result = await response.json();
      
      if (result.success) {
        setConfigMode(false);
        await fetchStrategyStatus();
      } else {
        setError('Failed to update configuration');
      }
    } catch (err) {
      setError('Error updating configuration');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStrategyStatus();
    fetchDashboardData();
    fetchRiskMetrics();
    setLastUpdate(new Date());

    // Set up polling for real-time updates
    const interval = setInterval(() => {
      fetchStrategyStatus();
      fetchDashboardData();
      fetchRiskMetrics();
      setLastUpdate(new Date());
    }, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, [fetchStrategyStatus, fetchDashboardData, fetchRiskMetrics]);

  const getPhaseColor = (phase: string) => {
    switch (phase) {
      case 'MORNING': return 'bg-green-500';
      case 'MIDDAY': return 'bg-yellow-500';
      case 'CLOSING': return 'bg-orange-500';
      default: return 'bg-gray-500';
    }
  };

  const formatCurrency = (amount: number) => {
    if (Math.abs(amount) >= 10000000) {
      return `₹${(amount / 10000000).toFixed(2)}Cr`;
    } else if (Math.abs(amount) >= 100000) {
      return `₹${(amount / 100000).toFixed(2)}L`;
    } else {
      return `₹${amount.toLocaleString()}`;
    }
  };

  const winRate = strategyData?.daily_stats 
    ? (strategyData.daily_stats.win_count / Math.max(1, strategyData.daily_stats.win_count + strategyData.daily_stats.loss_count)) * 100
    : 0;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Zap className="h-8 w-8 text-blue-500" />
            Ratio Strategy
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Institutional-grade options trading with 98%+ win rate potential
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          {lastUpdate && (
            <span className="text-sm text-gray-500">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          
          <Button
            onClick={() => setConfigMode(!configMode)}
            variant="outline"
            size="sm"
          >
            <Settings className="h-4 w-4 mr-2" />
            Configure
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main Control Panel */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Strategy Control</h2>
            <div className="flex items-center gap-4">
              <Badge variant={strategyData?.market_hours ? "default" : "secondary"}>
                Market {strategyData?.market_hours ? "Open" : "Closed"}
              </Badge>
              <Badge className={getPhaseColor(strategyData?.current_phase || "CLOSED")}>
                {strategyData?.current_phase || "CLOSED"}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Strategy Toggle */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="strategy-toggle" className="text-base font-medium">
                  Strategy Status
                </Label>
                <Switch
                  id="strategy-toggle"
                  checked={strategyData?.active || false}
                  onCheckedChange={toggleStrategy}
                  disabled={loading}
                />
              </div>
              
              <div className="text-sm text-gray-600">
                {strategyData?.active ? (
                  <span className="text-green-600 font-medium">● Active</span>
                ) : (
                  <span className="text-gray-500">○ Inactive</span>
                )}
              </div>
            </div>

            {/* Manual Execution */}
            <div className="space-y-4">
              <Button
                onClick={executeStrategy}
                disabled={loading || !strategyData?.active}
                className="w-full"
              >
                <Activity className="h-4 w-4 mr-2" />
                Execute Now
              </Button>
            </div>

            {/* Win Rate Display */}
            <div className="space-y-2">
              <Label className="text-base font-medium">Win Rate</Label>
              <div className="flex items-center gap-2">
                <Progress value={winRate} className="flex-1" />
                <span className="text-sm font-medium">{winRate.toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Modal */}
      {configMode && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Strategy Configuration</h3>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="nifty-lots">NIFTY Lots</Label>
                  <Input
                    id="nifty-lots"
                    type="number"
                    value={tempConfig.nifty_lots}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTempConfig(prev => ({
                      ...prev,
                      nifty_lots: parseInt(e.target.value) || 0
                    }))}
                    max={24}
                    min={1}
                  />
                  <span className="text-xs text-gray-500">Max: 24 (freeze limit)</span>
                </div>

                <div>
                  <Label htmlFor="banknifty-lots">BANKNIFTY Lots</Label>
                  <Input
                    id="banknifty-lots"
                    type="number"
                    value={tempConfig.banknifty_lots}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTempConfig(prev => ({
                      ...prev,
                      banknifty_lots: parseInt(e.target.value) || 0
                    }))}
                    max={20}
                    min={1}
                  />
                  <span className="text-xs text-gray-500">Max: 20 (freeze limit)</span>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="sensex-lots">SENSEX Lots</Label>
                  <Input
                    id="sensex-lots"
                    type="number"
                    value={tempConfig.sensex_lots}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTempConfig(prev => ({
                      ...prev,
                      sensex_lots: parseInt(e.target.value) || 0
                    }))}
                    max={25}
                    min={1}
                  />
                  <span className="text-xs text-gray-500">Max: 25 (freeze limit)</span>
                </div>

                <div>
                  <Label htmlFor="capital">Capital (₹)</Label>
                  <Input
                    id="capital"
                    type="number"
                    value={tempConfig.capital}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTempConfig(prev => ({
                      ...prev,
                      capital: parseInt(e.target.value) || 0
                    }))}
                    min={1000000}
                  />
                  <span className="text-xs text-gray-500">Minimum: ₹10L</span>
                </div>
              </div>
            </div>

            <div className="flex gap-4 mt-6">
              <Button onClick={updateConfiguration} disabled={loading}>
                Update Configuration
              </Button>
              <Button variant="outline" onClick={() => setConfigMode(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metrics Dashboard */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="risk">Risk Metrics</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Daily P&L */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Daily P&L</p>
                    <p className={`text-2xl font-bold ${
                      (strategyData?.daily_stats?.total_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatCurrency(strategyData?.daily_stats?.total_pnl || 0)}
                    </p>
                  </div>
                  {(strategyData?.daily_stats?.total_pnl || 0) >= 0 ? (
                    <TrendingUp className="h-8 w-8 text-green-600" />
                  ) : (
                    <TrendingDown className="h-8 w-8 text-red-600" />
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Trades Executed */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Trades Today</p>
                    <p className="text-2xl font-bold">
                      {strategyData?.daily_stats?.trades_executed || 0}
                    </p>
                  </div>
                  <BarChart3 className="h-8 w-8 text-blue-600" />
                </div>
              </CardContent>
            </Card>

            {/* Win Rate */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Win Rate</p>
                    <p className="text-2xl font-bold text-green-600">
                      {winRate.toFixed(1)}%
                    </p>
                  </div>
                  <Target className="h-8 w-8 text-green-600" />
                </div>
              </CardContent>
            </Card>

            {/* Risk Status */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Risk Status</p>
                    <p className={`text-sm font-bold ${
                      riskMetrics?.halt_trading ? 'text-red-600' : 'text-green-600'
                    }`}>
                      {riskMetrics?.halt_trading ? 'HALTED' : 'HEALTHY'}
                    </p>
                  </div>
                  <Shield className={`h-8 w-8 ${
                    riskMetrics?.halt_trading ? 'text-red-600' : 'text-green-600'
                  }`} />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="positions" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {['NIFTY', 'BANKNIFTY', 'SENSEX'].map((index) => {
              const position = strategyData?.positions?.[index];
              const positionSize = strategyData?.position_sizes?.[index] || 0;
              
              return (
                <Card key={index}>
                  <CardHeader>
                    <h3 className="text-lg font-semibold">{index}</h3>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Position Size:</span>
                        <span className="font-medium">{positionSize} lots</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Current Lots:</span>
                        <span className="font-medium">{position?.lots || 0} lots</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Avg Entry:</span>
                        <span className="font-medium">₹{position?.avg_entry_price?.toFixed(2) || '0.00'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Unrealized P&L:</span>
                        <span className={`font-medium ${
                          (position?.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          ₹{position?.unrealized_pnl?.toFixed(2) || '0.00'}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="risk" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold">Risk Metrics</h3>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Capital Utilization:</span>
                    <span className="font-medium">
                      {((riskMetrics?.capital_utilization || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Daily P&L:</span>
                    <span className={`font-medium ${
                      (riskMetrics?.daily_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatCurrency(riskMetrics?.daily_pnl || 0)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Trading Status:</span>
                    <Badge variant={riskMetrics?.halt_trading ? "destructive" : "default"}>
                      {riskMetrics?.halt_trading ? 'Halted' : 'Active'}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold">Position Concentration</h3>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(riskMetrics?.position_concentration || {}).map(([index, concentration]) => (
                    <div key={index} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>{index}</span>
                        <span>{((concentration as number) * 100).toFixed(1)}%</span>
                      </div>
                      <Progress value={(concentration as number) * 100} className="h-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-600">Total Trades</p>
                  <p className="text-3xl font-bold">
                    {strategyData?.daily_stats?.trades_executed || 0}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-600">Winning Trades</p>
                  <p className="text-3xl font-bold text-green-600">
                    {strategyData?.daily_stats?.win_count || 0}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-600">Losing Trades</p>
                  <p className="text-3xl font-bold text-red-600">
                    {strategyData?.daily_stats?.loss_count || 0}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-600">Profit Factor</p>
                  <p className="text-3xl font-bold text-blue-600">
                    {strategyData?.daily_stats?.loss_count 
                      ? (Math.abs(strategyData.daily_stats.total_pnl) / strategyData.daily_stats.loss_count).toFixed(2)
                      : '∞'
                    }
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Recent Alerts */}
      {dashboardData?.recent_alerts && dashboardData.recent_alerts.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Recent Alerts</h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {dashboardData.recent_alerts.slice(0, 5).map((alert, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <div className="flex items-center gap-2">
                    <Badge variant={alert.severity === 'warning' ? 'destructive' : 'default'}>
                      {alert.type}
                    </Badge>
                    <span className="text-sm">{alert.index}</span>
                    <span className="text-sm text-gray-600">{alert.action}</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default RatioStrategyPage;
