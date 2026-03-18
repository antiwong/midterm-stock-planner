import { useCallback } from 'react';
import { apiFetch, type PortfolioSummary } from '../api/client';
import { usePolling } from '../hooks/usePolling';
import PortfolioCard from '../components/PortfolioCard';

export default function Dashboard() {
  const fetch = useCallback(() => apiFetch<{ portfolios: PortfolioSummary[] }>('/portfolios/summary'), []);
  const { data, loading, lastUpdated } = usePolling(fetch);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white">Portfolio Overview</h1>
        {lastUpdated && (
          <span className="text-xs text-muted">Updated {lastUpdated.toLocaleTimeString()}</span>
        )}
      </div>

      {loading && !data ? (
        <div className="text-muted">Loading...</div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {data?.portfolios.map((p) => (
            <PortfolioCard key={p.watchlist} p={p} />
          ))}
        </div>
      )}

      {data && (
        <div className="mt-8 bg-surface-light rounded-xl p-5 border border-surface-lighter">
          <h2 className="text-lg font-semibold text-white mb-4">Summary</h2>
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
              {data.portfolios.map((p) => (
                <tr key={p.watchlist} className="border-b border-surface-lighter/50">
                  <td className="py-2 text-white font-medium">{p.watchlist.replace(/_/g, ' ')}</td>
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
      )}
    </div>
  );
}
