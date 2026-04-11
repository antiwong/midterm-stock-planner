import { BookOpen, Wrench, Sparkles, Shield } from 'lucide-react';

interface ChangeEntry {
  version: string;
  date: string;
  type: 'feature' | 'fix' | 'infra' | 'ui';
  title: string;
  items: string[];
}

const CHANGELOG: ChangeEntry[] = [
  {
    version: '2.1.0',
    date: '2026-04-11',
    type: 'ui',
    title: 'Dashboard UI Overhaul',
    items: [
      'Lucide SVG icons replace all Unicode nav icons (17 semantic icons)',
      'Fixed bottom tab bar on mobile (5 primary tabs + More overlay)',
      'Sparklines in portfolio position rows with real price data from API',
      'Equity curve with SPY benchmark overlay on Grand Total card',
      'Per-portfolio mini equity curves in card headers',
      'Return leaderboard with gold/silver/bronze rank badges',
      'Sortable portfolio summary table (Value, Return, Realized, Unrealized)',
      'Risk metric chips (Sharpe, MaxDD, WinRate) on portfolio headers',
      'Skeleton shimmer loading states on all pages',
      'Styled error cards with retry buttons',
      'Polling spinner showing data refresh status',
      'Focus-visible keyboard navigation rings',
      '44px+ touch targets on all interactive elements',
      'Buy/sell bar chart on DailyActions (desktop + mobile ratio bar)',
      'Empty state with CalendarOff icon for no-trade days',
    ],
  },
  {
    version: '2.0.1',
    date: '2026-04-08',
    type: 'feature',
    title: 'DXY Regime Filter for Precious Metals',
    items: [
      'UUP-based dollar index position scaling (3 bands: 25%/60%/100%)',
      'Per-watchlist regime overrides via config.yaml',
      'Cross-asset features: dxy_momentum, gold_silver_ratio, real_yield_proxy',
      'Reference ETFs (UUP, TIP) auto-downloaded daily',
      'Unpaused precious_metals with DXY protection',
    ],
  },
  {
    version: '2.0.0',
    date: '2026-03-27',
    type: 'feature',
    title: 'Portfolio P&L + Daily Actions',
    items: [
      'Portfolio Overview page with live P&L per position',
      'Daily Actions page showing net BUY/SELL per watchlist',
      'API endpoints: /portfolios/overview, /portfolios/daily-actions',
      'Grand total across all 10 paper trading portfolios',
    ],
  },
  {
    version: '1.9.0',
    date: '2026-03-27',
    type: 'feature',
    title: 'Concentration Limits & Risk Controls',
    items: [
      'Max 25% single-position weight across all portfolios',
      'Sector concentration caps (max 2 from same sector)',
      'Industry sub-group limits for focused watchlists',
      'Stop-loss at -15% with 5-day cooldown',
      'VIX-based position scaling (20-25 = 50%, 25-30 = 30%, >30 = exit)',
    ],
  },
  {
    version: '',
    date: '2026-04-03',
    type: 'fix',
    title: 'Position UNIQUE Constraint Crash (P1)',
    items: [
      'Fixed UNIQUE constraint crash on sell/rebuy same-day cycles',
      'tech_giants portfolio was frozen since 2026-03-27',
      'Added IntegrityError handling to all 4 UPDATE/INSERT paths',
    ],
  },
  {
    version: '',
    date: '2026-04-03',
    type: 'infra',
    title: 'Infrastructure Hardening',
    items: [
      '2GB swap file (prevents OOM kills during LightGBM training)',
      'Daily backups of all 10 paper trading DBs (7-day rotation)',
      'Log rotation (weekly, 4 weeks, compressed)',
      'Heartbeat monitor via systemd timer (independent of cron)',
      'Google Trends server-side fetching via trendspy',
      'Fixed cron silent failure from UTF-8 em-dash in comments',
      'Fixed cron SHELL bug (dash vs bash for .env sourcing)',
    ],
  },
  {
    version: '',
    date: '2026-03-27',
    type: 'fix',
    title: 'Stop-Loss Zombie Bug (P0)',
    items: [
      'Fixed 98 zombie positions across all portfolios (exit fields never written)',
      'Recovered accurate P&L: actual loss $30.5K (not $44.5K as shown)',
      'Fixed cron timezone misalignment (all jobs ran 8 hours off)',
      'Fixed Moby Picks data corruption (24 trades with price=0)',
    ],
  },
];

const TYPE_CONFIG = {
  feature: { icon: Sparkles, color: 'text-accent-light', bg: 'bg-accent/10', label: 'Feature' },
  fix: { icon: Wrench, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Fix' },
  infra: { icon: Shield, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'Infra' },
  ui: { icon: BookOpen, color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'UI' },
};

export default function Changelog() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold text-white">Changelog</h1>
        <p className="text-xs text-muted mt-0.5">What's new in myFuture</p>
      </div>

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-[19px] top-8 bottom-0 w-px bg-surface-lighter/40" />

        <div className="space-y-6">
          {CHANGELOG.map((entry, i) => {
            const cfg = TYPE_CONFIG[entry.type];
            const Icon = cfg.icon;
            return (
              <div key={i} className="relative flex gap-4">
                {/* Timeline dot */}
                <div className={`w-10 h-10 rounded-xl ${cfg.bg} flex items-center justify-center flex-shrink-0 z-10 border border-surface-lighter/30`}>
                  <Icon size={18} className={cfg.color} />
                </div>

                {/* Card */}
                <div className="flex-1 bg-surface-light border border-surface-lighter/40 rounded-xl p-4 shadow-md shadow-black/10">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {entry.version && (
                        <span className="text-xs font-bold text-white bg-surface-lighter/40 px-2 py-0.5 rounded-md">
                          v{entry.version}
                        </span>
                      )}
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-md ${cfg.bg} ${cfg.color}`}>
                        {cfg.label}
                      </span>
                    </div>
                    <span className="text-[11px] text-muted tabular-nums">{entry.date}</span>
                  </div>

                  <h3 className="text-sm font-semibold text-white mb-2">{entry.title}</h3>

                  <ul className="space-y-1">
                    {entry.items.map((item, j) => (
                      <li key={j} className="text-xs text-muted leading-relaxed flex gap-2">
                        <span className="text-surface-lighter mt-0.5 flex-shrink-0">-</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
