const BASE = '/api';

export async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { credentials: 'include' });
  if (res.status === 401) {
    // Session expired — force reload to show login
    window.location.reload();
    throw new Error('Session expired');
  }
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
