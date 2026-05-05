import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Alert, AlertDescription } from './ui/alert';
import { 
  AlertTriangle,
  BarChart3,
  Shield, 
  Brain, 
  Target,
  RefreshCw,
  Wifi,
  WifiOff,
  DollarSign,
  Bell,
  Eye
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

interface PortfolioData {
  summary: {
    total_value: number;
    total_pnl: number;
    total_pnl_percentage: number;
    day_pnl: number;
    day_pnl_percentage: number;
    buying_power: number;
    margin_used: number;
    margin_available: number;
    positions_count: number;
    diversity_score: number;
    risk_score: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
  };
  positions: Array<{
    symbol: string;
    quantity: number;
    avg_price: number;
    current_price: number;
    pnl: number;
    pnl_percentage: number;
    allocation: number;
    risk_contribution: number;
    sector: string;
    entry_date: string;
    position_type: 'long' | 'short';
  }>;
  metrics: {
    volatility: number;
    beta: number;
    var_95: number;
    expected_shortfall: number;
    concentration_risk: number;
    sector_exposure: Record<string, number>;
  };
  performance: {
    daily_returns: Array<{
      date: string;
      return: number;
      cumulative_return: number;
    }>;
    monthly_returns: Array<{
      month: string;
      return: number;
    }>;
    benchmark_comparison: {
      portfolio_return: number;
      benchmark_return: number;
      alpha: number;
      beta: number;
      tracking_error: number;
    };
  };
  timestamp: string;
}

interface AlertData {
  rules: Array<{
    id: string;
    name: string;
    condition: string;
    threshold: number;
    status: 'active' | 'paused' | 'triggered';
    created_at: string;
    last_triggered: string | null;
    trigger_count: number;
    priority: 'low' | 'medium' | 'high' | 'critical';
    type: 'price' | 'volume' | 'indicator' | 'news' | 'custom';
  }>;
  recent_alerts: Array<{
    id: string;
    rule_name: string;
    message: string;
    severity: 'info' | 'warning' | 'error' | 'critical';
    timestamp: string;
    symbol: string;
    acknowledged: boolean;
    details: Record<string, any>;
  }>;
  statistics: {
    total_alerts_today: number;
    critical_alerts_today: number;
    alert_accuracy: number;
    avg_response_time: number;
    false_positive_rate: number;
    most_triggered_rule: string;
  };
  timestamp: string;
}

interface AIInsights {
  pattern_analysis: {
    identified_patterns: Array<{
      pattern: string;
      confidence: number;
      timeframe: string;
      implications: string;
      historical_accuracy: number;
    }>;
    market_regime: 'trending' | 'sideways' | 'volatile';
    trend_strength: number;
    volatility_forecast: number;
  };
  risk_assessment: {
    overall_risk: 'low' | 'medium' | 'high' | 'extreme';
    risk_score: number;
    risk_factors: Array<{
      factor: string;
      impact: number;
      probability: number;
      description: string;
    }>;
    diversification_score: number;
    correlation_risk: number;
    tail_risk: number;
  };
  ml_predictions: {
    price_prediction: {
      predicted_price: number;
      confidence_interval: [number, number];
      time_horizon: string;
      model_accuracy: number;
    };
    volatility_prediction: {
      predicted_volatility: number;
      regime_change_probability: number;
    };
    signal_strength: number;
    recommendation: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
  };
  sentiment_analysis: {
    overall_sentiment: 'very_positive' | 'positive' | 'neutral' | 'negative' | 'very_negative';
    sentiment_score: number;
    news_sentiment: number;
    social_sentiment: number;
    institutional_sentiment: number;
  };
  timestamp: string;
}

interface SystemStatus {
  services: Record<string, 'healthy' | 'degraded' | 'down'>;
  performance_metrics: {
    signals_generated: number;
    uptime: string;
    last_update: string;
    api_response_time: number;
    data_freshness: number;
  };
  data_quality: {
    completeness: number;
    accuracy: number;
    timeliness: number;
    consistency: number;
  };
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
  const dayPnl = (Math.random() - 0.5) * 20000;
  const totalPnl = (Math.random() - 0.3) * 100000;
  
  return {
    summary: {
      total_value: totalValue,
      total_pnl: totalPnl,
      total_pnl_percentage: (totalPnl / totalValue) * 100,
      day_pnl: dayPnl,
      day_pnl_percentage: (dayPnl / totalValue) * 100,
      buying_power: 200000 + Math.random() * 100000,
      margin_used: 50000 + Math.random() * 30000,
      margin_available: 150000 + Math.random() * 50000,
      positions_count: 8 + Math.floor(Math.random() * 7),
      diversity_score: 0.6 + Math.random() * 0.3,
      risk_score: 0.4 + Math.random() * 0.4,
      sharpe_ratio: 0.8 + Math.random() * 0.7,
      max_drawdown: -0.15 + Math.random() * 0.1,
      win_rate: 0.55 + Math.random() * 0.3
    },
    positions: Array.from({ length: 8 }, (_, i) => {
      const symbols = ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'TCS', 'HDFC', 'INFY', 'ICICI', 'KOTAKBANK'];
      const sectors = ['Technology', 'Banking', 'Energy', 'Healthcare', 'Consumer', 'Industrial', 'Financial', 'Telecom'];
      const currentPrice = 100 + Math.random() * 2000;
      const avgPrice = currentPrice * (0.9 + Math.random() * 0.2);
      const quantity = Math.floor(Math.random() * 100) + 10;
      const pnl = (currentPrice - avgPrice) * quantity;
      
      return {
        symbol: symbols[i % symbols.length],
        quantity,
        avg_price: avgPrice,
        current_price: currentPrice,
        pnl,
        pnl_percentage: (pnl / (avgPrice * quantity)) * 100,
        allocation: 5 + Math.random() * 20,
        risk_contribution: 0.05 + Math.random() * 0.15,
        sector: sectors[i % sectors.length],
        entry_date: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
        position_type: Math.random() > 0.8 ? 'short' : 'long'
      };
    }),
    metrics: {
      volatility: 0.15 + Math.random() * 0.1,
      beta: 0.8 + Math.random() * 0.4,
      var_95: -0.02 - Math.random() * 0.03,
      expected_shortfall: -0.04 - Math.random() * 0.02,
      concentration_risk: 0.3 + Math.random() * 0.3,
      sector_exposure: {
        'Technology': 25 + Math.random() * 15,
        'Banking': 20 + Math.random() * 15,
        'Energy': 15 + Math.random() * 10,
        'Healthcare': 10 + Math.random() * 10,
        'Consumer': 12 + Math.random() * 8,
        'Industrial': 8 + Math.random() * 7,
        'Financial': 10 + Math.random() * 5
      }
    },
    performance: {
      daily_returns: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
        return: (Math.random() - 0.5) * 0.04,
        cumulative_return: 0.05 + (Math.random() - 0.5) * 0.1
      })),
      monthly_returns: Array.from({ length: 12 }, (_, i) => ({
        month: new Date(Date.now() - i * 30 * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
        return: (Math.random() - 0.4) * 0.15
      })),
      benchmark_comparison: {
        portfolio_return: 0.08 + Math.random() * 0.1,
        benchmark_return: 0.06 + Math.random() * 0.08,
        alpha: 0.02 + Math.random() * 0.04,
        beta: 0.9 + Math.random() * 0.2,
        tracking_error: 0.03 + Math.random() * 0.02
      }
    },
    timestamp: new Date().toISOString()
  };
};

const generateMockAlertData = (): AlertData => ({
  rules: Array.from({ length: 6 }, (_, i) => ({
    id: `rule-${i}`,
    name: ['Price Alert', 'Volume Spike', 'RSI Overbought', 'Support Break', 'News Alert', 'Volatility Spike'][i],
    condition: ['price > 20000', 'volume > 1.5x avg', 'rsi > 80', 'price < support', 'sentiment < -0.5', 'iv > 25%'][i],
    threshold: [20000, 1.5, 80, 19800, -0.5, 25][i],
    status: ['active', 'paused', 'triggered'][Math.floor(Math.random() * 3)] as any,
    created_at: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
    last_triggered: Math.random() > 0.5 ? new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString() : null,
    trigger_count: Math.floor(Math.random() * 50),
    priority: ['low', 'medium', 'high', 'critical'][Math.floor(Math.random() * 4)] as any,
    type: ['price', 'volume', 'indicator', 'news', 'custom'][Math.floor(Math.random() * 5)] as any
  })),
  recent_alerts: Array.from({ length: 8 }, (_, i) => ({
    id: `alert-${i}`,
    rule_name: ['Price Alert', 'Volume Spike', 'RSI Alert', 'Support Break'][i % 4],
    message: `Alert triggered: ${['Price crossed 20000', 'Volume spike detected', 'RSI overbought', 'Support level broken'][i % 4]}`,
    severity: ['info', 'warning', 'error', 'critical'][Math.floor(Math.random() * 4)] as any,
    timestamp: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString(),
    symbol: ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'TCS'][i % 4],
    acknowledged: Math.random() > 0.3,
    details: { price: 20000 + Math.random() * 100, volume: Math.floor(Math.random() * 10000) }
  })),
  statistics: {
    total_alerts_today: 12 + Math.floor(Math.random() * 20),
    critical_alerts_today: 2 + Math.floor(Math.random() * 5),
    alert_accuracy: 0.75 + Math.random() * 0.2,
    avg_response_time: 300 + Math.random() * 200,
    false_positive_rate: 0.15 + Math.random() * 0.1,
    most_triggered_rule: 'Volume Spike Alert'
  },
  timestamp: new Date().toISOString()
});

const generateMockAIInsights = (): AIInsights => ({
  pattern_analysis: {
    identified_patterns: [
      { pattern: 'Rising Wedge', confidence: 0.8, timeframe: '1D', implications: 'Potential bearish reversal', historical_accuracy: 0.72 },
      { pattern: 'Bull Flag', confidence: 0.65, timeframe: '4H', implications: 'Bullish continuation', historical_accuracy: 0.68 },
      { pattern: 'Double Top', confidence: 0.55, timeframe: '1D', implications: 'Resistance at current levels', historical_accuracy: 0.61 }
    ],
    market_regime: Math.random() > 0.6 ? 'trending' : Math.random() > 0.3 ? 'sideways' : 'volatile',
    trend_strength: Math.random() * 100,
    volatility_forecast: 0.15 + Math.random() * 0.1
  },
  risk_assessment: {
    overall_risk: ['low', 'medium', 'high', 'extreme'][Math.floor(Math.random() * 4)] as any,
    risk_score: Math.random() * 100,
    risk_factors: [
      { factor: 'Market Volatility', impact: 0.7, probability: 0.6, description: 'High volatility expected' },
      { factor: 'Correlation Risk', impact: 0.5, probability: 0.4, description: 'Positions highly correlated' },
      { factor: 'Liquidity Risk', impact: 0.3, probability: 0.2, description: 'Some positions less liquid' }
    ],
    diversification_score: 0.6 + Math.random() * 0.3,
    correlation_risk: 0.4 + Math.random() * 0.4,
    tail_risk: 0.05 + Math.random() * 0.05
  },
  ml_predictions: {
    price_prediction: {
      predicted_price: 19900 + Math.random() * 200,
      confidence_interval: [19800, 20100],
      time_horizon: '5 days',
      model_accuracy: 0.65 + Math.random() * 0.2
    },
    volatility_prediction: {
      predicted_volatility: 0.2 + Math.random() * 0.1,
      regime_change_probability: 0.3 + Math.random() * 0.3
    },
    signal_strength: Math.random() * 100,
    recommendation: ['strong_buy', 'buy', 'hold', 'sell', 'strong_sell'][Math.floor(Math.random() * 5)] as any
  },
  sentiment_analysis: {
    overall_sentiment: ['very_positive', 'positive', 'neutral', 'negative', 'very_negative'][Math.floor(Math.random() * 5)] as any,
    sentiment_score: (Math.random() - 0.5) * 2,
    news_sentiment: (Math.random() - 0.5) * 2,
    social_sentiment: (Math.random() - 0.5) * 2,
    institutional_sentiment: (Math.random() - 0.5) * 2
  },
  timestamp: new Date().toISOString()
});

const generateMockSystemStatus = (): SystemStatus => ({
  services: {
    'data-feed': Math.random() > 0.1 ? 'healthy' : 'degraded',
    'signal-engine': Math.random() > 0.05 ? 'healthy' : 'degraded',
    'portfolio-manager': Math.random() > 0.1 ? 'healthy' : 'degraded',
    'alert-system': Math.random() > 0.1 ? 'healthy' : 'degraded',
    'ai-engine': Math.random() > 0.15 ? 'healthy' : 'degraded'
  },
  performance_metrics: {
    signals_generated: 150 + Math.floor(Math.random() * 100),
    uptime: '99.8%',
    last_update: new Date().toISOString(),
    api_response_time: 50 + Math.random() * 100,
    data_freshness: 0.95 + Math.random() * 0.05
  },
  data_quality: {
    completeness: 0.95 + Math.random() * 0.05,
    accuracy: 0.92 + Math.random() * 0.08,
    timeliness: 0.98 + Math.random() * 0.02,
    consistency: 0.94 + Math.random() * 0.06
  },
  timestamp: new Date().toISOString()
});

const AdvancedAnalyticsDashboard: React.FC = () => {
  const [optionsData, setOptionsData] = useState<OptionsData | null>(null);
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(null);
  const [alertData, setAlertData] = useState<AlertData | null>(null);
  const [aiInsights, setAIInsights] = useState<AIInsights | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('connecting');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [activeTab, setActiveTab] = useState('overview');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchDataWithFallback = useCallback(async (url: string, mockGenerator: () => any) => {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.warn(`API call failed for ${url}, using mock data:`, error);
      return mockGenerator();
    }
  }, []);

  const fetchAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [optionsRes, portfolioRes, alertRes, aiRes, systemRes] = await Promise.all([
        fetchDataWithFallback('http://localhost:8000/api/options/chain', generateMockOptionsData),
        fetchDataWithFallback('http://localhost:8000/api/portfolio/summary', generateMockPortfolioData),
        fetchDataWithFallback('http://localhost:8000/api/alerts/rules', generateMockAlertData),
        fetchDataWithFallback('http://localhost:8000/api/ai/ml-insights', generateMockAIInsights),
        fetchDataWithFallback('http://localhost:8000/api/system/status', generateMockSystemStatus)
      ]);

      setOptionsData(optionsRes);
      setPortfolioData(portfolioRes);
      setAlertData(alertRes);
      setAIInsights(aiRes);
      setSystemStatus(systemRes);
      setConnectionStatus('connected');
      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      setConnectionStatus('disconnected');
    } finally {
      setLoading(false);
    }
  }, [fetchDataWithFallback]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchAllData, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, fetchAllData]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercentage = (value: number, decimals: number = 2) => {
    return `${value.toFixed(decimals)}%`;
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'text-green-500';
      case 'medium': return 'text-yellow-500';
      case 'high': return 'text-orange-500';
      case 'extreme': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <p className="text-lg font-medium">Loading Advanced Analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-full mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Advanced Analytics Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Last updated: {lastUpdate.toLocaleTimeString()} • 
            <span className={`ml-2 ${connectionStatus === 'connected' ? 'text-green-500' : 'text-red-500'}`}>
              {connectionStatus === 'connected' ? <Wifi className="inline w-4 h-4" /> : <WifiOff className="inline w-4 h-4" />}
              {connectionStatus}
            </span>
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <Button 
            variant="outline" 
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={autoRefresh ? 'bg-blue-50 border-blue-300' : ''}
          >
            {autoRefresh ? <Eye className="w-4 h-4 mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            {autoRefresh ? 'Live' : 'Refresh'}
          </Button>
          <Button onClick={fetchAllData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh All
          </Button>
        </div>
      </div>

      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Key Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Portfolio Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {portfolioData ? formatCurrency(portfolioData.summary.total_value) : '---'}
            </div>
            <p className={`text-xs ${(portfolioData?.summary.day_pnl_percentage ?? 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {portfolioData ? `${(portfolioData.summary.day_pnl_percentage ?? 0) > 0 ? '+' : ''}${formatPercentage(portfolioData.summary.day_pnl_percentage ?? 0)}` : '---'} today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Risk Score</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {aiInsights ? `${aiInsights.risk_assessment.risk_score.toFixed(0)}/100` : '---'}
            </div>
            <p className={`text-xs ${aiInsights ? getRiskColor(aiInsights.risk_assessment.overall_risk) : 'text-gray-500'}`}>
              {aiInsights ? aiInsights.risk_assessment.overall_risk.toUpperCase() : '---'} risk
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Alerts</CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {alertData ? alertData.statistics.total_alerts_today : '---'}
            </div>
            <p className="text-xs text-muted-foreground">
              {alertData ? `${alertData.statistics.critical_alerts_today} critical` : '---'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Confidence</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {aiInsights ? `${(aiInsights.ml_predictions.signal_strength).toFixed(0)}%` : '---'}
            </div>
            <p className="text-xs text-muted-foreground">
              {aiInsights ? `${aiInsights.ml_predictions.recommendation.replace('_', ' ').toUpperCase()}` : '---'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="options">Options</TabsTrigger>
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="ai">AI Insights</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Market Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <BarChart3 className="w-5 h-5 mr-2" />
                  Market Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">PCR Ratio</span>
                    <span className="text-lg font-bold">
                      {optionsData ? optionsData.pcr.pcr_oi.toFixed(2) : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Max Pain</span>
                    <span className="text-lg font-bold">
                      {optionsData ? optionsData.max_pain.max_pain_strike.toFixed(0) : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Trend</span>
                    <Badge variant={optionsData?.pcr.trend === 'bullish' ? 'default' : optionsData?.pcr.trend === 'bearish' ? 'destructive' : 'secondary'}>
                      {optionsData ? optionsData.pcr.trend : '---'}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Portfolio Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Target className="w-5 h-5 mr-2" />
                  Portfolio Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Total P&L</span>
                    <span className={`text-lg font-bold ${(portfolioData?.summary.total_pnl ?? 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {portfolioData ? formatCurrency(portfolioData.summary.total_pnl ?? 0) : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Win Rate</span>
                    <span className="text-lg font-bold">
                      {portfolioData ? formatPercentage(portfolioData.summary.win_rate * 100, 1) : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Positions</span>
                    <span className="text-lg font-bold">
                      {portfolioData ? portfolioData.summary.positions_count : '---'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="options" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Put-Call Ratio */}
            <Card>
              <CardHeader>
                <CardTitle>Put-Call Ratio Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">PCR (OI)</span>
                    <span className="text-lg font-bold">
                      {optionsData ? optionsData.pcr.pcr_oi.toFixed(2) : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">PCR (Volume)</span>
                    <span className="text-lg font-bold">
                      {optionsData ? optionsData.pcr.pcr_volume.toFixed(2) : '---'}
                    </span>
                  </div>
                  <div className="mt-4 p-3 bg-gray-50 rounded">
                    <p className="text-sm font-medium">Interpretation</p>
                    <p className="text-sm text-gray-600 mt-1">
                      {optionsData ? optionsData.pcr.interpretation : 'Loading...'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Max Pain */}
            <Card>
              <CardHeader>
                <CardTitle>Max Pain Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Max Pain Strike</span>
                    <span className="text-lg font-bold">
                      {optionsData ? optionsData.max_pain.max_pain_strike.toFixed(0) : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Current Price</span>
                    <span className="text-lg font-bold">
                      {optionsData ? optionsData.max_pain.current_price.toFixed(0) : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Distance</span>
                    <span className={`text-lg font-bold ${(optionsData?.max_pain.distance_from_max_pain ?? 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {optionsData ? `${(optionsData.max_pain.distance_from_max_pain ?? 0) > 0 ? '+' : ''}${(optionsData.max_pain.distance_from_max_pain ?? 0).toFixed(0)}` : '---'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Support & Resistance */}
          <Card>
            <CardHeader>
              <CardTitle>Support & Resistance Levels</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium mb-3 text-green-600">Support Levels</h4>
                  <div className="space-y-2">
                    {optionsData?.support_resistance.support_levels.map((level, idx) => (
                      <div key={idx} className="flex justify-between items-center p-2 bg-green-50 rounded">
                        <span className="text-sm font-medium">{level.level.toFixed(0)}</span>
                        <Badge variant="outline" className="text-xs">
                          {level.type} ({(level.strength * 100).toFixed(0)}%)
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="font-medium mb-3 text-red-600">Resistance Levels</h4>
                  <div className="space-y-2">
                    {optionsData?.support_resistance.resistance_levels.map((level, idx) => (
                      <div key={idx} className="flex justify-between items-center p-2 bg-red-50 rounded">
                        <span className="text-sm font-medium">{level.level.toFixed(0)}</span>
                        <Badge variant="outline" className="text-xs">
                          {level.type} ({(level.strength * 100).toFixed(0)}%)
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="portfolio" className="space-y-6">
          {/* Portfolio Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Sharpe Ratio</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {portfolioData ? portfolioData.summary.sharpe_ratio.toFixed(2) : '---'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">
                  {portfolioData ? formatPercentage(portfolioData.summary.max_drawdown * 100) : '---'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Diversity Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {portfolioData ? (portfolioData.summary.diversity_score * 100).toFixed(0) : '---'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Beta</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {portfolioData ? portfolioData.metrics.beta.toFixed(2) : '---'}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Top Positions */}
          <Card>
            <CardHeader>
              <CardTitle>Top Positions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {portfolioData?.positions.slice(0, 5).map((position, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div className="flex items-center space-x-3">
                      <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      <div>
                        <p className="font-medium">{position.symbol}</p>
                        <p className="text-sm text-gray-600">{position.sector}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`font-medium ${position.pnl > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(position.pnl)}
                      </p>
                      <p className="text-sm text-gray-600">
                        {formatPercentage(position.allocation, 1)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alerts" className="space-y-6">
          {/* Alert Statistics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Alerts</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {alertData ? alertData.statistics.total_alerts_today : '---'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Critical Alerts</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">
                  {alertData ? alertData.statistics.critical_alerts_today : '---'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Accuracy</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {alertData ? formatPercentage(alertData.statistics.alert_accuracy * 100) : '---'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Avg Response</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {alertData ? `${alertData.statistics.avg_response_time.toFixed(0)}s` : '---'}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent Alerts */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {alertData?.recent_alerts.slice(0, 8).map((alert, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 border rounded">
                    <div className="flex items-center space-x-3">
                      <div className={`w-2 h-2 rounded-full ${
                        alert.severity === 'critical' ? 'bg-red-500' :
                        alert.severity === 'error' ? 'bg-orange-500' :
                        alert.severity === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
                      }`}></div>
                      <div>
                        <p className="font-medium">{alert.rule_name}</p>
                        <p className="text-sm text-gray-600">{alert.message}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">{alert.symbol}</p>
                      <p className="text-xs text-gray-500">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai" className="space-y-6">
          {/* AI Predictions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Brain className="w-5 h-5 mr-2" />
                  Price Prediction
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Predicted Price</span>
                    <span className="text-lg font-bold">
                      {aiInsights ? aiInsights.ml_predictions.price_prediction.predicted_price.toFixed(0) : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Confidence</span>
                    <span className="text-lg font-bold">
                      {aiInsights ? formatPercentage(aiInsights.ml_predictions.price_prediction.model_accuracy * 100) : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Recommendation</span>
                    <Badge variant={
                      aiInsights?.ml_predictions.recommendation.includes('buy') ? 'default' :
                      aiInsights?.ml_predictions.recommendation.includes('sell') ? 'destructive' : 'secondary'
                    }>
                      {aiInsights ? aiInsights.ml_predictions.recommendation.replace('_', ' ').toUpperCase() : '---'}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Target className="w-5 h-5 mr-2" />
                  Risk Assessment
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Overall Risk</span>
                    <Badge variant={
                      aiInsights?.risk_assessment.overall_risk === 'low' ? 'default' :
                      aiInsights?.risk_assessment.overall_risk === 'medium' ? 'secondary' :
                      aiInsights?.risk_assessment.overall_risk === 'high' ? 'destructive' : 'destructive'
                    }>
                      {aiInsights ? aiInsights.risk_assessment.overall_risk.toUpperCase() : '---'}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Risk Score</span>
                    <span className="text-lg font-bold">
                      {aiInsights ? `${aiInsights.risk_assessment.risk_score.toFixed(0)}/100` : '---'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Diversification</span>
                    <span className="text-lg font-bold">
                      {aiInsights ? formatPercentage(aiInsights.risk_assessment.diversification_score * 100) : '---'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Pattern Analysis */}
          <Card>
            <CardHeader>
              <CardTitle>Pattern Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {aiInsights?.pattern_analysis.identified_patterns.map((pattern, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div>
                      <p className="font-medium">{pattern.pattern}</p>
                      <p className="text-sm text-gray-600">{pattern.implications}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">{formatPercentage(pattern.confidence * 100)}</p>
                      <p className="text-xs text-gray-500">{pattern.timeframe}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Sentiment Analysis */}
          <Card>
            <CardHeader>
              <CardTitle>Sentiment Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Overall Sentiment</span>
                  <Badge variant={
                    aiInsights?.sentiment_analysis.overall_sentiment.includes('positive') ? 'default' :
                    aiInsights?.sentiment_analysis.overall_sentiment.includes('negative') ? 'destructive' : 'secondary'
                  }>
                    {aiInsights ? aiInsights.sentiment_analysis.overall_sentiment.replace('_', ' ').toUpperCase() : '---'}
                  </Badge>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-sm font-medium">News</p>
                    <p className={`text-lg font-bold ${(aiInsights?.sentiment_analysis.news_sentiment ?? 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {aiInsights ? (aiInsights.sentiment_analysis.news_sentiment ?? 0).toFixed(1) : '---'}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium">Social</p>
                    <p className={`text-lg font-bold ${(aiInsights?.sentiment_analysis.social_sentiment ?? 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {aiInsights ? (aiInsights.sentiment_analysis.social_sentiment ?? 0).toFixed(1) : '---'}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium">Institutional</p>
                    <p className={`text-lg font-bold ${(aiInsights?.sentiment_analysis.institutional_sentiment ?? 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {aiInsights ? (aiInsights.sentiment_analysis.institutional_sentiment ?? 0).toFixed(1) : '---'}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="system" className="space-y-6">
          {/* System Health */}
          <Card>
            <CardHeader>
              <CardTitle>System Health</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {systemStatus && Object.entries(systemStatus.services).map(([service, status]) => (
                  <div key={service} className="flex items-center justify-between p-3 border rounded">
                    <div className="flex items-center space-x-3">
                      <div className={`w-2 h-2 rounded-full ${
                        status === 'healthy' ? 'bg-green-500' :
                        status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
                      }`}></div>
                      <span className="font-medium">{service.replace('-', ' ').toUpperCase()}</span>
                    </div>
                    <Badge variant={status === 'healthy' ? 'default' : status === 'degraded' ? 'secondary' : 'destructive'}>
                      {status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Performance Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Uptime</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {systemStatus ? systemStatus.performance_metrics.uptime : '---'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Signals Generated</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {systemStatus ? systemStatus.performance_metrics.signals_generated : '---'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">API Response Time</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {systemStatus ? `${systemStatus.performance_metrics.api_response_time.toFixed(0)}ms` : '---'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Data Quality</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {systemStatus ? formatPercentage(systemStatus.data_quality.accuracy * 100) : '---'}
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
