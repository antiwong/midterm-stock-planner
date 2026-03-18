import { useNavigate } from 'react-router-dom';
import type { PortfolioSummary } from '../api/client';

const MODE_BADGE: Record<string, string> = {
  alpaca: 'bg-accent/20 text-accent-light',
  local: 'bg-surface-lighter text-muted',
};

export default function PortfolioCard({ p }: { p: PortfolioSummary }) {
  const navigate = useNavigate();
  const ret = p.cumulative_return * 100;
  const daily = p.daily_return * 100;
  const isUp = ret >= 0;
  const dailyUp = daily >= 0;

  return (
    <div
      onClick={() => navigate(`/paper-trading?wl=${p.watchlist}`)}
      className="bg-surface-light rounded-xl p-5 border border-surface-lighter hover:border-accent/30 cursor-pointer transition-all"
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="text-white font-semibold text-sm">{p.watchlist.replace(/_/g, ' ')}</h3>
          <span className={`text-xs px-2 py-0.5 rounded-full ${MODE_BADGE[p.mode] || MODE_BADGE.local}`}>
            {p.mode}
          </span>
        </div>
        <span className="text-xs text-muted">{p.positions_count} pos</span>
      </div>

      <div className="text-2xl font-bold text-white mb-1">
        ${p.portfolio_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
      </div>

      <div className="flex gap-4 text-sm">
        <span className={isUp ? 'text-gain' : 'text-loss'}>
          {isUp ? '+' : ''}{ret.toFixed(2)}%
        </span>
        <span className={`text-xs ${dailyUp ? 'text-gain/70' : 'text-loss/70'}`}>
          today {dailyUp ? '+' : ''}{daily.toFixed(2)}%
        </span>
      </div>
    </div>
  );
}
