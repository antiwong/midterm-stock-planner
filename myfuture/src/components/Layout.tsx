import { useState, useEffect, useRef } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';

const NAV_SECTIONS = [
  {
    label: 'Trading',
    items: [
      { to: '/', label: 'Dashboard', icon: '◈' },
      { to: '/paper-trading', label: 'Paper Trading', icon: '◆' },
      { to: '/forward-testing', label: 'Forward Testing', icon: '◇' },
      { to: '/multi-portfolio', label: 'Multi-Portfolio', icon: '◫' },
      { to: '/signals', label: 'Signal Tracker', icon: '⚡' },
    ],
  },
  {
    label: 'Analysis',
    items: [
      { to: '/watchlists', label: 'Watchlists', icon: '◱' },
      { to: '/moby', label: 'Moby Analysis', icon: '◉' },
      { to: '/sentiment', label: 'Sentiment', icon: '◔' },
      { to: '/realtime-monitoring', label: 'Monitoring', icon: '◎' },
      { to: '/earnings-calendar', label: 'Earnings', icon: '◰' },
      { to: '/watchlist-comparison', label: 'Comparison', icon: '◧' },
      { to: '/recommendations', label: 'Recommendations', icon: '◈' },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/alerts', label: 'Alerts', icon: '◬' },
      { to: '/notifications', label: 'Notifications', icon: '◩' },
      { to: '/settings', label: 'Settings', icon: '◈' },
    ],
  },
];

interface LayoutProps {
  user: { username: string; display_name?: string };
  onLogout: () => void;
}

export default function Layout({ user, onLogout }: LayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [search, setSearch] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Press "/" anywhere to focus search (Bloomberg-style)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        searchRef.current?.focus();
      }
      if (e.key === 'Escape') {
        searchRef.current?.blur();
        setSearch('');
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile header */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-30 bg-surface-light/90 backdrop-blur-md border-b border-surface-lighter px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-accent to-purple flex items-center justify-center">
            <span className="text-[10px] font-bold text-white">mF</span>
          </div>
          <span className="text-sm font-semibold text-white tracking-tight">myFuture</span>
        </div>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-surface-lighter transition-smooth"
          aria-label="Toggle menu"
        >
          <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            {mobileOpen ? (
              <><line x1="5" y1="5" x2="15" y2="15" /><line x1="5" y1="15" x2="15" y2="5" /></>
            ) : (
              <><line x1="3" y1="5" x2="17" y2="5" /><line x1="3" y1="10" x2="17" y2="10" /><line x1="3" y1="15" x2="17" y2="15" /></>
            )}
          </svg>
        </button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-20 animate-fade-in"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <nav className={`
        fixed md:static z-20 top-0 left-0 h-full w-60 flex-shrink-0 flex flex-col
        border-r border-surface-lighter/60
        bg-gradient-to-b from-surface-light via-surface-light to-surface
        transition-transform duration-300 ease-out
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        {/* Brand */}
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent via-purple to-cyan flex items-center justify-center shadow-lg shadow-accent/20">
              <span className="text-xs font-bold text-white tracking-tighter">mF</span>
            </div>
            <div>
              <h1 className="text-[15px] font-bold text-white tracking-tight">myFuture</h1>
              <p className="text-[10px] text-muted tracking-widest uppercase">Portfolio Monitor</p>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="mx-4 h-px bg-gradient-to-r from-transparent via-surface-lighter to-transparent" />

        {/* Search */}
        <div className="px-4 py-2">
          <div className="relative">
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && search.trim()) {
                  navigate(`/ticker/${search.trim()}`);
                  setSearch('');
                  setMobileOpen(false);
                  searchRef.current?.blur();
                }
              }}
              placeholder="Search ticker..."
              className="w-full bg-surface/50 border border-surface-lighter/40 rounded-lg pl-3 pr-8 py-1.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-smooth"
            />
            <kbd className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-gray-600 bg-surface-lighter/40 px-1.5 py-0.5 rounded font-mono">/</kbd>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 pt-3 pb-2 overflow-y-auto px-3 space-y-4">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label}>
              <p className="text-[10px] font-semibold text-muted/60 uppercase tracking-[0.15em] px-3 mb-1.5">
                {section.label}
              </p>
              <div className="space-y-0.5">
                {section.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) =>
                      `group flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] transition-smooth relative ${
                        isActive
                          ? 'bg-accent/10 text-white font-medium glow-accent'
                          : 'text-gray-500 hover:text-gray-300 hover:bg-surface-hover'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-full bg-accent" />
                        )}
                        <span className={`text-xs ${isActive ? 'text-accent-light' : 'text-gray-600 group-hover:text-gray-400'} transition-smooth`}>
                          {item.icon}
                        </span>
                        <span>{item.label}</span>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* User + Footer */}
        <div className="mx-4 h-px bg-gradient-to-r from-transparent via-surface-lighter to-transparent" />
        <div className="px-5 py-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-muted truncate">{user.display_name || user.username}</span>
            <button
              onClick={onLogout}
              className="text-[10px] text-muted hover:text-red-400 transition-smooth"
            >
              Sign out
            </button>
          </div>
          <div className="flex items-center justify-between mt-1.5">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-gain animate-pulse-soft" />
              <span className="text-[10px] text-muted">Live · 60s</span>
            </div>
            <span className="text-[10px] text-surface-lighter">v2.0</span>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-surface p-4 sm:p-6 lg:p-8 pt-16 md:pt-6 lg:pt-8">
        <div className="max-w-7xl mx-auto animate-fade-in" key={location.pathname}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
