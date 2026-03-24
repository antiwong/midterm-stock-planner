import { useCallback, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiFetch, type Position, type Trade, type Snapshot, type Signal } from '../api/client';
import { usePolling } from '../hooks/usePolling';
import EquityCurve from '../components/EquityCurve';
import ApiError from '../components/ApiError';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const WLS = ['moby_picks', 'tech_giants', 'semiconductors', 'precious_metals'];

export default function PaperTrading() {
  const [params] = useSearchParams();
  const [wl, setWl] = useState(params.get('wl') || 'moby_picks');

  const fetchPositions = useCallback(() => apiFetch<{ positions: Position[] }>(`/portfolios/${wl}/positions`), [wl]);
  const fetchTrades = useCallback(() => apiFetch<{ trades: Trade[] }>(`/portfolios/${wl}/trades?limit=30`), [wl]);
  const fetchSnapshots = useCallback(() => apiFetch<{ snapshots: Snapshot[] }>(`/portfolios/${wl}/snapshots?days=90`), [wl]);
  const fetchSignals = useCallback(() => apiFetch<{ signals: Signal[] }>(`/portfolios/${wl}/signals`), [wl]);

  const pos = usePolling(fetchPositions);
  const trades = usePolling(fetchTrades);
  const snaps = usePolling(fetchSnapshots);
  const sigs = usePolling(fetchSignals);

  const anyError = pos.error || trades.error || snaps.error || sigs.error;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white">Paper Trading</h1>
        <select
          value={wl}
          onChange={(e) => setWl(e.target.value)}
          className="bg-surface-light border border-surface-lighter rounded-lg px-3 py-1.5 text-sm text-white"
        >
          {WLS.map((w) => <option key={w} value={w}>{w.replace(/_/g, ' ')}</option>)}
        </select>
      </div>

      {anyError && (
        <div className="mb-4">
          <ApiError error={anyError} onRetry={() => { pos.refresh(); trades.refresh(); snaps.refresh(); sigs.refresh(); }} />
        </div>
      )}

      {/* Equity Curve */}
      <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter mb-4">
        <h2 className="text-sm font-semibold text-white mb-3">Equity Curve (vs SPY)</h2>
        <EquityCurve snapshots={snaps.data?.snapshots || []} showBenchmark height={280} />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Daily P&L */}
        <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter">
          <h2 className="text-sm font-semibold text-white mb-3">Daily P&L</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={(snaps.data?.snapshots || []).slice(-20)}>
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
              <Tooltip
                contentStyle={{ background: '#22232d', border: '1px solid #2a2b37', borderRadius: 8, color: '#e2e8f0' }}
                formatter={(v) => `${(Number(v) * 100).toFixed(2)}%`}
              />
              <Bar dataKey="daily_return">
                {(snaps.data?.snapshots || []).slice(-20).map((s, i) => (
                  <Cell key={i} fill={s.daily_return >= 0 ? '#10b981' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Signals */}
        <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter">
          <h2 className="text-sm font-semibold text-white mb-3">Latest Signals</h2>
          <div className="space-y-1 max-h-[200px] overflow-auto">
            {(sigs.data?.signals || []).slice(0, 15).map((s) => (
              <div key={s.ticker} className="flex justify-between text-xs py-1 border-b border-surface-lighter/50">
                <span className="text-white font-medium w-16">{s.ticker}</span>
                <span className={s.action === 'BUY' ? 'text-gain' : 'text-loss'}>{s.action}</span>
                <span className="text-muted">#{s.rank}</span>
                <span className="text-muted">{s.prediction.toFixed(3)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Positions */}
      <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter mb-4">
        <h2 className="text-sm font-semibold text-white mb-3">Active Positions</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-muted text-left border-b border-surface-lighter">
              <th className="pb-2">Ticker</th>
              <th className="pb-2 text-right">Shares</th>
              <th className="pb-2 text-right">Entry</th>
              <th className="pb-2 text-right">Weight</th>
              <th className="pb-2 text-right">Entry Date</th>
            </tr>
          </thead>
          <tbody>
            {(pos.data?.positions || []).map((p) => (
              <tr key={p.ticker} className="border-b border-surface-lighter/50">
                <td className="py-2 text-white font-medium">{p.ticker}</td>
                <td className="py-2 text-right">{p.shares.toFixed(2)}</td>
                <td className="py-2 text-right">${p.entry_price.toFixed(2)}</td>
                <td className="py-2 text-right">{(p.weight * 100).toFixed(1)}%</td>
                <td className="py-2 text-right text-muted">{p.entry_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Trade History */}
      <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter">
        <h2 className="text-sm font-semibold text-white mb-3">Recent Trades</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-muted text-left border-b border-surface-lighter">
              <th className="pb-2">Date</th>
              <th className="pb-2">Ticker</th>
              <th className="pb-2">Action</th>
              <th className="pb-2 text-right">Shares</th>
              <th className="pb-2 text-right">Price</th>
              <th className="pb-2 text-right">Value</th>
            </tr>
          </thead>
          <tbody>
            {(trades.data?.trades || []).map((t, i) => (
              <tr key={i} className="border-b border-surface-lighter/50">
                <td className="py-1.5 text-muted">{t.date}</td>
                <td className="py-1.5 text-white">{t.ticker}</td>
                <td className={`py-1.5 ${t.action === 'BUY' ? 'text-gain' : 'text-loss'}`}>{t.action}</td>
                <td className="py-1.5 text-right">{t.shares.toFixed(2)}</td>
                <td className="py-1.5 text-right">${t.price.toFixed(2)}</td>
                <td className="py-1.5 text-right">${t.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
