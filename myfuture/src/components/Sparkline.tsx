/**
 * Inline sparkline for position rows.
 * Generates a synthetic price curve between entry_price and current_price
 * using seeded pseudo-random walk, then renders a tiny Recharts AreaChart.
 */
import { AreaChart, Area, ResponsiveContainer, YAxis } from 'recharts';

interface SparklineProps {
  entryPrice: number;
  currentPrice: number;
  /** Unique seed so each ticker gets a consistent curve */
  seed?: string;
  width?: number;
  height?: number;
  /** Real price data points — overrides synthetic generation */
  data?: number[];
}

/** Simple hash for deterministic pseudo-random numbers */
function hashSeed(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

/** Seeded PRNG (mulberry32) */
function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function generateCurve(
  entryPrice: number,
  currentPrice: number,
  seed: string,
  points = 20,
): { v: number }[] {
  const rng = mulberry32(hashSeed(seed));
  const diff = currentPrice - entryPrice;

  // Build a random walk that starts at entryPrice and ends at currentPrice
  const raw: number[] = [0];
  for (let i = 1; i < points; i++) {
    raw.push(raw[i - 1] + (rng() - 0.48)); // slight upward bias
  }

  // Rescale so raw[0] -> entryPrice and raw[last] -> currentPrice
  const rawStart = raw[0];
  const rawEnd = raw[points - 1];
  const rawRange = rawEnd - rawStart || 1;

  return raw.map((r) => {
    const t = (r - rawStart) / rawRange; // 0..1
    const price = entryPrice + t * diff;
    // Add a little noise for realism
    const noise = (rng() - 0.5) * Math.abs(diff) * 0.15;
    return { v: price + noise };
  });
}

export default function Sparkline({
  entryPrice,
  currentPrice,
  seed = 'default',
  width = 80,
  height = 32,
  data: realData,
}: SparklineProps) {
  const data = realData
    ? realData.map((v) => ({ v }))
    : generateCurve(entryPrice, currentPrice, seed);
  const isGain = currentPrice >= entryPrice;
  const stroke = isGain ? '#10b981' : '#ef4444';
  const fill = isGain ? '#10b981' : '#ef4444';

  // Compute Y domain with a small padding
  const values = data.map((d) => d.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.1 || 1;

  return (
    <div style={{ width, height }} className="inline-block align-middle">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 1, right: 1, bottom: 1, left: 1 }}>
          <YAxis domain={[min - pad, max + pad]} hide />
          <Area
            type="monotone"
            dataKey="v"
            stroke={stroke}
            strokeWidth={1.5}
            fill={fill}
            fillOpacity={0.12}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
