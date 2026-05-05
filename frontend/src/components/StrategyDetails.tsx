import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Activity, Target } from 'lucide-react';

interface Trade {
  id: string;
  instrument: string;
  direction: 'buy' | 'sell';
  quantity: number;
  price: number;
  timestamp: string;
  order_type: string;
  status: string;
  pnl: number;
  fees: number;
}

interface Position {
  instrument: string;
  quantity: number;
  average_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  timestamp: string;
}

interface StrategyDetailsProps {
  strategyName: string;
  onClose: () => void;
}

const StrategyDetails: React.FC<StrategyDetailsProps> = ({ strategyName, onClose }) => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [performance, setPerformance] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'positions' | 'trades' | 'charts'>('overview');

  useEffect(() => {
    fetchStrategyDetails();
    const interval = setInterval(fetchStrategyDetails, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [strategyName]);

  const fetchStrategyDetails = async () => {
    try {
      const [performanceRes, tradesRes, positionsRes] = await Promise.all([
        fetch(`/api/papertest/strategies/${strategyName}/performance`),
        fetch(`/api/papertest/strategies/${strategyName}/trades?limit=100`),
        fetch(`/api/papertest/strategies/${strategyName}/positions`)
      ]);

      const [performanceData, tradesData, positionsData] = await Promise.all([
        performanceRes.json(),
        tradesRes.json(),
        positionsRes.json()
      ]);

      if (performanceData.success) setPerformance(performanceData.data);
      if (tradesData.success) setTrades(tradesData.data.trades);
      if (positionsData.success) setPositions(positionsData.data.positions);
    } catch (error) {
      console.error('Failed to fetch strategy details:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  // Prepare chart data
  const pnlChartData = trades.map((trade, index) => {
    const cumulativePnl = trades.slice(0, index + 1).reduce((sum, t) => sum + t.pnl, 0);
    return {
      trade: index + 1,
      pnl: cumulativePnl,
      timestamp: new Date(trade.timestamp).toLocaleTimeString()
    };
  });

  const tradeDistribution = [
    { name: 'Winning', value: performance?.metrics.winning_trades || 0, color: '#10B981' },
    { name: 'Losing', value: performance?.metrics.losing_trades || 0, color: '#EF4444' }
  ];

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-gray-800 p-8 rounded-lg">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="text-white mt-4">Loading strategy details...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-white capitalize">
            {strategyName.replace('_', ' ')} Details
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-700">
          <div className="flex space-x-8 px-6">
            {[
              { id: 'overview', label: 'Overview', icon: Activity },
              { id: 'positions', label: 'Positions', icon: Target },
              { id: 'trades', label: 'Trades', icon: DollarSign },
              { id: 'charts', label: 'Charts', icon: TrendingUp }
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as any)}
                className={`py-4 px-2 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Key Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <DollarSign className="h-5 w-5 text-green-400" />
                    <span className="text-sm font-medium text-gray-300">Total P&L</span>
                  </div>
                  <p className={`text-2xl font-bold ${performance?.metrics.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatCurrency(performance?.metrics.total_pnl || 0)}
                  </p>
                </div>

                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <TrendingUp className="h-5 w-5 text-blue-400" />
                    <span className="text-sm font-medium text-gray-300">Win Rate</span>
                  </div>
                  <p className="text-2xl font-bold text-white">
                    {formatPercentage(performance?.metrics.win_rate || 0)}
                  </p>
                </div>

                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <Activity className="h-5 w-5 text-purple-400" />
                    <span className="text-sm font-medium text-gray-300">Total Trades</span>
                  </div>
                  <p className="text-2xl font-bold text-white">
                    {performance?.metrics.total_trades || 0}
                  </p>
                </div>

                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <TrendingDown className="h-5 w-5 text-orange-400" />
                    <span className="text-sm font-medium text-gray-300">Max Drawdown</span>
                  </div>
                  <p className="text-2xl font-bold text-red-400">
                    {formatPercentage(performance?.metrics.max_drawdown || 0)}
                  </p>
                </div>
              </div>

              {/* Ratio Strategy Specific Data */}
              {performance?.ratio_strategy_data && (
                <div className="bg-gray-800 p-6 rounded-lg">
                  <h3 className="text-lg font-semibold text-white mb-4">Strategy Details</h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div>
                      <span className="text-gray-400">Current Capital:</span>
                      <p className="text-white font-medium">
                        {formatCurrency(performance.ratio_strategy_data.current_capital)}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-400">Virtual Capital:</span>
                      <p className="text-white font-medium">
                        {formatCurrency(performance.ratio_strategy_data.virtual_capital)}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-400">Daily P&L:</span>
                      <p className={`font-medium ${performance.ratio_strategy_data.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(performance.ratio_strategy_data.daily_pnl)}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-400">Active Setups:</span>
                      <p className="text-white font-medium">
                        {performance.ratio_strategy_data.active_setups}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-400">Peak Capital:</span>
                      <p className="text-white font-medium">
                        {formatCurrency(performance.ratio_strategy_data.peak_capital)}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-400">Subscribed Instruments:</span>
                      <p className="text-white font-medium">
                        {performance.ratio_strategy_data.subscribed_instruments?.join(', ') || 'None'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'positions' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white">Active Positions</h3>
              {positions.length === 0 ? (
                <div className="text-center py-8">
                  <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-400">No active positions</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-3 px-4 text-gray-300">Instrument</th>
                        <th className="text-right py-3 px-4 text-gray-300">Quantity</th>
                        <th className="text-right py-3 px-4 text-gray-300">Avg Price</th>
                        <th className="text-right py-3 px-4 text-gray-300">Current Price</th>
                        <th className="text-right py-3 px-4 text-gray-300">Unrealized P&L</th>
                        <th className="text-right py-3 px-4 text-gray-300">Realized P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((position, index) => (
                        <tr key={index} className="border-b border-gray-800">
                          <td className="py-3 px-4 text-white font-medium">{position.instrument}</td>
                          <td className="py-3 px-4 text-right text-white">{position.quantity}</td>
                          <td className="py-3 px-4 text-right text-white">{formatCurrency(position.average_price)}</td>
                          <td className="py-3 px-4 text-right text-white">{formatCurrency(position.current_price)}</td>
                          <td className={`py-3 px-4 text-right font-medium ${position.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatCurrency(position.unrealized_pnl)}
                          </td>
                          <td className={`py-3 px-4 text-right font-medium ${position.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatCurrency(position.realized_pnl)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {activeTab === 'trades' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white">Recent Trades</h3>
              {trades.length === 0 ? (
                <div className="text-center py-8">
                  <DollarSign className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-400">No trades executed yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-3 px-4 text-gray-300">Time</th>
                        <th className="text-left py-3 px-4 text-gray-300">Instrument</th>
                        <th className="text-center py-3 px-4 text-gray-300">Direction</th>
                        <th className="text-right py-3 px-4 text-gray-300">Quantity</th>
                        <th className="text-right py-3 px-4 text-gray-300">Price</th>
                        <th className="text-right py-3 px-4 text-gray-300">P&L</th>
                        <th className="text-center py-3 px-4 text-gray-300">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.slice().reverse().map((trade) => (
                        <tr key={trade.id} className="border-b border-gray-800">
                          <td className="py-3 px-4 text-white">
                            {new Date(trade.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="py-3 px-4 text-white font-medium">{trade.instrument}</td>
                          <td className="py-3 px-4 text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              trade.direction === 'buy' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                            }`}>
                              {trade.direction.toUpperCase()}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right text-white">{trade.quantity}</td>
                          <td className="py-3 px-4 text-right text-white">{formatCurrency(trade.price)}</td>
                          <td className={`py-3 px-4 text-right font-medium ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatCurrency(trade.pnl)}
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              trade.status === 'executed' ? 'bg-green-600 text-white' : 'bg-yellow-600 text-white'
                            }`}>
                              {trade.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {activeTab === 'charts' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* P&L Chart */}
                <div className="bg-gray-800 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-white mb-4">Cumulative P&L</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={pnlChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="trade" stroke="#9CA3AF" />
                      <YAxis stroke="#9CA3AF" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                        labelStyle={{ color: '#F3F4F6' }}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="pnl" 
                        stroke="#3B82F6" 
                        fill="#3B82F6" 
                        fillOpacity={0.3}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* Trade Distribution */}
                <div className="bg-gray-800 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-white mb-4">Trade Distribution</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={tradeDistribution}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, value, percent }) => `${name}: ${value} (${(percent * 100).toFixed(0)}%)`}
                      >
                        {tradeDistribution.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Trade P&L Distribution */}
              {trades.length > 0 && (
                <div className="bg-gray-800 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-white mb-4">Trade P&L Distribution</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={trades.map((trade, index) => ({ 
                      trade: index + 1, 
                      pnl: trade.pnl,
                      fill: trade.pnl >= 0 ? '#10B981' : '#EF4444'
                    }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="trade" stroke="#9CA3AF" />
                      <YAxis stroke="#9CA3AF" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                        labelStyle={{ color: '#F3F4F6' }}
                      />
                      <Bar dataKey="pnl" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StrategyDetails;
