import { useCallback, useState, useMemo, useEffect } from 'react';
import { apiFetch } from '../api/client';
import { usePolling } from '../hooks/usePolling';
import TickerLink from '../components/TickerLink';
import Sparkline from '../components/Sparkline';
import EquityCurve from '../components/EquityCurve';
import { Skeleton, SkeletonStat, SkeletonCard } from '../components/Skeleton';
import { ChevronUp, ChevronDown, RefreshCw } from 'lucide-react';
import ErrorCard from '../components/ErrorCard';
import type { PriceBar, Snapshot } from '../api/client';

interface OverviewPosition {
  ticker: string;
  shares: number;
  entry_price: number;
  current_price: number;
  entry_date: string;
  cost_basis: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pct: number;
  weight_pct: number;
}

interface OverviewPortfolio {
  watchlist: string;
  cash: number;
  invested: number;
  portfolio_value: number;
  initial_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_return_pct: number;
  positions_count: number;
  positions: OverviewPosition[];
  sharpe_ratio?: number | null;
  max_drawdown?: number;
  win_rate?: number;
}

interface OverviewGrandTotal {
  cash: number;
  invested: number;
  portfolio_value: number;
  initial_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_return_pct: number;
}

interface OverviewResponse {
  grand_total: OverviewGrandTotal;
  portfolios: OverviewPortfolio[];
}

type SortKey = 'portfolio_value' | 'total_return_pct' | 'realized_pnl' | 'unrealized_pnl';
type SortDir = 'asc' | 'desc';

function fmt(n: number): string {
  return n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtPct(n: number): string {
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%';
}

function pnlColor(n: number): string {
  if (n > 0) return 'text-gain';
  if (n < 0) return 'text-loss';
  return 'text-muted';
}

const SORTABLE_COLS: { key: SortKey; label: string; align: string }[] = [
  { key: 'portfolio_value', label: 'Value', align: 'text-right' },
  { key: 'total_return_pct', label: 'Return', align: 'text-right' },
  { key: 'realized_pnl', label: 'Realized', align: 'text-right' },
  { key: 'unrealized_pnl', label: 'Unrealized', align: 'text-right' },
];

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <ChevronDown size={12} className="opacity-0 group-hover:opacity-40 ml-0.5 inline" />;
  return dir === 'desc'
    ? <ChevronDown size={12} className="text-accent ml-0.5 inline" />
    : <ChevronUp size={12} className="text-accent ml-0.5 inline" />;
}

export default function PortfolioOverview() {
  const [sortKey, setSortKey] = useState<SortKey>('total_return_pct');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const fetchOverview = useCallback(
    () => apiFetch<OverviewResponse>('/portfolios/overview'),
    [],
  );
  const { data, loading, error, lastUpdated } = usePolling(fetchOverview);

  // Fetch real sparkline data for position tickers
  const [sparkData, setSparkData] = useState<Record<string, number[]>>({});
  const [snapshotData, setSnapshotData] = useState<Record<string, { date: string; value: number }[]>>({});
  const [benchmarkSnapshots, setBenchmarkSnapshots] = useState<Record<string, { date: string; benchmark_cumulative: number }[]>>({});

  useEffect(() => {
    if (!data) return;
    // Collect unique tickers across all portfolios
    const tickers = new Set<string>();
    data.portfolios.forEach((p) => p.positions.forEach((pos) => tickers.add(pos.ticker)));

    // Fetch recent prices for each ticker (last 30 bars)
    const abortController = new AbortController();
    Promise.allSettled(
      [...tickers].map((ticker) =>
        apiFetch<PriceBar[]>(`/prices/${ticker}?limit=30`).then((bars) => ({
          ticker,
          closes: bars.map((b) => b.close),
        }))
      )
    ).then((results) => {
      if (abortController.signal.aborted) return;
      const map: Record<string, number[]> = {};
      for (const r of results) {
        if (r.status === 'fulfilled') map[r.value.ticker] = r.value.closes;
      }
      setSparkData(map);
    });

    // Fetch snapshot equity history per watchlist (also extract benchmark_cumulative)
    Promise.allSettled(
      data.portfolios.map((p) =>
        apiFetch<Snapshot[]>(`/portfolios/${p.watchlist}/snapshots`).then((snaps) => ({
          watchlist: p.watchlist,
          points: snaps.slice(-30).map((s) => ({ date: s.date, value: s.portfolio_value })),
          benchmarks: snaps.slice(-30).map((s) => ({ date: s.date, benchmark_cumulative: s.benchmark_cumulative })),
        }))
      )
    ).then((results) => {
      if (abortController.signal.aborted) return;
      const map: Record<string, { date: string; value: number }[]> = {};
      const bmMap: Record<string, { date: string; benchmark_cumulative: number }[]> = {};
      for (const r of results) {
        if (r.status === 'fulfilled' && r.value.points.length > 0) {
          map[r.value.watchlist] = r.value.points;
          bmMap[r.value.watchlist] = r.value.benchmarks;
        }
      }
      setSnapshotData(map);
      setBenchmarkSnapshots(bmMap);
    });

    return () => abortController.abort();
  }, [data]);

  // Aggregate equity data for grand total curve
  const grandTotalEquity = useMemo(() => {
    if (Object.keys(snapshotData).length === 0) return undefined;
    // Merge all watchlist snapshots by date
    const dateMap = new Map<string, number>();
    for (const points of Object.values(snapshotData)) {
      for (const p of points) {
        dateMap.set(p.date, (dateMap.get(p.date) ?? 0) + p.value);
      }
    }
    return [...dateMap.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-30)
      .map(([date, value]) => ({ date, value }));
  }, [snapshotData]);

  // Build benchmark overlay data: SPY dollar-equivalent using grand total initial value
  const grandTotalBenchmark = useMemo(() => {
    if (!data || Object.keys(benchmarkSnapshots).length === 0) return undefined;
    const initVal = data.grand_total.initial_value;
    // Average the benchmark_cumulative across watchlists per date (they should all track SPY)
    const dateMap = new Map<string, { sum: number; count: number }>();
    for (const snaps of Object.values(benchmarkSnapshots)) {
      for (const s of snaps) {
        const entry = dateMap.get(s.date) ?? { sum: 0, count: 0 };
        entry.sum += s.benchmark_cumulative;
        entry.count += 1;
        dateMap.set(s.date, entry);
      }
    }
    return [...dateMap.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-30)
      .map(([date, { sum, count }]) => ({
        date,
        value: initVal * (1 + sum / count),
      }));
  }, [data, benchmarkSnapshots]);

  const sortedPortfolios = useMemo(() => {
    if (!data) return [];
    const sorted = [...data.portfolios].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      return sortDir === 'desc' ? bv - av : av - bv;
    });
    return sorted;
  }, [data, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  }

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-3 w-64" />
        </div>
        <div className="bg-surface-light border border-surface-lighter/40 rounded-xl p-5">
          <Skeleton className="h-3 w-24 mb-3" />
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {Array.from({ length: 7 }).map((_, i) => (
              <SkeletonStat key={i} />
            ))}
          </div>
        </div>
        <SkeletonCard rows={3} cols={6} />
        <SkeletonCard rows={5} cols={10} />
      </div>
    );
  }

  if (error) {
    return <ErrorCard message={error} onRetry={() => window.location.reload()} />;
  }

  if (!data) return null;

  const { grand_total: gt } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Portfolio Overview</h1>
          <p className="text-xs text-muted mt-0.5 flex items-center gap-1.5">
            <span>All positions with live P&L</span>
            {lastUpdated && <span>· Updated {lastUpdated.toLocaleTimeString()}</span>}
            {loading && data && (
              <RefreshCw size={11} className="text-accent animate-spin" />
            )}
          </p>
        </div>
      </div>

      {/* Grand Total Card */}
      <div className="bg-surface-light border border-surface-lighter/40 rounded-xl p-5 shadow-lg shadow-black/20">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-widest">Grand Total</h2>
          <span className={`text-xl font-black tabular-nums ${pnlColor(gt.total_return_pct)}`}>
            {fmtPct(gt.total_return_pct)}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <Stat label="Portfolio Value" value={`$${fmt(gt.portfolio_value)}`} />
          <Stat label="Cash" value={`$${fmt(gt.cash)}`} />
          <Stat label="Invested" value={`$${fmt(gt.invested)}`} />
          <Stat label="Initial" value={`$${fmt(gt.initial_value)}`} />
          <Stat label="Realized P&L" value={`$${fmt(gt.realized_pnl)}`} color={pnlColor(gt.realized_pnl)} />
          <Stat label="Unrealized P&L" value={`$${fmt(gt.unrealized_pnl)}`} color={pnlColor(gt.unrealized_pnl)} />
        </div>
        {/* 30-day equity curve */}
        <div className="mt-4 -mx-1">
          <EquityCurve initialValue={gt.initial_value} currentValue={gt.portfolio_value} height={120} seed="grand_total" data={grandTotalEquity} benchmarkData={grandTotalBenchmark} />
        </div>
      </div>

      {/* Return Leaderboard */}
      {sortedPortfolios.length > 1 && (() => {
        const ranked = [...data.portfolios].sort((a, b) => b.total_return_pct - a.total_return_pct);
        const bestReturn = Math.max(...ranked.map((p) => Math.abs(p.total_return_pct)), 0.1);
        const RANK_STYLES = [
          'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
          'bg-slate-300/10 text-slate-300 border-slate-400/30',
          'bg-amber-700/15 text-amber-600 border-amber-600/30',
        ];
        return (
          <div className="bg-surface-light border border-surface-lighter/40 rounded-xl p-4 shadow-md shadow-black/10">
            <h2 className="text-xs font-semibold text-muted/60 uppercase tracking-widest mb-3">Return Leaderboard</h2>
            <div className="space-y-2">
              {ranked.map((p, i) => {
                const barWidth = bestReturn > 0 ? Math.abs(p.total_return_pct) / bestReturn * 100 : 0;
                const isGain = p.total_return_pct >= 0;
                return (
                  <div key={p.watchlist} className="flex items-center gap-3">
                    <span className={`w-7 h-7 rounded-lg border flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                      i < 3 ? RANK_STYLES[i] : 'bg-surface-lighter/20 text-muted border-surface-lighter/30'
                    }`}>
                      {i + 1}
                    </span>
                    <span className="text-sm text-white font-medium w-28 truncate capitalize">{p.watchlist.replace(/_/g, ' ')}</span>
                    <div className="flex-1 h-5 bg-surface/50 rounded-full overflow-hidden relative">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${isGain ? 'bg-gain/40' : 'bg-loss/40'}`}
                        style={{ width: `${Math.min(barWidth, 100)}%` }}
                      />
                    </div>
                    <span className={`text-sm font-bold tabular-nums w-16 text-right flex-shrink-0 ${pnlColor(p.total_return_pct)}`}>
                      {fmtPct(p.total_return_pct)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      {/* Portfolio Summary Table — sortable */}
      <div className="bg-surface-light border border-surface-lighter/40 rounded-xl overflow-hidden overflow-x-auto shadow-md shadow-black/10">
        <table className="w-full text-sm min-w-[640px]">
          <thead>
            <tr className="border-b border-surface-lighter/40 text-muted/60 text-xs uppercase tracking-wider">
              <th className="text-left px-4 py-3 font-semibold">Portfolio</th>
              <th className="text-right px-4 py-3 font-semibold">Cash</th>
              <th className="text-right px-4 py-3 font-semibold">Invested</th>
              {SORTABLE_COLS.map((col) => (
                <th
                  key={col.key}
                  className={`${col.align} px-4 py-3 font-semibold cursor-pointer select-none group hover:text-muted transition-smooth`}
                  onClick={() => toggleSort(col.key)}
                >
                  {col.label}
                  <SortIcon active={sortKey === col.key} dir={sortDir} />
                </th>
              ))}
              <th className="text-right px-4 py-3 font-semibold">Pos</th>
            </tr>
          </thead>
          <tbody>
            {sortedPortfolios.map((p) => (
              <tr key={p.watchlist} className="border-b border-surface-lighter/20 hover:bg-surface-hover/30 transition-smooth">
                <td className="px-4 py-2.5 font-medium text-white">{p.watchlist.replace(/_/g, ' ')}</td>
                <td className="px-4 py-2.5 text-right text-muted tabular-nums">${fmt(p.cash)}</td>
                <td className="px-4 py-2.5 text-right text-muted tabular-nums">${fmt(p.invested)}</td>
                <td className="px-4 py-2.5 text-right text-white tabular-nums">${fmt(p.portfolio_value)}</td>
                <td className={`px-4 py-2.5 text-right font-medium tabular-nums ${pnlColor(p.total_return_pct)}`}>
                  {fmtPct(p.total_return_pct)}
                </td>
                <td className={`px-4 py-2.5 text-right tabular-nums ${pnlColor(p.realized_pnl)}`}>${fmt(p.realized_pnl)}</td>
                <td className={`px-4 py-2.5 text-right tabular-nums ${pnlColor(p.unrealized_pnl)}`}>${fmt(p.unrealized_pnl)}</td>
                <td className="px-4 py-2.5 text-right text-muted">{p.positions_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Per-portfolio position details — with mini equity curve in header */}
      {sortedPortfolios.filter((p) => p.positions.length > 0).map((p) => (
        <div key={p.watchlist} className="bg-surface-light border border-surface-lighter/40 rounded-xl overflow-hidden overflow-x-auto shadow-md shadow-black/10">
          <div className="px-4 py-3 border-b border-surface-lighter/40 flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-white capitalize">{p.watchlist.replace(/_/g, ' ')}</h3>
              <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                <span className="text-[11px] text-muted">
                  PV: ${fmt(p.portfolio_value)} · Cash: ${fmt(p.cash)}
                </span>
                {p.sharpe_ratio != null && (
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium tabular-nums ${
                    p.sharpe_ratio >= 1 ? 'bg-gain/15 text-gain' : p.sharpe_ratio >= 0 ? 'bg-yellow-500/15 text-yellow-400' : 'bg-loss/15 text-loss'
                  }`}>
                    SR {p.sharpe_ratio.toFixed(2)}
                  </span>
                )}
                {p.max_drawdown != null && (
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium tabular-nums ${
                    Math.abs(p.max_drawdown) <= 10 ? 'bg-gain/15 text-gain' : Math.abs(p.max_drawdown) <= 20 ? 'bg-yellow-500/15 text-yellow-400' : 'bg-loss/15 text-loss'
                  }`}>
                    DD {p.max_drawdown.toFixed(1)}%
                  </span>
                )}
                {p.win_rate != null && (
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium tabular-nums ${
                    p.win_rate >= 55 ? 'bg-gain/15 text-gain' : p.win_rate >= 45 ? 'bg-yellow-500/15 text-yellow-400' : 'bg-loss/15 text-loss'
                  }`}>
                    WR {p.win_rate.toFixed(0)}%
                  </span>
                )}
              </div>
            </div>
            {/* Mini equity curve */}
            <div className="w-28 flex-shrink-0">
              <EquityCurve
                initialValue={p.initial_value}
                currentValue={p.portfolio_value}
                height={48}
                hideTooltip
                seed={p.watchlist}
                data={snapshotData[p.watchlist]}
              />
            </div>
            <span className={`text-sm font-bold tabular-nums flex-shrink-0 ${pnlColor(p.total_return_pct)}`}>
              {fmtPct(p.total_return_pct)}
            </span>
          </div>
          <table className="w-full text-xs min-w-[600px]">
            <thead>
              <tr className="border-b border-surface-lighter/30 text-muted/50 uppercase tracking-wider">
                <th className="text-left px-4 py-2 font-semibold">Ticker</th>
                <th className="text-center px-2 py-2 font-semibold">Trend</th>
                <th className="text-right px-4 py-2 font-semibold">Shares</th>
                <th className="text-right px-4 py-2 font-semibold">Entry</th>
                <th className="text-right px-4 py-2 font-semibold">Current</th>
                <th className="text-right px-4 py-2 font-semibold hidden md:table-cell">Cost</th>
                <th className="text-right px-4 py-2 font-semibold">Value</th>
                <th className="text-right px-4 py-2 font-semibold">P&L</th>
                <th className="text-right px-4 py-2 font-semibold">%</th>
                <th className="text-right px-4 py-2 font-semibold">Wt</th>
              </tr>
            </thead>
            <tbody>
              {p.positions.map((pos) => (
                <tr key={pos.ticker} className="border-b border-surface-lighter/10 hover:bg-surface-hover/20 transition-smooth">
                  <td className="px-4 py-2 font-medium text-white">
                    <TickerLink ticker={pos.ticker} />
                  </td>
                  <td className="px-2 py-1 text-center">
                    <Sparkline
                      entryPrice={pos.entry_price}
                      currentPrice={pos.current_price}
                      seed={pos.ticker}
                      width={80}
                      height={32}
                      data={sparkData[pos.ticker]}
                    />
                  </td>
                  <td className="px-4 py-2 text-right text-muted tabular-nums">{pos.shares.toFixed(1)}</td>
                  <td className="px-4 py-2 text-right text-muted tabular-nums">{pos.entry_price.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right text-white tabular-nums">{pos.current_price.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right text-muted tabular-nums hidden md:table-cell">${fmt(pos.cost_basis)}</td>
                  <td className="px-4 py-2 text-right text-white tabular-nums">${fmt(pos.market_value)}</td>
                  <td className={`px-4 py-2 text-right font-medium tabular-nums ${pnlColor(pos.unrealized_pnl)}`}>
                    ${fmt(pos.unrealized_pnl)}
                  </td>
                  <td className={`px-4 py-2 text-right tabular-nums ${pnlColor(pos.unrealized_pct)}`}>
                    {fmtPct(pos.unrealized_pct)}
                  </td>
                  <td className="px-4 py-2 text-right text-muted tabular-nums">{pos.weight_pct.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function Stat({ label, value, color, large }: { label: string; value: string; color?: string; large?: boolean }) {
  return (
    <div>
      <p className="text-[10px] text-muted/60 uppercase tracking-wider">{label}</p>
      <p className={`${large ? 'text-lg' : 'text-sm'} font-bold tabular-nums ${color || 'text-white'} mt-0.5`}>
        {value}
      </p>
    </div>
  );
}
