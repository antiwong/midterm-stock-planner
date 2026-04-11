/**
 * Mini equity curve chart for portfolio summary cards.
 * Generates a synthetic 30-day portfolio value history from initialValue
 * to currentValue with realistic daily return noise, rendered as a
 * Recharts AreaChart with gain/loss coloring.
 */
import { useId } from 'react';
import { ComposedChart, AreaChart, Area, Line, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';

interface EquityCurveProps {
  initialValue: number;
  currentValue: number;
  /** Chart height in pixels (default 120) */
  height?: number;
  /** Hide tooltip for compact mode */
  hideTooltip?: boolean;
  /** Unique seed string for deterministic but distinct curves per portfolio */
  seed?: string;
  /** Real equity data points (overrides synthetic generation) */
  data?: { date: string; value: number }[];
  /** Optional benchmark overlay data (e.g. SPY cumulative return in dollar terms) */
  benchmarkData?: { date: string; value: number }[];
}

/** Seeded PRNG (mulberry32) for deterministic curves */
function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Simple string hash for seeding */
function hashSeed(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h) || 424242;
}

function generateEquityCurve(
  initialValue: number,
  currentValue: number,
  seed: string = 'default',
  days = 30,
): { day: number; value: number; label: string }[] {
  const rng = mulberry32(hashSeed(seed));
  const totalReturn = currentValue / initialValue - 1;
  // Daily return that compounds to the total return over `days`
  const dailyDrift = Math.pow(1 + totalReturn, 1 / days) - 1;
  // Volatility scaled to the magnitude of returns (min 0.3% daily vol)
  const dailyVol = Math.max(Math.abs(totalReturn) / Math.sqrt(days) * 0.8, 0.003);

  const points: { day: number; value: number; label: string }[] = [];
  let v = initialValue;

  for (let i = 0; i <= days; i++) {
    const date = new Date();
    date.setDate(date.getDate() - (days - i));
    const label = `${date.getMonth() + 1}/${date.getDate()}`;
    points.push({ day: i, value: Math.round(v), label });
    if (i < days) {
      // Random daily return with drift
      const shock = (rng() + rng() + rng() - 1.5) * 2; // approx normal via sum of uniforms
      const dailyReturn = dailyDrift + dailyVol * shock;
      v = v * (1 + dailyReturn);
    }
  }

  // Force the last point to match currentValue exactly
  points[points.length - 1].value = Math.round(currentValue);

  return points;
}

export default function EquityCurve({
  initialValue,
  currentValue,
  height = 120,
  hideTooltip = false,
  seed = 'default',
  data: realData,
  benchmarkData,
}: EquityCurveProps) {
  const gradId = useId().replace(/:/g, '_') + '_equityGrad';
  const baseData = realData
    ? realData.map((d, i) => ({ day: i, value: Math.round(d.value), label: d.date }))
    : generateEquityCurve(initialValue, currentValue, seed);

  // Merge benchmark data by index (align by position) or date
  const hasBenchmark = benchmarkData && benchmarkData.length > 0;
  const data = baseData.map((point, i) => {
    const bmPoint = hasBenchmark
      ? benchmarkData!.find((b) => b.date === point.label) ?? benchmarkData![i]
      : undefined;
    return {
      ...point,
      benchmark: bmPoint ? Math.round(bmPoint.value) : undefined,
    };
  });

  const isGain = currentValue >= initialValue;
  const stroke = isGain ? '#10b981' : '#ef4444';
  const fill = isGain ? '#10b981' : '#ef4444';

  const values = data.map((d) => d.value);
  const bmValues = hasBenchmark ? data.filter((d) => d.benchmark != null).map((d) => d.benchmark!) : [];
  const allValues = [...values, ...bmValues];
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const pad = (max - min) * 0.08 || 100;

  const showLegend = hasBenchmark && !hideTooltip;
  const showXAxis = !hideTooltip && height >= 80;
  const ChartComponent = hasBenchmark ? ComposedChart : AreaChart;

  // Sparse tick labels: show ~3-4 date labels across the curve
  const xAxisTicks = showXAxis
    ? data.filter((_, i) => i === 0 || i === Math.floor(data.length / 3) || i === Math.floor(2 * data.length / 3) || i === data.length - 1).map((d) => d.day)
    : [];

  return (
    <div className="w-full">
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ChartComponent data={data} margin={{ top: 4, right: 4, bottom: showXAxis ? 2 : 0, left: 4 }}>
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={fill} stopOpacity={0.25} />
                <stop offset="100%" stopColor={fill} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <YAxis domain={[min - pad, max + pad]} hide />
            {showXAxis && (
              <XAxis
                dataKey="day"
                ticks={xAxisTicks}
                tickFormatter={(day: number) => data[day]?.label ?? ''}
                tick={{ fontSize: 9, fill: '#4b5563' }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
            )}
            {!hideTooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1a1b23',
                  border: '1px solid #2d2e3a',
                  borderRadius: 8,
                  fontSize: 11,
                }}
                labelStyle={{ color: '#9ca3af' }}
                labelFormatter={(_, payload) => payload?.[0]?.payload?.label ?? ''}
                formatter={(value: number, name: string) => [
                  `$${value.toLocaleString()}`,
                  name === 'benchmark' ? 'SPY' : 'Portfolio',
                ]}
              />
            )}
            <Area
              type="monotone"
              dataKey="value"
              stroke={stroke}
              strokeWidth={1.5}
              fill={`url(#${gradId})`}
              dot={false}
              isAnimationActive={false}
            />
            {hasBenchmark && (
              <Line
                type="monotone"
                dataKey="benchmark"
                stroke="#64748b"
                strokeWidth={1.2}
                strokeDasharray="4 3"
                strokeOpacity={0.6}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            )}
          </ChartComponent>
        </ResponsiveContainer>
      </div>
      {showLegend && (
        <div className="flex items-center gap-4 mt-1.5 px-1">
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: stroke }} />
            <span className="text-[10px] text-muted">Portfolio</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-full bg-slate-500 opacity-60" />
            <span className="text-[10px] text-muted">SPY</span>
          </div>
        </div>
      )}
    </div>
  );
}
