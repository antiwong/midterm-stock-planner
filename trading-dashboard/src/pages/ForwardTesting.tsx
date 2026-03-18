import { useCallback, useState } from 'react';
import { apiFetch, type Prediction } from '../api/client';
import { usePolling } from '../hooks/usePolling';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function ForwardTesting() {
  const [horizon, setHorizon] = useState(5);

  const fetchPredictions = useCallback(
    () => apiFetch<{ predictions: Prediction[]; count: number }>(`/forward/predictions?horizon=${horizon}&limit=500`),
    [horizon],
  );
  const fetchAccuracy = useCallback(() => apiFetch<{
    overall: { total: number; hits: number | null; avg_return: number | null };
    by_watchlist: Array<{ watchlist: string; horizon_days: number; total: number; hits: number; avg_return: number }>;
    stats: { total_predictions: number; evaluated: number; active: number; pending_eval: number };
  }>('/forward/accuracy'), []);

  const preds = usePolling(fetchPredictions);
  const accuracy = usePolling(fetchAccuracy);

  const stats = accuracy.data?.stats;

  // Group predictions by watchlist for the signal summary
  const byWatchlist: Record<string, Prediction[]> = {};
  (preds.data?.predictions || []).forEach((p) => {
    if (!byWatchlist[p.watchlist]) byWatchlist[p.watchlist] = [];
    byWatchlist[p.watchlist].push(p);
  });

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white">Forward Testing</h1>
        <div className="flex gap-2">
          {[5, 63].map((h) => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              className={`px-3 py-1 rounded-lg text-sm ${
                horizon === h ? 'bg-accent text-white' : 'bg-surface-light text-muted border border-surface-lighter'
              }`}
            >
              {h}-day
            </button>
          ))}
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Predictions', value: stats?.total_predictions || 0 },
          { label: 'Evaluated', value: stats?.evaluated || 0 },
          { label: 'Active', value: stats?.active || 0 },
          { label: 'Pending Eval', value: stats?.pending_eval || 0 },
        ].map((s) => (
          <div key={s.label} className="bg-surface-light rounded-xl p-4 border border-surface-lighter">
            <div className="text-muted text-xs">{s.label}</div>
            <div className="text-xl font-bold text-white mt-1">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Hit rates by watchlist */}
      {(accuracy.data?.by_watchlist || []).length > 0 && (
        <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter mb-4">
          <h2 className="text-sm font-semibold text-white mb-3">Hit Rates by Portfolio</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={accuracy.data!.by_watchlist.map((r) => ({
              name: `${r.watchlist} (${r.horizon_days}d)`,
              hit_rate: r.total > 0 ? (r.hits / r.total) * 100 : 0,
              total: r.total,
            }))}>
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: '#22232d', border: '1px solid #2a2b37', borderRadius: 8, color: '#e2e8f0' }} />
              <Bar dataKey="hit_rate" name="Hit Rate %">
                {(accuracy.data?.by_watchlist || []).map((r, i) => (
                  <Cell key={i} fill={r.total > 0 && r.hits / r.total >= 0.5 ? '#10b981' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Predictions by watchlist */}
      {Object.entries(byWatchlist).map(([wl, predictions]) => {
        const buys = predictions.filter((p) => p.predicted_action === 'BUY').slice(0, 5);
        const sells = predictions.filter((p) => p.predicted_action === 'SELL').slice(0, 5);
        return (
          <div key={wl} className="bg-surface-light rounded-xl p-5 border border-surface-lighter mb-4">
            <h2 className="text-sm font-semibold text-white mb-3">
              {wl.replace(/_/g, ' ')} — {predictions.length} predictions
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="text-xs text-gain font-medium mb-2">TOP BUY</h3>
                {buys.map((p) => (
                  <div key={p.ticker} className="flex justify-between text-xs py-1 border-b border-surface-lighter/50">
                    <span className="text-white font-medium">#{p.predicted_rank} {p.ticker}</span>
                    <span className="text-muted">{p.predicted_score.toFixed(3)}</span>
                    <span className="text-muted">${p.entry_price.toFixed(2)}</span>
                    <span className="text-muted">{p.maturity_date}</span>
                  </div>
                ))}
              </div>
              <div>
                <h3 className="text-xs text-loss font-medium mb-2">TOP SELL</h3>
                {sells.map((p) => (
                  <div key={p.ticker} className="flex justify-between text-xs py-1 border-b border-surface-lighter/50">
                    <span className="text-white font-medium">#{p.predicted_rank} {p.ticker}</span>
                    <span className="text-muted">{p.predicted_score.toFixed(3)}</span>
                    <span className="text-muted">${p.entry_price.toFixed(2)}</span>
                    <span className="text-muted">{p.maturity_date}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
