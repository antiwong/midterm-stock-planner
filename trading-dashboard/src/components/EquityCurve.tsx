import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { Snapshot } from '../api/client';

interface Props {
  snapshots: Snapshot[];
  height?: number;
  showBenchmark?: boolean;
  mini?: boolean;
}

export default function EquityCurve({ snapshots, height = 300, showBenchmark = false, mini = false }: Props) {
  if (!snapshots.length) return <div className="text-muted text-sm">No data</div>;

  // Normalize to base 100
  const base = snapshots[0]?.portfolio_value || 100000;
  const data = snapshots.map((s) => ({
    date: s.date,
    portfolio: (s.portfolio_value / base) * 100,
    benchmark: showBenchmark ? (1 + (s.benchmark_cumulative || 0)) * 100 : undefined,
  }));

  if (mini) {
    return (
      <ResponsiveContainer width="100%" height={60}>
        <LineChart data={data}>
          <Line type="monotone" dataKey="portfolio" stroke="#6366f1" dot={false} strokeWidth={1.5} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} />
        <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} domain={['auto', 'auto']} />
        <Tooltip
          contentStyle={{ background: '#22232d', border: '1px solid #2a2b37', borderRadius: 8, color: '#e2e8f0' }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <ReferenceLine y={100} stroke="#64748b" strokeDasharray="3 3" />
        <Line type="monotone" dataKey="portfolio" stroke="#6366f1" dot={false} strokeWidth={2} name="Portfolio" />
        {showBenchmark && (
          <Line type="monotone" dataKey="benchmark" stroke="#64748b" dot={false} strokeWidth={1} strokeDasharray="4 4" name="SPY" />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
