import { useCallback } from 'react';
import { apiFetch, type PortfolioSummary, type Snapshot, type Position } from '../api/client';
import { usePolling } from '../hooks/usePolling';
import ApiError from '../components/ApiError';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';

const WLS = ['moby_picks', 'tech_giants', 'semiconductors', 'precious_metals'];
const COLORS: Record<string, string> = {
  moby_picks: '#6366f1',
  tech_giants: '#06b6d4',
  semiconductors: '#10b981',
  precious_metals: '#f59e0b',
};

export default function MultiPortfolio() {
  const fetchSummary = useCallback(() => apiFetch<{ portfolios: PortfolioSummary[] }>('/portfolios/summary'), []);
  const fetchAllSnaps = useCallback(async () => {
    const results: Record<string, Snapshot[]> = {};
    await Promise.all(
      WLS.map(async (wl) => {
        const d = await apiFetch<{ snapshots: Snapshot[] }>(`/portfolios/${wl}/snapshots?days=90`);
        results[wl] = d.snapshots;
      }),
    );
    return results;
  }, []);
  const fetchAllPositions = useCallback(async () => {
    const results: Record<string, Position[]> = {};
    await Promise.all(
      WLS.map(async (wl) => {
        const d = await apiFetch<{ positions: Position[] }>(`/portfolios/${wl}/positions`);
        results[wl] = d.positions;
      }),
    );
    return results;
  }, []);

  const summary = usePolling(fetchSummary);
  const snaps = usePolling(fetchAllSnaps);
  const positions = usePolling(fetchAllPositions);

  const anyError = summary.error || snaps.error || positions.error;

  // Build overlay chart data
  const chartData: Record<string, number | string>[] = [];
  if (snaps.data) {
    const dateSet = new Set<string>();
    Object.values(snaps.data).forEach((arr) => arr.forEach((s) => dateSet.add(s.date)));
    const dates = Array.from(dateSet).sort();

    const bases: Record<string, number> = {};
    dates.forEach((date) => {
      const row: Record<string, number | string> = { date };
      WLS.forEach((wl) => {
        const snap = snaps.data?.[wl]?.find((s) => s.date === date);
        if (snap) {
          if (!bases[wl]) bases[wl] = snap.portfolio_value;
          row[wl] = (snap.portfolio_value / bases[wl]) * 100;
        }
      });
      chartData.push(row);
    });
  }

  // Position overlap
  const allTickers = new Map<string, string[]>();
  if (positions.data) {
    Object.entries(positions.data).forEach(([wl, pos]) => {
      pos.forEach((p) => {
        if (!allTickers.has(p.ticker)) allTickers.set(p.ticker, []);
        allTickers.get(p.ticker)!.push(wl);
      });
    });
  }
  const overlap = Array.from(allTickers.entries())
    .filter(([, wls]) => wls.length > 1)
    .sort((a, b) => b[1].length - a[1].length);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Multi-Portfolio Comparison</h1>

      {anyError && (
        <div className="mb-4">
          <ApiError error={anyError} onRetry={() => { summary.refresh(); snaps.refresh(); positions.refresh(); }} />
        </div>
      )}

      {/* Overlay equity curves */}
      <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter mb-4">
        <h2 className="text-sm font-semibold text-white mb-3">Performance (Normalized to 100)</h2>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={chartData}>
            <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} />
            <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} domain={['auto', 'auto']} />
            <Tooltip contentStyle={{ background: '#22232d', border: '1px solid #2a2b37', borderRadius: 8, color: '#e2e8f0' }} />
            <Legend />
            <ReferenceLine y={100} stroke="#64748b" strokeDasharray="3 3" />
            {WLS.map((wl) => (
              <Line key={wl} type="monotone" dataKey={wl} stroke={COLORS[wl]} dot={false} strokeWidth={2} name={wl.replace(/_/g, ' ')} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Summary table */}
      <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter mb-4">
        <h2 className="text-sm font-semibold text-white mb-3">Portfolio Comparison</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-muted text-left border-b border-surface-lighter">
              <th className="pb-2">Portfolio</th>
              <th className="pb-2 text-right">Value</th>
              <th className="pb-2 text-right">Daily</th>
              <th className="pb-2 text-right">Total Return</th>
              <th className="pb-2 text-right">Positions</th>
              <th className="pb-2 text-right">Mode</th>
            </tr>
          </thead>
          <tbody>
            {(summary.data?.portfolios || []).map((p) => (
              <tr key={p.watchlist} className="border-b border-surface-lighter/50">
                <td className="py-2">
                  <span className="inline-block w-3 h-3 rounded-full mr-2" style={{ background: COLORS[p.watchlist] }} />
                  <span className="text-white font-medium">{p.watchlist.replace(/_/g, ' ')}</span>
                </td>
                <td className="py-2 text-right">${p.portfolio_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                <td className={`py-2 text-right ${p.daily_return >= 0 ? 'text-gain' : 'text-loss'}`}>
                  {(p.daily_return * 100).toFixed(2)}%
                </td>
                <td className={`py-2 text-right ${p.cumulative_return >= 0 ? 'text-gain' : 'text-loss'}`}>
                  {(p.cumulative_return * 100).toFixed(2)}%
                </td>
                <td className="py-2 text-right">{p.positions_count}</td>
                <td className="py-2 text-right text-muted">{p.mode}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Position overlap */}
      {overlap.length > 0 && (
        <div className="bg-surface-light rounded-xl p-5 border border-surface-lighter">
          <h2 className="text-sm font-semibold text-white mb-3">Position Overlap (2+ portfolios)</h2>
          <div className="space-y-1">
            {overlap.map(([ticker, wls]) => (
              <div key={ticker} className="flex items-center gap-2 text-sm py-1 border-b border-surface-lighter/50">
                <span className="text-white font-medium w-16">{ticker}</span>
                <div className="flex gap-1">
                  {wls.map((wl) => (
                    <span key={wl} className="px-2 py-0.5 rounded text-xs" style={{ background: COLORS[wl] + '30', color: COLORS[wl] }}>
                      {wl.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
