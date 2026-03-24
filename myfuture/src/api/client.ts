const BASE = '/api';

export async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { credentials: "include" });
  if (res.status === 401) { window.location.reload(); throw new Error("Session expired"); }
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

// Types
export interface PortfolioSummary {
  watchlist: string;
  portfolio_value: number;
  cash: number;
  initial_value: number;
  cumulative_return: number;
  daily_return: number;
  benchmark_cumulative: number;
  positions_count: number;
  last_updated: string | null;
  mode: string;
  sharpe_ratio: number | null;
  max_drawdown: number;
  win_rate: number;
}

export interface Position {
  ticker: string;
  shares: number;
  entry_price: number;
  entry_date: string;
  weight: number;
  is_active: number;
}

export interface Trade {
  date: string;
  ticker: string;
  action: string;
  shares: number;
  price: number;
  value: number;
  cost: number;
}

export interface Snapshot {
  date: string;
  portfolio_value: number;
  cash: number;
  daily_return: number;
  cumulative_return: number;
  benchmark_return: number;
  benchmark_cumulative: number;
}

export interface Signal {
  date: string;
  ticker: string;
  prediction: number;
  rank: number;
  percentile: number;
  action: string;
}

export interface Prediction {
  id: number;
  prediction_date: string;
  maturity_date: string;
  ticker: string;
  watchlist: string;
  horizon_days: number;
  predicted_score: number;
  predicted_rank: number;
  predicted_action: string;
  entry_price: number;
  actual_price: number | null;
  actual_return: number | null;
  hit: number | null;
  evaluated_at: string | null;
}

export interface MobyPick {
  date: string;
  company: string;
  ticker: string;
  current_price: number;
  price_target: number;
  upside_pct: number;
  rating: string;
  earnings_date: string | null;
  article_title: string | null;
}

export interface MobyPerformance {
  ticker: string;
  company: string;
  entry_date: string;
  entry_price: number;
  price_target: number;
  current_price: number;
  actual_return_pct: number;
  target_return_pct: number;
  progress_pct: number;
  rating: string;
}

export interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// --- Analysis Runs ---
export interface AnalysisRun {
  run_id: string;
  name: string | null;
  watchlist: string;
  status: string;
  created_at: string;
  completed_at: string | null;
}

// --- Real-Time Monitoring ---
export interface MonitoringData {
  alerts: Array<{ level: string; type: string; message: string }>;
  daily_summary: {
    daily_return: number;
    ytd_return: number;
    volatility_30d: number | null;
    sharpe_30d: number | null;
    current_drawdown: number;
    top_positions: Record<string, number>;
    benchmark_return?: number;
    excess_return?: number;
  };
  performance_metrics: {
    total_return: number;
    annualized_return: number;
    volatility: number;
    sharpe_ratio: number | null;
    max_drawdown: number;
    win_rate: number;
    avg_win: number;
  };
}

// --- Earnings Calendar ---
export interface EarningsData {
  exposure: {
    count: number;
    total_exposure: number;
    unique_tickers: number;
    upcoming_earnings: Array<{
      ticker: string;
      earnings_date: string;
      weight: number;
    }>;
    exposure_by_ticker: Record<string, number>;
    exposure_by_period: Record<string, number>;
  };
  impact: {
    earnings_events_analyzed: number;
    aggregate_impact: {
      avg_weighted_return: number;
      win_rate: number;
      total_weighted_return: number;
    };
    by_ticker: Record<string, { count: number; avg_return: number; win_rate: number }>;
  };
}

// --- Watchlist Comparison ---
export interface RegressionSummary {
  watchlist: string;
  baseline_sharpe: number;
  peak_sharpe: number;
  final_sharpe: number;
  final_ic: number;
  best_feature: string;
  best_delta: number;
  duration_min: number;
}

export interface EnsembleData {
  ml_metrics: {
    sharpe: number;
    total_return: number;
    max_drawdown: number;
    win_rate: number;
    avg_turnover_per_rebalance: number;
  };
  ensemble_metrics: {
    sharpe: number;
    total_return: number;
    max_drawdown: number;
    win_rate: number;
    avg_turnover_per_rebalance: number;
  };
  verdict: string;
}

export interface StressScenario {
  scenario: string;
  days: number;
  total_return: number;
  max_drawdown: number;
  halted: boolean;
  liquidated: boolean;
  halted_day: number | null;
  liquidated_day: number | null;
  value_at_exit: number;
  value_without_rules: number;
}

export interface CoverageItem {
  watchlist: string;
  total_tickers: number;
  with_config: number;
  coverage_pct: number;
}

// --- Alert Management ---
export interface AlertConfig {
  id: number;
  alert_type: string;
  run_id: string | null;
  threshold: number | null;
  channels: string[];
  min_interval_hours: number;
  enabled: boolean;
  last_sent_at: string | null;
}

export interface AlertHistoryItem {
  id: number;
  alert_type: string;
  level: string;
  message: string;
  sent_at: string | null;
  channels_sent: string[];
  delivered: boolean;
}

// --- Notifications ---
export interface Notification {
  id: number;
  type: string;
  category: string;
  message: string;
  timestamp: string | null;
  read: boolean;
}

// --- Signal Tracker ---
export interface LiveWatchlist {
  positions: Array<{
    ticker: string;
    shares: number;
    entry_price: number;
    entry_date: string;
    weight: number;
  }>;
  positions_count: number;
  signals: Array<{
    date: string;
    ticker: string;
    action: string;
    prediction: number;
    rank: number;
    percentile: number;
  }>;
  signals_count: number;
  snapshot: {
    date: string;
    portfolio_value: number;
    cash: number;
    daily_return: number;
    cumulative_return: number;
    benchmark_return: number;
    benchmark_cumulative: number;
  } | null;
  recent_trades: Array<{
    date: string;
    ticker: string;
    action: string;
    shares: number;
    price: number;
    value: number;
  }>;
  buy_signals: number;
  sell_signals: number;
}

export interface LiveDashboard {
  watchlists: Record<string, LiveWatchlist>;
  trigger_summary: { buy: number; sell: number; hold: number };
}

// --- Sentiment ---
export interface SentimentTicker {
  ticker: string;
  composite: number | null;
  signal_breadth?: number;
  signal_conviction?: number;
  news?: { avg: number; count: number; positive: number; negative: number; neutral: number };
  analyst?: { strong_buy: number; buy: number; hold: number; sell: number; strong_sell: number; score: number };
  eodhd?: { score: number; article_count: number };
}

export interface MarketRegime {
  regime: string;
  confidence_multiplier: number;
  vix: number | null;
  spy_5d_return: number | null;
}

export interface BlogTicker {
  date: string;
  ticker: string;
  composite_score: number;
  confidence: string;
  headline_count: number;
  buzz_ratio: number;
  regime: string;
  category: string;
  source_count: number;
  options_pcr: number | null;
  options_iv_pct: number | null;
  forward_event: string | null;
  signal_breadth: number;
  signal_conviction: number;
  signal_label: string;
}

export interface TriggerEvaluation {
  ticker: string;
  signal: string;
  composite_score: number | null;
  conviction: number | null;
  breadth: number | null;
  regime: string;
  regime_multiplier: number;
  insider_cluster: boolean;
  reasons: string[];
}

export interface NewsArticle {
  date: string;
  ticker: string;
  headline: string;
  source: string;
  category: string;
  sentiment: number | null;
  url: string;
}

export interface AnalystRec {
  ticker: string;
  date: string;
  strong_buy: number;
  buy: number;
  hold: number;
  sell: number;
  strong_sell: number;
  total: number;
  score: number;
}

export interface InsiderTxn {
  date: string;
  ticker: string;
  insider: string;
  type: string;
  shares: number;
  price: number;
  value: number;
}

export interface EarningsSurprise {
  date: string;
  ticker: string;
  actual_eps: number;
  estimate_eps: number;
  surprise_pct: number;
  beat: boolean | null;
  quarter: number | null;
  year: number | null;
}

// --- Sentiment Trend ---
export interface SentimentTrendPoint {
  date: string;
  score: number;
}

export interface SentimentTrendMulti {
  tickers: Record<string, SentimentTrendPoint[]>;
  available_tickers: string[];
}

// --- Watchlists ---
export interface WatchlistSummary {
  id: string;
  name: string;
  description: string;
  category: string;
  ticker_count: number;
  has_prices: number;
  is_active_portfolio: boolean;
}

export interface WatchlistTicker {
  ticker: string;
  price?: number;
  date?: string;
  daily_return?: number;
  return_30d?: number;
  return_90d?: number;
  volume?: number;
}

export interface WatchlistDetail {
  id: string;
  name: string;
  description: string;
  category: string;
  tickers: WatchlistTicker[];
  count: number;
}

export interface TriggerSignal {
  watchlist: string;
  date: string;
  ticker: string;
  action: string;
  score: number;
  rank: number;
  percentile: number | null;
  forward_confirms: boolean;
  forward_maturity: string | null;
  forward_score: number | null;
}
