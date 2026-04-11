import { useCallback, useState } from 'react';
import { apiFetch } from '../api/client';
import { usePolling } from '../hooks/usePolling';
import TickerLink from '../components/TickerLink';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { CalendarOff } from 'lucide-react';
import { Skeleton, SkeletonCard } from '../components/Skeleton';
import ErrorCard from '../components/ErrorCard';

interface Action {
  ticker: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  shares: number;
  price: number;
  dollar_value: number;
  weight_pct?: number;
  realized_pnl?: number;
}

interface WatchlistActions {
  watchlist: string;
  date: string;
  actions: Action[];
  buy_count: number;
  sell_count: number;
  hold_count: number;
  net_buy_value: number;
  net_sell_value: number;
}

interface DailyActionsResponse {
  watchlists: WatchlistActions[];
}

function fmt(n: number): string {
  return n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

const ACTION_STYLE = {
  BUY:  { bg: 'bg-gain/15', text: 'text-gain', label: 'BUY' },
  SELL: { bg: 'bg-loss/15', text: 'text-loss', label: 'SELL' },
  HOLD: { bg: 'bg-surface-lighter/30', text: 'text-muted', label: 'HOLD' },
};

export default function DailyActions() {
  const [dateFilter, setDateFilter] = useState(() => new Date().toISOString().slice(0, 10));
  const [showHolds, setShowHolds] = useState(false);

  const fetchActions = useCallback(
    () => {
      const q = dateFilter ? `?date=${dateFilter}` : '';
      return apiFetch<DailyActionsResponse>(`/portfolios/daily-actions${q}`);
    },
    [dateFilter],
  );
  const { data, loading, error, lastUpdated } = usePolling(fetchActions, 60000, dateFilter);

  const totalBuys = data?.watchlists.reduce((s, w) => s + w.net_buy_value, 0) ?? 0;
  const totalSells = data?.watchlists.reduce((s, w) => s + w.net_sell_value, 0) ?? 0;
  const totalBuyCount = data?.watchlists.reduce((s, w) => s + w.buy_count, 0) ?? 0;
  const totalSellCount = data?.watchlists.reduce((s, w) => s + w.sell_count, 0) ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Daily Actions</h1>
          <p className="text-xs text-muted mt-0.5">
            New entries and exits only — rebalances excluded
            {lastUpdated && <> · Updated {lastUpdated.toLocaleTimeString()}</>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-muted cursor-pointer min-h-[44px] px-2">
            <input
              type="checkbox"
              checked={showHolds}
              onChange={(e) => setShowHolds(e.target.checked)}
              className="rounded border-surface-lighter w-5 h-5"
            />
            Show holds
          </label>
          <input
            type="date"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="bg-surface border border-surface-lighter/40 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-accent/50 min-h-[44px]"
          />
          {dateFilter && (
            <button
              onClick={() => setDateFilter('')}
              className="text-xs text-muted hover:text-white transition-smooth"
            >
              Latest
            </button>
          )}
        </div>
      </div>

      {loading && !data && (
        <div className="space-y-6">
          <div className="bg-surface-light border border-surface-lighter/40 rounded-xl p-4 flex flex-wrap gap-6">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-2.5 w-20" />
                <Skeleton className="h-6 w-28" />
              </div>
            ))}
          </div>
          <SkeletonCard rows={4} cols={6} />
          <SkeletonCard rows={3} cols={6} />
        </div>
      )}

      {error && <ErrorCard message={error} onRetry={() => window.location.reload()} />}

      {data && data.watchlists.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-14 h-14 rounded-2xl bg-surface-lighter/20 flex items-center justify-center mb-4">
            <CalendarOff size={28} className="text-muted/40" />
          </div>
          <p className="text-sm font-medium text-muted mb-1">No actions today</p>
          <p className="text-xs text-muted/50 max-w-xs">
            There are no new entries or exits for this date. Try selecting a different date or check back after the next rebalance.
          </p>
        </div>
      )}

      {data && data.watchlists.length > 0 && (
        <>
          {/* Summary bar with mini bar chart */}
          <div className="bg-surface-light border border-surface-lighter/40 rounded-xl p-4 flex flex-wrap items-center gap-4 sm:gap-6 shadow-lg shadow-black/20">
            <div>
              <p className="text-[10px] text-muted/60 uppercase tracking-wider">New Buys</p>
              <p className="text-lg font-bold text-gain tabular-nums">{totalBuyCount} · ${fmt(totalBuys)}</p>
            </div>
            <div>
              <p className="text-[10px] text-muted/60 uppercase tracking-wider">Sells / Exits</p>
              <p className="text-lg font-bold text-loss tabular-nums">{totalSellCount} · ${fmt(totalSells)}</p>
            </div>
            <div>
              <p className="text-[10px] text-muted/60 uppercase tracking-wider">Net Flow</p>
              <p className={`text-lg font-bold tabular-nums ${totalBuys - totalSells >= 0 ? 'text-gain' : 'text-loss'}`}>
                ${fmt(totalBuys - totalSells)}
              </p>
            </div>
            {/* Buy vs Sell ratio bar — visible on all screens */}
            {(totalBuys > 0 || totalSells > 0) && (
              <div className="w-full sm:w-auto sm:ml-auto sm:min-w-[220px] mt-2 sm:mt-0">
                {/* Mobile: horizontal ratio bar */}
                <div className="block sm:hidden">
                  <div className="flex items-center gap-2 text-[10px] text-muted/60 uppercase tracking-wider mb-1">
                    <span>Buy vs Sell Flow</span>
                  </div>
                  <div className="flex h-3 rounded-full overflow-hidden bg-surface-lighter/20">
                    {totalBuys > 0 && (
                      <div
                        className="bg-gain/80 transition-all duration-300"
                        style={{ width: `${(totalBuys / (totalBuys + totalSells)) * 100}%` }}
                      />
                    )}
                    {totalSells > 0 && (
                      <div
                        className="bg-loss/80 transition-all duration-300"
                        style={{ width: `${(totalSells / (totalBuys + totalSells)) * 100}%` }}
                      />
                    )}
                  </div>
                  <div className="flex justify-between text-[10px] mt-0.5">
                    <span className="text-gain tabular-nums">${fmt(totalBuys)}</span>
                    <span className="text-loss tabular-nums">${fmt(totalSells)}</span>
                  </div>
                </div>
                {/* Desktop: Recharts bar chart */}
                {data.watchlists.length > 1 && (
                  <div className="hidden sm:block" style={{ width: 220, height: 64 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={data.watchlists.map((wl) => ({
                          name: wl.watchlist.replace(/_/g, ' ').slice(0, 8),
                          buy: wl.net_buy_value,
                          sell: -wl.net_sell_value,
                        }))}
                        margin={{ top: 2, right: 2, bottom: 0, left: 2 }}
                        barGap={1}
                        barSize={12}
                      >
                        <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#6b7280' }} axisLine={false} tickLine={false} />
                        <YAxis hide />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#1a1b23', border: '1px solid #2d2e3a', borderRadius: 8, fontSize: 11 }}
                          labelStyle={{ color: '#9ca3af' }}
                          formatter={(value: number) => ['$' + fmt(Math.abs(value))]}
                        />
                        <Bar dataKey="buy" name="Buy" radius={[2, 2, 0, 0]}>
                          {data.watchlists.map((_, i) => (
                            <Cell key={i} fill="#10b981" fillOpacity={0.8} />
                          ))}
                        </Bar>
                        <Bar dataKey="sell" name="Sell" radius={[0, 0, 2, 2]}>
                          {data.watchlists.map((_, i) => (
                            <Cell key={i} fill="#ef4444" fillOpacity={0.8} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Per-watchlist action tables */}
          {data.watchlists.map((wl) => {
            const visibleActions = showHolds
              ? wl.actions
              : wl.actions.filter((a) => a.action !== 'HOLD');

            if (visibleActions.length === 0) return null;

            return (
              <div key={wl.watchlist} className="bg-surface-light border border-surface-lighter/40 rounded-xl overflow-hidden overflow-x-auto shadow-md shadow-black/10">
                <div className="px-4 py-3 border-b border-surface-lighter/40 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white capitalize">
                      {wl.watchlist.replace(/_/g, ' ')}
                    </h3>
                    <p className="text-[11px] text-muted">{wl.date}</p>
                  </div>
                  <div className="flex gap-3 text-xs">
                    {wl.buy_count > 0 && (
                      <span className="text-gain font-medium">
                        {wl.buy_count} buy · ${fmt(wl.net_buy_value)}
                      </span>
                    )}
                    {wl.sell_count > 0 && (
                      <span className="text-loss font-medium">
                        {wl.sell_count} sell · ${fmt(wl.net_sell_value)}
                      </span>
                    )}
                    {wl.hold_count > 0 && (
                      <span className="text-muted">
                        {wl.hold_count} hold
                      </span>
                    )}
                  </div>
                </div>
                <table className="w-full text-sm min-w-[500px]">
                  <thead>
                    <tr className="border-b border-surface-lighter/30 text-muted/50 text-xs uppercase tracking-wider">
                      <th className="text-left px-4 py-2 font-semibold">Action</th>
                      <th className="text-left px-4 py-2 font-semibold">Ticker</th>
                      <th className="text-right px-4 py-2 font-semibold">Shares</th>
                      <th className="text-right px-4 py-2 font-semibold">Price</th>
                      <th className="text-right px-4 py-2 font-semibold">Amount</th>
                      <th className="text-right px-4 py-2 font-semibold">Wt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleActions.map((a) => {
                      const style = ACTION_STYLE[a.action];
                      return (
                        <tr
                          key={`${a.ticker}-${a.action}`}
                          className={`border-b border-surface-lighter/10 hover:bg-surface-hover/20 transition-smooth ${
                            a.action === 'HOLD' ? 'opacity-50' : ''
                          }`}
                        >
                          <td className="px-4 py-2.5">
                            <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold uppercase ${style.bg} ${style.text}`}>
                              {style.label}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 font-medium text-white">
                            <TickerLink ticker={a.ticker} />
                          </td>
                          <td className="px-4 py-2.5 text-right text-white tabular-nums">
                            {a.shares.toFixed(a.shares < 10 ? 2 : 0)}
                          </td>
                          <td className="px-4 py-2.5 text-right text-muted tabular-nums">
                            ${a.price.toFixed(2)}
                          </td>
                          <td className={`px-4 py-2.5 text-right font-medium tabular-nums ${style.text}`}>
                            ${fmt(a.dollar_value)}
                            {a.realized_pnl != null && a.realized_pnl !== 0 && (
                              <span className={`ml-1 text-xs ${a.realized_pnl >= 0 ? 'text-gain' : 'text-loss'}`}>
                                (P&L ${fmt(a.realized_pnl)})
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 text-right text-muted tabular-nums">
                            {a.weight_pct != null ? `${a.weight_pct}%` : ''}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
