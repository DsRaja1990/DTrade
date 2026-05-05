// User and Authentication Types
export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  preferences?: UserPreferences;
  profile?: UserProfile;
}

export interface UserProfile {
  phone?: string;
  dhan_client_id?: string;
  risk_tolerance: 'low' | 'medium' | 'high';
  trading_experience: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  preferred_segments: string[];
  max_position_size?: number;
  daily_loss_limit?: number;
}

export interface UserPreferences {
  theme: 'dark' | 'light';
  notifications_enabled: boolean;
  sound_enabled: boolean;
  auto_logout_minutes: number;
  default_quantity: number;
  price_alerts_enabled: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  username: string;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Trading Types
export interface Order {
  id: string;
  user_id: string;
  symbol: string;
  exchange: string;
  transaction_type: 'BUY' | 'SELL';
  order_type: 'MARKET' | 'LIMIT' | 'STOP_LOSS' | 'STOP_LOSS_MARKET';
  product_type: 'INTRADAY' | 'CNC' | 'MTF' | 'CO' | 'BO';
  quantity: number;
  price?: number;
  trigger_price?: number;
  validity: 'DAY' | 'IOC';
  status: 'PENDING' | 'OPEN' | 'COMPLETED' | 'CANCELLED' | 'REJECTED';
  order_id?: string;
  avg_price?: number;
  filled_qty?: number;
  created_at: string;
  updated_at: string;
  tags?: string[];
}

export interface Position {
  id: string;
  user_id: string;
  symbol: string;
  exchange: string;
  product_type: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  pnl: number;
  pnl_percentage: number;
  day_pnl: number;
  created_at: string;
  updated_at: string;
}

export interface Portfolio {
  id: string;
  user_id: string;
  total_value: number;
  available_balance: number;
  used_margin: number;
  total_pnl: number;
  day_pnl: number;
  positions: Position[];
  updated_at: string;
}

// Market Data Types
export interface Quote {
  symbol: string;
  exchange: string;
  ltp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  change: number;
  change_percent: number;
  bid_price: number;
  ask_price: number;
  bid_qty: number;
  ask_qty: number;
  timestamp: string;
}

export interface OptionChainData {
  strike_price: number;
  call_option?: OptionQuote;
  put_option?: OptionQuote;
}

export interface OptionQuote {
  symbol: string;
  ltp: number;
  bid_price: number;
  ask_price: number;
  volume: number;
  oi: number;
  oi_change: number;
  iv: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
}

export interface CandleData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Instrument {
  symbol: string;
  exchange: string;
  segment: string;
  instrument_type: string;
  lot_size: number;
  tick_size: number;
  isin?: string;
  expiry_date?: string;
  strike_price?: number;
  option_type?: 'CE' | 'PE';
}

// AI and Strategy Types
export interface AIStrategy {
  id: string;
  user_id: string;
  name: string;
  description: string;
  strategy_type: 'momentum' | 'mean_reversion' | 'breakout' | 'arbitrage' | 'custom';
  is_active: boolean;
  parameters: Record<string, any>;
  performance_metrics: StrategyMetrics;
  created_at: string;
  updated_at: string;
}

export interface StrategyMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  max_drawdown: number;
  sharpe_ratio: number;
  avg_trade_duration: number;
}

export interface TradingSignal {
  id: string;
  strategy_id: string;
  symbol: string;
  signal_type: 'BUY' | 'SELL' | 'HOLD';
  strength: number;
  confidence: number;
  price_target?: number;
  stop_loss?: number;
  reasoning: string;
  created_at: string;
  expires_at?: string;
}

export interface BacktestResult {
  id: string;
  strategy_id: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return: number;
  annual_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  trades: BacktestTrade[];
  equity_curve: { date: string; value: number }[];
  created_at: string;
}

export interface BacktestTrade {
  symbol: string;
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  return_percent: number;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'quote' | 'order_update' | 'position_update' | 'signal' | 'alert';
  data: any;
  timestamp: string;
}

export interface MarketFeedData {
  symbol: string;
  ltp: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp: string;
}

// Analytics Types
export interface PerformanceMetrics {
  total_pnl: number;
  day_pnl: number;
  total_trades: number;
  winning_trades: number;
  win_rate: number;
  avg_trade_size: number;
  largest_win: number;
  largest_loss: number;
  sharpe_ratio: number;
  max_drawdown: number;
  calmar_ratio: number;
  sortino_ratio: number;
}

export interface RiskMetrics {
  var_95: number;
  var_99: number;
  expected_shortfall: number;
  beta: number;
  alpha: number;
  correlation_to_market: number;
  volatility: number;
  downside_deviation: number;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Error Types
export interface ApiError {
  message: string;
  code: string;
  details?: Record<string, any>;
}

// Form Types
export interface OrderForm {
  symbol: string;
  exchange: string;
  transaction_type: 'BUY' | 'SELL';
  order_type: 'MARKET' | 'LIMIT' | 'STOP_LOSS' | 'STOP_LOSS_MARKET';
  product_type: 'INTRADAY' | 'CNC' | 'MTF' | 'CO' | 'BO';
  quantity: number;
  price?: number;
  trigger_price?: number;
  validity: 'DAY' | 'IOC';
  tags?: string[];
}

export interface StrategyForm {
  name: string;
  description: string;
  strategy_type: 'momentum' | 'mean_reversion' | 'breakout' | 'arbitrage' | 'custom';
  parameters: Record<string, any>;
}

// Chart Types
export interface ChartConfig {
  symbol: string;
  timeframe: '1m' | '5m' | '15m' | '1h' | '1d';
  indicators: string[];
  studies: string[];
}

// AI Trade Types
export interface AITradeConfig {
  enabled: boolean;
  max_positions: number;
  max_risk_per_trade: number;
  stop_loss_percent: number;
  take_profit_percent: number;
  allowed_symbols: string[];
  trading_hours: {
    start: string;
    end: string;
  };
}

export interface AITradeStatus {
  is_active: boolean;
  total_trades_today: number;
  current_positions: number;
  pnl_today: number;
  last_signal_time?: string;
  next_check_time?: string;
}
