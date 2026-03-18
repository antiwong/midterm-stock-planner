import { useCallback } from 'react';
import { apiFetch, type MobyPick, type MobyPerformance } from '../api/client';
import { usePolling } from '../hooks/usePolling';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function MobyAnalysis() {
  const fetchPicks = useCallback(() => apiFetch<{ picks: MobyPick[] }>('/moby/analysis'), []);
  const fetchPerf = useCallback(() => apiFetch<{ performance: MobyPerformance[] }>('/moby/performance'), []);

  const picks = usePolling(fetchPicks);
  const perf = usePolling(fetchPerf);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Moby Analysis</h1>

      {/* Pick cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {(picks.data?.picks || []).map((p) => {
          const upColor = p.upside_pct >= 30 ? 'text-gain' : p.upside_pct >= 15 ? 'text-yellow-400' : 'text-muted';
          return (
            <div key={p.ticker} className="bg-surface-light rounded-xl p-5 border border-surface-lighter">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="text-white font-bold text-lg">{p.ticker}</h3>
                  <p className="text-xs text-muted truncate max-w-[200px]">{p.company}</p>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-accent/20 text-accent-light">
                  {p.rating}
                </span>
              </div>
              <div className="flex justify-between items-end mt-3">
                <div>
                  <div className="text-muted text-xs">Current</div>
                  <div className="text-white font-semibold">${p.current_price.toFixed(2)}</div>
                </div>
                <div className="text-right">
                  <div className="text-muted text-xs">Target</div>
                  <div className="text-white font-semibold">${p.price_target.toFixed(0)}</div>
                </div>
                <div className="text-right">
                  <div className="text-muted text-xs">Upside</div>
                  <div className={`font-bold ${upColor}`}>{p.upside_pct}%</div>
                </div>
              </div>
              {p.earnings_date && (
                <div className="mt-2 text-xs text-muted">Earnings: {p.earnings_date}</div>
              )}
              {p.article_title && (
                <div className="mt-2 text-xs text-muted/70 italic truncate">{p.article_title}</div>
              )}
            </div>
          );
        })}
      </div>

      {/* Upside bar chart */}
      <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter mb-4">
        <h2 className="text-sm font-semibold text-white mb-3">Upside Potential</h2>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart
            data={(picks.data?.picks || [])
              .sort((a, b) => b.upside_pct - a.upside_pct)
              .map((p) => ({ ticker: p.ticker, upside: p.upside_pct }))}
            layout="vertical"
          >
            <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} unit="%" />
            <YAxis type="category" dataKey="ticker" tick={{ fill: '#e2e8f0', fontSize: 12 }} tickLine={false} width={60} />
            <Tooltip contentStyle={{ background: '#22232d', border: '1px solid #2a2b37', borderRadius: 8, color: '#e2e8f0' }} />
            <Bar dataKey="upside" name="Upside %">
              {(picks.data?.picks || [])
                .sort((a, b) => b.upside_pct - a.upside_pct)
                .map((p, i) => (
                  <Cell key={i} fill={p.upside_pct >= 30 ? '#10b981' : p.upside_pct >= 15 ? '#f59e0b' : '#64748b'} />
                ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Performance tracking */}
      {(perf.data?.performance || []).length > 0 && (
        <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter">
          <h2 className="text-sm font-semibold text-white mb-3">Performance vs Target</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted text-left border-b border-surface-lighter">
                <th className="pb-2">Ticker</th>
                <th className="pb-2 text-right">Entry</th>
                <th className="pb-2 text-right">Current</th>
                <th className="pb-2 text-right">Target</th>
                <th className="pb-2 text-right">Return</th>
                <th className="pb-2 text-right">Progress</th>
              </tr>
            </thead>
            <tbody>
              {(perf.data?.performance || []).map((p) => (
                <tr key={p.ticker} className="border-b border-surface-lighter/50">
                  <td className="py-2 text-white font-medium">{p.ticker}</td>
                  <td className="py-2 text-right">${p.entry_price.toFixed(2)}</td>
                  <td className="py-2 text-right">${p.current_price.toFixed(2)}</td>
                  <td className="py-2 text-right">${p.price_target.toFixed(0)}</td>
                  <td className={`py-2 text-right ${p.actual_return_pct >= 0 ? 'text-gain' : 'text-loss'}`}>
                    {p.actual_return_pct >= 0 ? '+' : ''}{p.actual_return_pct.toFixed(1)}%
                  </td>
                  <td className="py-2 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 bg-surface-lighter rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full bg-accent"
                          style={{ width: `${Math.min(100, Math.max(0, p.progress_pct))}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted">{p.progress_pct.toFixed(0)}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
