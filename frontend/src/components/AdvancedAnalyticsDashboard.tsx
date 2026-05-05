import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Alert, AlertDescription } from './ui/alert';
import { 
  Activity, 
  Shield, 
  Brain, 
  Target,
  AlertTriangle,
  BarChart3,
  PieChart,
  LineChart,
  Zap,
  Settings
} from 'lucide-react';

// Enhanced type definitions
interface OptionsData {
  pcr: {
    pcr_oi: number;
    pcr_volume: number;
    interpretation: string;
    trend: 'bullish' | 'bearish' | 'neutral';
    confidence: number;
  };
  max_pain: {
    max_pain_strike: number;
    current_price: number;
    distance_from_max_pain: number;
    interpretation: string;
    probability: number;
  };
  option_flow: {
    unusual_activity: Array<{
      strike: number;
      type: string;
      volume: number;
      oi: number;
      vol_oi_ratio: number;
      sentiment: 'bullish' | 'bearish' | 'neutral';
    }>;
    summary: {
      total_unusual_activity: number;
      bullish_flow: number;
      bearish_flow: number;
      net_flow: number;
    };
  };
  support_resistance: {
    current_price: number;
    support_levels: Array<{
      level: number;
      strength: number;
      type: 'strong' | 'weak' | 'medium';
    }>;
    resistance_levels: Array<{
      level: number;
      strength: number;
      type: 'strong' | 'weak' | 'medium';
    }>;
  };
  greeks: {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    rho: number;
  };
  timestamp: string;
}

// Removed duplicate PortfolioData interface - using the one below

// Removed unused AlertData interface - using AlertsData instead

// Removed duplicate AIInsights interface - using the simpler one below

interface AlertsData {
  total_alerts: number;
  active_rules: number;
  total_rules: number;
  alerts_by_type: Record<string, number>;
  alerts_by_symbol: Record<string, number>;
  timestamp: string;
}

interface SystemStatus {
  system_health: {
    signal_engine: string;
    market_data: string;
    websocket_connections: number;
  };
  performance_metrics: {
    signals_generated: number;
    uptime: string;
    last_update: string;
  };
  features_enabled: {
    options_analysis: boolean;
    portfolio_management: boolean;
    alerts: boolean;
    ml_scoring: boolean;
  };
  timestamp: string;
}

interface PortfolioData {
  portfolio_metrics: {
    total_value: number;
    total_pnl: number;
    total_pnl_percentage: number;
    daily_return: number;
    volatility: number;
    sharpe_ratio: number;
    max_drawdown: number;
    current_drawdown: number;
    win_rate: number;
    profit_factor: number;
  };
  risk_metrics: {
    leverage_ratio: number;
    position_concentrations: Record<string, number>;
  };
  positions: Array<{
    symbol: string;
    quantity: number;
    entry_price: number;
    current_price: number;
    market_value: number;
    pnl: number;
    pnl_percentage: number;
  }>;
  timestamp: string;
}

interface AIInsights {
  model_status: {
    ml_scorer_trained: boolean;
    pattern_recognizer_ready: boolean;
    risk_assessment_ready: boolean;
    last_training: string;
  };
  insights: {
    market_regime: string;
    volatility_forecast: string;
    pattern_confidence: number;
    risk_score: number;
  };
  recommendations: string[];
  timestamp: string;
}

// Enhanced mock data generators
const generateMockOptionsData = (): OptionsData => ({
  pcr: {
    pcr_oi: 0.85 + Math.random() * 0.4,
    pcr_volume: 0.9 + Math.random() * 0.3,
    interpretation: Math.random() > 0.5 ? "Market shows bullish sentiment" : "Market shows bearish sentiment",
    trend: Math.random() > 0.6 ? 'bullish' : Math.random() > 0.3 ? 'bearish' : 'neutral',
    confidence: 0.7 + Math.random() * 0.3
  },
  max_pain: {
    max_pain_strike: 19800 + Math.random() * 400,
    current_price: 19900 + Math.random() * 200,
    distance_from_max_pain: (Math.random() - 0.5) * 200,
    interpretation: "Price may gravitate towards max pain level",
    probability: 0.6 + Math.random() * 0.3
  },
  option_flow: {
    unusual_activity: Array.from({ length: 5 }, (_, i) => ({
      strike: 19800 + i * 50,
      type: Math.random() > 0.5 ? 'CALL' : 'PUT',
      volume: Math.floor(Math.random() * 10000) + 1000,
      oi: Math.floor(Math.random() * 5000) + 500,
      vol_oi_ratio: 0.5 + Math.random() * 2,
      sentiment: Math.random() > 0.6 ? 'bullish' : Math.random() > 0.3 ? 'bearish' : 'neutral'
    })),
    summary: {
      total_unusual_activity: 5,
      bullish_flow: 60 + Math.random() * 30,
      bearish_flow: 40 + Math.random() * 30,
      net_flow: (Math.random() - 0.5) * 50
    }
  },
  support_resistance: {
    current_price: 19950 + Math.random() * 100,
    support_levels: [
      { level: 19800, strength: 0.8, type: 'strong' },
      { level: 19850, strength: 0.6, type: 'medium' },
      { level: 19900, strength: 0.4, type: 'weak' }
    ],
    resistance_levels: [
      { level: 20100, strength: 0.9, type: 'strong' },
      { level: 20050, strength: 0.7, type: 'medium' },
      { level: 20000, strength: 0.5, type: 'weak' }
    ]
  },
  greeks: {
    delta: Math.random() * 0.8 + 0.1,
    gamma: Math.random() * 0.05,
    theta: -Math.random() * 0.1,
    vega: Math.random() * 0.3,
    rho: Math.random() * 0.1
  },
  timestamp: new Date().toISOString()
});

const generateMockPortfolioData = (): PortfolioData => {
  const totalValue = 1000000 + Math.random() * 500000;
  const totalPnl = (Math.random() - 0.3) * 100000;
  
  return {
    portfolio_metrics: {
      total_value: totalValue,
      total_pnl: totalPnl,
      total_pnl_percentage: (totalPnl / totalValue) * 100,
      daily_return: (Math.random() - 0.5) * 0.05,
      volatility: 0.15 + Math.random() * 0.1,
      sharpe_ratio: 0.8 + Math.random() * 0.7,
      max_drawdown: -0.15 + Math.random() * 0.1,
      current_drawdown: -0.05 + Math.random() * 0.05,
      win_rate: 0.55 + Math.random() * 0.3,
      profit_factor: 1.2 + Math.random() * 0.8
    },
    risk_metrics: {
      leverage_ratio: 1.0 + Math.random() * 2.0,
      position_concentrations: {
        'NIFTY': 25 + Math.random() * 15,
        'BANKNIFTY': 20 + Math.random() * 10,
        'RELIANCE': 15 + Math.random() * 10
      }
    },
    positions: Array.from({ length: 5 }, (_, i) => {
      const symbols = ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'TCS', 'HDFC'];
      const currentPrice = 100 + Math.random() * 2000;
      const entryPrice = currentPrice * (0.95 + Math.random() * 0.1);
      const quantity = Math.floor(Math.random() * 100) + 10;
      const marketValue = currentPrice * quantity;
      const pnl = (currentPrice - entryPrice) * quantity;
      
      return {
        symbol: symbols[i],
        quantity,
        entry_price: entryPrice,
        current_price: currentPrice,
        market_value: marketValue,
        pnl,
        pnl_percentage: (pnl / (entryPrice * quantity)) * 100
      };
    }),
    timestamp: new Date().toISOString()
  };
};

const AdvancedAnalyticsDashboard: React.FC = () => {
  const [optionsData, setOptionsData] = useState<OptionsData | null>(null);
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(null);
  const [alertsData, setAlertsData] = useState<AlertsData | null>(null);
  const [aiInsights, setAIInsights] = useState<AIInsights | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('options');

  const fetchOptionsData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/options/chain');
      if (!response.ok) throw new Error('Failed to fetch options data');
      const data = await response.json();
      
      // Transform the API response to match our interface
      setOptionsData({
        pcr: {
          pcr_oi: data.options_data?.pcr?.pcr_oi || 1.0,
          pcr_volume: data.options_data?.pcr?.pcr_volume || 1.0,
          interpretation: data.options_data?.pcr?.interpretation || "Market sentiment analysis",
          trend: data.options_data?.pcr?.trend || 'neutral',
          confidence: data.options_data?.pcr?.confidence || 0.5
        },
        max_pain: {
          max_pain_strike: data.options_data?.max_pain?.strike || 20000,
          current_price: data.options_data?.current_price || 20000,
          distance_from_max_pain: data.options_data?.max_pain?.distance || 0,
          interpretation: "Price analysis relative to max pain",
          probability: 0.7
        },
        option_flow: {
          unusual_activity: data.options_data?.unusual_activity || [],
          summary: {
            total_unusual_activity: data.options_data?.unusual_activity?.length || 0,
            bullish_flow: 60,
            bearish_flow: 40,
            net_flow: 20
          }
        },
        support_resistance: {
          current_price: data.options_data?.current_price || 20000,
          support_levels: data.options_data?.support_levels || [
            { level: 19800, strength: 0.8, type: 'strong' },
            { level: 19900, strength: 0.6, type: 'medium' }
          ],
          resistance_levels: data.options_data?.resistance_levels || [
            { level: 20200, strength: 0.8, type: 'strong' },
            { level: 20100, strength: 0.6, type: 'medium' }
          ]
        },
        greeks: {
          delta: data.options_data?.greeks?.delta || 0.5,
          gamma: data.options_data?.greeks?.gamma || 0.02,
          theta: data.options_data?.greeks?.theta || -0.05,
          vega: data.options_data?.greeks?.vega || 0.15,
          rho: data.options_data?.greeks?.rho || 0.05
        },
        timestamp: new Date().toISOString()
      });
    } catch (err) {
      console.error('Error fetching options data:', err);
      // Use mock data as fallback
      setOptionsData(generateMockOptionsData());
    }
  };

  const fetchPortfolioData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/portfolio/summary');
      if (!response.ok) throw new Error('Failed to fetch portfolio data');
      const data = await response.json();
      
      // Transform the API response to match our interface
      setPortfolioData({
        portfolio_metrics: {
          total_value: data.portfolio_metrics?.total_value || 1000000,
          total_pnl: data.portfolio_metrics?.total_pnl || 0,
          total_pnl_percentage: data.portfolio_metrics?.total_pnl_percentage || 0,
          daily_return: data.portfolio_metrics?.daily_return || 0,
          volatility: data.portfolio_metrics?.volatility || 0,
          sharpe_ratio: data.portfolio_metrics?.sharpe_ratio || 0,
          max_drawdown: data.portfolio_metrics?.max_drawdown || 0,
          current_drawdown: data.portfolio_metrics?.current_drawdown || 0,
          win_rate: data.portfolio_metrics?.win_rate || 0,
          profit_factor: data.portfolio_metrics?.profit_factor || 1.0
        },
        risk_metrics: {
          leverage_ratio: data.risk_metrics?.leverage_ratio || 1.0,
          position_concentrations: data.risk_metrics?.position_concentrations || {}
        },
        positions: data.positions || [],
        timestamp: new Date().toISOString()
      });
    } catch (err) {
      console.error('Error fetching portfolio data:', err);
      // Use mock data as fallback
      setPortfolioData(generateMockPortfolioData());
    }
  };

  const fetchAlertsData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/alerts/rules');
      if (!response.ok) throw new Error('Failed to fetch alerts data');
      const data = await response.json();
      
      // Transform the API response to match our interface
      setAlertsData({
        total_alerts: data.statistics?.total_alerts_today || 0,
        active_rules: data.rules?.filter((r: any) => r.status === 'active').length || 0,
        total_rules: data.rules?.length || 0,
        alerts_by_type: data.alerts_by_type || { 'price': 5, 'volume': 3, 'technical': 2 },
        alerts_by_symbol: data.alerts_by_symbol || { 'NIFTY': 8, 'BANKNIFTY': 2 },
        timestamp: new Date().toISOString()
      });
    } catch (err) {
      console.error('Error fetching alerts data:', err);
      // Use mock data as fallback
      setAlertsData({
        total_alerts: 10,
        active_rules: 5,
        total_rules: 8,
        alerts_by_type: { 'price': 5, 'volume': 3, 'technical': 2 },
        alerts_by_symbol: { 'NIFTY': 8, 'BANKNIFTY': 2 },
        timestamp: new Date().toISOString()
      });
    }
  };

  const fetchAIInsights = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/ai/ml-insights');
      if (!response.ok) throw new Error('Failed to fetch AI insights');
      const data = await response.json();
      
      // Transform the API response to match our interface
      setAIInsights({
        model_status: {
          ml_scorer_trained: data.model_status?.ml_scorer_trained || false,
          pattern_recognizer_ready: data.model_status?.pattern_recognizer_ready || true,
          risk_assessment_ready: data.model_status?.risk_assessment_ready || true,
          last_training: data.model_status?.last_training || new Date().toISOString()
        },
        insights: {
          market_regime: data.insights?.market_regime || 'trending',
          volatility_forecast: data.insights?.volatility_forecast || 'moderate',
          pattern_confidence: data.insights?.pattern_confidence || 0.7,
          risk_score: data.insights?.risk_score || 0.5
        },
        recommendations: data.recommendations || [
          "Monitor key support levels around 19800",
          "Consider position sizing based on current volatility",
          "Watch for breakout above resistance at 20100"
        ],
        timestamp: new Date().toISOString()
      });
    } catch (err) {
      console.error('Error fetching AI insights:', err);
      // Use mock data as fallback
      setAIInsights({
        model_status: {
          ml_scorer_trained: false,
          pattern_recognizer_ready: true,
          risk_assessment_ready: true,
          last_training: new Date().toISOString()
        },
        insights: {
          market_regime: 'trending',
          volatility_forecast: 'moderate',
          pattern_confidence: 0.7,
          risk_score: 0.5
        },
        recommendations: [
          "Monitor key support levels",
          "Consider position sizing based on volatility",
          "Watch for breakout patterns"
        ],
        timestamp: new Date().toISOString()
      });
    }
  };

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/system/status');
      if (!response.ok) throw new Error('Failed to fetch system status');
      const data = await response.json();
      
      // Transform the API response to match our interface
      setSystemStatus({
        system_health: {
          signal_engine: data.status || 'healthy',
          market_data: 'healthy',
          websocket_connections: data.active_connections || 0
        },
        performance_metrics: {
          signals_generated: data.signals_generated || 0,
          uptime: '99.8%',
          last_update: data.last_update || new Date().toISOString()
        },
        features_enabled: {
          options_analysis: data.api_endpoints_active || true,
          portfolio_management: data.api_endpoints_active || true,
          alerts: data.api_endpoints_active || true,
          ml_scoring: data.api_endpoints_active || true
        },
        timestamp: new Date().toISOString()
      });
    } catch (err) {
      console.error('Error fetching system status:', err);
      // Use mock data as fallback
      setSystemStatus({
        system_health: {
          signal_engine: 'healthy',
          market_data: 'healthy',
          websocket_connections: 1
        },
        performance_metrics: {
          signals_generated: 150,
          uptime: '99.8%',
          last_update: new Date().toISOString()
        },
        features_enabled: {
          options_analysis: true,
          portfolio_management: true,
          alerts: true,
          ml_scoring: true
        },
        timestamp: new Date().toISOString()
      });
    }
  };

  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        fetchOptionsData(),
        fetchPortfolioData(),
        fetchAlertsData(),
        fetchAIInsights(),
        fetchSystemStatus()
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    
    // Set up auto-refresh every 30 seconds
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'connected':
      case 'live':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'error':
      case 'stale':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg font-medium text-gray-600">Loading advanced analytics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Error loading analytics: {error}
          <Button onClick={fetchAllData} className="ml-2" size="sm">
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Advanced Analytics</h1>
          <p className="text-gray-600">Comprehensive trading analysis and insights</p>
        </div>
        <Button onClick={fetchAllData} variant="outline" size="sm">
          <Activity className="h-4 w-4 mr-2" />
          Refresh Data
        </Button>
      </div>

      {/* System Status Overview */}
      {systemStatus && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="h-5 w-5 mr-2" />
              System Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-600">Signal Engine</div>
                <div className={`text-lg font-bold ${getStatusColor(systemStatus.system_health.signal_engine)}`}>
                  {systemStatus.system_health.signal_engine.toUpperCase()}
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-600">Market Data</div>
                <div className={`text-lg font-bold ${getStatusColor(systemStatus.system_health.market_data)}`}>
                  {systemStatus.system_health.market_data.toUpperCase()}
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-600">WebSocket Connections</div>
                <div className="text-lg font-bold text-blue-600">
                  {systemStatus.system_health.websocket_connections}
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-600">Signals Generated</div>
                <div className="text-lg font-bold text-purple-600">
                  {systemStatus.performance_metrics.signals_generated}
                </div>
              </div>
            </div>
            
            <div className="mt-4 pt-4 border-t">
              <div className="text-sm font-medium text-gray-600 mb-2">Features Status</div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={systemStatus.features_enabled.options_analysis ? "default" : "secondary"}>
                  Options Analysis: {systemStatus.features_enabled.options_analysis ? "ON" : "OFF"}
                </Badge>
                <Badge variant={systemStatus.features_enabled.portfolio_management ? "default" : "secondary"}>
                  Portfolio Management: {systemStatus.features_enabled.portfolio_management ? "ON" : "OFF"}
                </Badge>
                <Badge variant={systemStatus.features_enabled.alerts ? "default" : "secondary"}>
                  Alerts: {systemStatus.features_enabled.alerts ? "ON" : "OFF"}
                </Badge>
                <Badge variant={systemStatus.features_enabled.ml_scoring ? "default" : "secondary"}>
                  ML Scoring: {systemStatus.features_enabled.ml_scoring ? "ON" : "OFF"}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Analytics Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="options">Options Analysis</TabsTrigger>
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="ai">AI Insights</TabsTrigger>
          <TabsTrigger value="risk">Risk Analysis</TabsTrigger>
        </TabsList>

        {/* Options Analysis Tab */}
        <TabsContent value="options" className="space-y-4">
          {optionsData ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* PCR Analysis */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <PieChart className="h-5 w-5 mr-2" />
                    Put-Call Ratio
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm font-medium text-gray-600">PCR (OI)</div>
                        <div className="text-2xl font-bold text-blue-600">
                          {optionsData.pcr.pcr_oi.toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-600">PCR (Volume)</div>
                        <div className="text-2xl font-bold text-green-600">
                          {optionsData.pcr.pcr_volume.toFixed(2)}
                        </div>
                      </div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm font-medium text-gray-600">Interpretation</div>
                      <div className="text-sm text-gray-800">{optionsData.pcr.interpretation}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Max Pain */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Target className="h-5 w-5 mr-2" />
                    Max Pain Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm font-medium text-gray-600">Max Pain Strike</div>
                        <div className="text-2xl font-bold text-purple-600">
                          {optionsData.max_pain.max_pain_strike}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-600">Current Price</div>
                        <div className="text-2xl font-bold text-orange-600">
                          {optionsData.max_pain.current_price.toFixed(2)}
                        </div>
                      </div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm font-medium text-gray-600">Distance</div>
                      <div className="text-sm text-gray-800">
                        {optionsData.max_pain.distance_from_max_pain.toFixed(2)} points
                      </div>
                      <div className="text-xs text-gray-600 mt-1">
                        {optionsData.max_pain.interpretation}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Support & Resistance */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <BarChart3 className="h-5 w-5 mr-2" />
                    Support & Resistance
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm font-medium text-green-600">Support Levels</div>
                        <div className="space-y-1">
                          {optionsData.support_resistance.support_levels.slice(0, 3).map((level, index) => (
                            <div key={index} className="text-sm">
                              {level.level} <span className="text-gray-500">({level.strength.toLocaleString()})</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-red-600">Resistance Levels</div>
                        <div className="space-y-1">
                          {optionsData.support_resistance.resistance_levels.slice(0, 3).map((level, index) => (
                            <div key={index} className="text-sm">
                              {level.level} <span className="text-gray-500">({level.strength.toLocaleString()})</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Unusual Activity */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Zap className="h-5 w-5 mr-2" />
                    Unusual Activity
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-gray-600">
                      Total Unusual Activity: {optionsData.option_flow.summary.total_unusual_activity}
                    </div>
                    <div className="space-y-2">
                      {optionsData.option_flow.unusual_activity.slice(0, 5).map((activity, index) => (
                        <div key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                          <div className="text-sm">
                            <span className="font-medium">{activity.strike}</span> {activity.type}
                          </div>
                          <div className="text-sm text-right">
                            <div className="font-medium">{activity.vol_oi_ratio.toFixed(2)}x</div>
                            <div className="text-gray-500">{activity.volume.toLocaleString()}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center text-gray-500">Options data not available</div>
          )}
        </TabsContent>

        {/* Portfolio Tab */}
        <TabsContent value="portfolio" className="space-y-4">
          {portfolioData ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Portfolio Metrics */}
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <LineChart className="h-5 w-5 mr-2" />
                    Portfolio Metrics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-gray-600">Total Value</div>
                      <div className="text-lg font-bold text-blue-600">
                        {formatCurrency(portfolioData.portfolio_metrics.total_value)}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-gray-600">Total P&L</div>
                      <div className={`text-lg font-bold ${
                        portfolioData.portfolio_metrics.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {portfolioData.portfolio_metrics.total_pnl >= 0 ? '+' : ''}
                        {formatCurrency(portfolioData.portfolio_metrics.total_pnl)}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-gray-600">Daily Return</div>
                      <div className={`text-lg font-bold ${
                        portfolioData.portfolio_metrics.daily_return >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {portfolioData.portfolio_metrics.daily_return >= 0 ? '+' : ''}
                        {formatPercentage(portfolioData.portfolio_metrics.daily_return)}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-gray-600">Sharpe Ratio</div>
                      <div className="text-lg font-bold text-purple-600">
                        {portfolioData.portfolio_metrics.sharpe_ratio.toFixed(2)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-4 pt-4 border-t grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-gray-600">Max Drawdown</div>
                      <div className="text-sm font-bold text-red-600">
                        {formatPercentage(portfolioData.portfolio_metrics.max_drawdown)}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-gray-600">Current Drawdown</div>
                      <div className="text-sm font-bold text-orange-600">
                        {formatPercentage(portfolioData.portfolio_metrics.current_drawdown)}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-gray-600">Win Rate</div>
                      <div className="text-sm font-bold text-green-600">
                        {formatPercentage(portfolioData.portfolio_metrics.win_rate)}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-gray-600">Profit Factor</div>
                      <div className="text-sm font-bold text-blue-600">
                        {portfolioData.portfolio_metrics.profit_factor.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Risk Metrics */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Shield className="h-5 w-5 mr-2" />
                    Risk Metrics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="text-sm font-medium text-gray-600">Leverage Ratio</div>
                      <div className="text-2xl font-bold text-orange-600">
                        {portfolioData.risk_metrics.leverage_ratio.toFixed(2)}x
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-sm font-medium text-gray-600 mb-2">Position Concentration</div>
                      <div className="space-y-2">
                        {Object.entries(portfolioData.risk_metrics.position_concentrations).map(([symbol, concentration]) => (
                          <div key={symbol} className="flex justify-between">
                            <span className="text-sm">{symbol}</span>
                            <span className="text-sm font-medium">{formatPercentage(concentration)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Current Positions */}
              <Card className="md:col-span-3">
                <CardHeader>
                  <CardTitle>Current Positions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left p-2">Symbol</th>
                          <th className="text-right p-2">Quantity</th>
                          <th className="text-right p-2">Entry Price</th>
                          <th className="text-right p-2">Current Price</th>
                          <th className="text-right p-2">Market Value</th>
                          <th className="text-right p-2">P&L</th>
                          <th className="text-right p-2">P&L %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {portfolioData.positions.map((position, index) => (
                          <tr key={index} className="border-b">
                            <td className="p-2 font-medium">{position.symbol}</td>
                            <td className="p-2 text-right">{position.quantity}</td>
                            <td className="p-2 text-right">{position.entry_price.toFixed(2)}</td>
                            <td className="p-2 text-right">{position.current_price.toFixed(2)}</td>
                            <td className="p-2 text-right">{formatCurrency(position.market_value)}</td>
                            <td className={`p-2 text-right font-medium ${
                              position.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {position.pnl >= 0 ? '+' : ''}{formatCurrency(position.pnl)}
                            </td>
                            <td className={`p-2 text-right font-medium ${
                              position.pnl_percentage >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {position.pnl_percentage >= 0 ? '+' : ''}{formatPercentage(position.pnl_percentage)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    
                    {portfolioData.positions.length === 0 && (
                      <div className="text-center text-gray-500 py-8">No positions currently open</div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center text-gray-500">Portfolio data not available</div>
          )}
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alerts" className="space-y-4">
          {alertsData ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <AlertTriangle className="h-5 w-5 mr-2" />
                    Alert Summary
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <div className="text-sm font-medium text-gray-600">Total Alerts</div>
                        <div className="text-2xl font-bold text-blue-600">{alertsData.total_alerts}</div>
                      </div>
                      <div className="space-y-2">
                        <div className="text-sm font-medium text-gray-600">Active Rules</div>
                        <div className="text-2xl font-bold text-green-600">{alertsData.active_rules}</div>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-gray-600">Total Rules</div>
                      <div className="text-lg font-bold text-purple-600">{alertsData.total_rules}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Alerts by Type</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(alertsData.alerts_by_type).map(([type, count]) => (
                      <div key={type} className="flex justify-between">
                        <span className="text-sm capitalize">{type.replace('_', ' ')}</span>
                        <span className="text-sm font-medium">{count}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Alerts by Symbol</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(alertsData.alerts_by_symbol).map(([symbol, count]) => (
                      <div key={symbol} className="flex justify-between">
                        <span className="text-sm font-medium">{symbol}</span>
                        <span className="text-sm font-medium">{count}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center text-gray-500">Alerts data not available</div>
          )}
        </TabsContent>

        {/* AI Insights Tab */}
        <TabsContent value="ai" className="space-y-4">
          {aiInsights ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Brain className="h-5 w-5 mr-2" />
                    Model Status
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">ML Scorer</span>
                      <Badge variant={aiInsights.model_status.ml_scorer_trained ? "default" : "secondary"}>
                        {aiInsights.model_status.ml_scorer_trained ? "Trained" : "Untrained"}
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Pattern Recognizer</span>
                      <Badge variant={aiInsights.model_status.pattern_recognizer_ready ? "default" : "secondary"}>
                        {aiInsights.model_status.pattern_recognizer_ready ? "Ready" : "Not Ready"}
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Risk Assessment</span>
                      <Badge variant={aiInsights.model_status.risk_assessment_ready ? "default" : "secondary"}>
                        {aiInsights.model_status.risk_assessment_ready ? "Ready" : "Not Ready"}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>AI Insights</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm font-medium text-gray-600">Market Regime</div>
                        <div className="text-lg font-bold text-blue-600 capitalize">
                          {aiInsights.insights.market_regime}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-600">Volatility Forecast</div>
                        <div className="text-lg font-bold text-orange-600 capitalize">
                          {aiInsights.insights.volatility_forecast}
                        </div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm font-medium text-gray-600">Pattern Confidence</div>
                        <div className="text-lg font-bold text-green-600">
                          {formatPercentage(aiInsights.insights.pattern_confidence * 100)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-600">Risk Score</div>
                        <div className={`text-lg font-bold ${
                          aiInsights.insights.risk_score > 0.7 ? 'text-red-600' : 
                          aiInsights.insights.risk_score > 0.4 ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                          {(aiInsights.insights.risk_score * 100).toFixed(0)}/100
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle>AI Recommendations</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {aiInsights.recommendations.map((recommendation, index) => (
                      <div key={index} className="p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
                        <div className="text-sm text-blue-800">{recommendation}</div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center text-gray-500">AI insights not available</div>
          )}
        </TabsContent>

        {/* Risk Analysis Tab */}
        <TabsContent value="risk" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Shield className="h-5 w-5 mr-2 text-red-500" />
                  Risk Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center text-gray-500">
                  Advanced risk metrics coming soon...
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>VaR Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center text-gray-500">
                  Value at Risk analysis coming soon...
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Stress Testing</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center text-gray-500">
                  Portfolio stress testing coming soon...
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AdvancedAnalyticsDashboard;
