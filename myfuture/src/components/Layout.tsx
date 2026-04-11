import { useState, useEffect, useRef, type ReactNode } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  FlaskConical,
  PieChart,
  PlayCircle,
  Layers,
  Zap,
  List,
  Fish,
  SmilePlus,
  Activity,
  CalendarDays,
  GitCompareArrows,
  ThumbsUp,
  Bell,
  BellRing,
  Settings,
  Menu,
  X,
  MoreHorizontal,
  BookOpen,
} from 'lucide-react';

const NAV_SECTIONS: { label: string; items: { to: string; label: string; icon: ReactNode }[] }[] = [
  {
    label: 'Trading',
    items: [
      { to: '/', label: 'Dashboard', icon: <LayoutDashboard size={16} /> },
      { to: '/paper-trading', label: 'Paper Trading', icon: <FileText size={16} /> },
      { to: '/forward-testing', label: 'Forward Testing', icon: <FlaskConical size={16} /> },
      { to: '/portfolio-overview', label: 'Portfolio P&L', icon: <PieChart size={16} /> },
      { to: '/daily-actions', label: 'Daily Actions', icon: <PlayCircle size={16} /> },
      { to: '/multi-portfolio', label: 'Multi-Portfolio', icon: <Layers size={16} /> },
      { to: '/signals', label: 'Signal Tracker', icon: <Zap size={16} /> },
    ],
  },
  {
    label: 'Analysis',
    items: [
      { to: '/watchlists', label: 'Watchlists', icon: <List size={16} /> },
      { to: '/moby', label: 'Moby Analysis', icon: <Fish size={16} /> },
      { to: '/sentiment', label: 'Sentiment', icon: <SmilePlus size={16} /> },
      { to: '/realtime-monitoring', label: 'Monitoring', icon: <Activity size={16} /> },
      { to: '/earnings-calendar', label: 'Earnings', icon: <CalendarDays size={16} /> },
      { to: '/watchlist-comparison', label: 'Comparison', icon: <GitCompareArrows size={16} /> },
      { to: '/recommendations', label: 'Recommendations', icon: <ThumbsUp size={16} /> },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/alerts', label: 'Alerts', icon: <Bell size={16} /> },
      { to: '/notifications', label: 'Notifications', icon: <BellRing size={16} /> },
      { to: '/settings', label: 'Settings', icon: <Settings size={16} /> },
      { to: '/changelog', label: 'Changelog', icon: <BookOpen size={16} /> },
    ],
  },
];

/** Primary bottom-bar tabs on mobile — these 5 routes get direct access */
const BOTTOM_TABS: { to: string; label: string; icon: ReactNode }[] = [
  { to: '/', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
  { to: '/paper-trading', label: 'Trading', icon: <FileText size={20} /> },
  { to: '/portfolio-overview', label: 'P&L', icon: <PieChart size={20} /> },
  { to: '/daily-actions', label: 'Actions', icon: <PlayCircle size={20} /> },
  { to: '/signals', label: 'Signals', icon: <Zap size={20} /> },
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
      {/* Mobile header — hide hamburger since bottom bar handles primary nav */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-30 bg-surface-light/90 backdrop-blur-md border-b border-surface-lighter px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-accent to-purple flex items-center justify-center">
            <span className="text-[10px] font-bold text-white">mF</span>
          </div>
          <span className="text-sm font-semibold text-white tracking-tight">myFuture</span>
        </div>
        {/* Search on mobile header */}
        <div className="relative flex-1 max-w-[180px] ml-3">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value.toUpperCase())}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && search.trim()) {
                navigate(`/ticker/${search.trim()}`);
                setSearch('');
                searchRef.current?.blur();
              }
            }}
            placeholder="Ticker..."
            className="w-full bg-surface/50 border border-surface-lighter/40 rounded-lg pl-3 pr-2 py-1.5 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-accent/50 min-h-[36px]"
          />
        </div>
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

        {/* Navigation — py-2.5 for better touch targets */}
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
                      `group flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] transition-smooth relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-light ${
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
                        <span className={`flex-shrink-0 ${isActive ? 'text-accent-light' : 'text-gray-600 group-hover:text-gray-400'} transition-smooth`}>
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
            <NavLink to="/changelog" className="text-[10px] text-surface-lighter hover:text-muted transition-smooth">v2.1</NavLink>
          </div>
        </div>
      </nav>

      {/* Main content — extra bottom padding on mobile to clear bottom bar */}
      <main className="flex-1 overflow-auto bg-surface p-4 sm:p-6 lg:p-8 pt-16 md:pt-6 lg:pt-8 pb-24 md:pb-6 lg:pb-8">
        <div className="max-w-7xl mx-auto animate-fade-in" key={location.pathname}>
          <Outlet />
        </div>
      </main>

      {/* Mobile bottom tab bar — visible below md breakpoint */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-surface-light/95 backdrop-blur-md border-t border-surface-lighter">
        <div className="flex items-stretch justify-around">
          {BOTTOM_TABS.map((tab) => {
            const isActive =
              tab.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(tab.to);
            return (
              <NavLink
                key={tab.to}
                to={tab.to}
                className={`flex flex-col items-center justify-center flex-1 min-h-[56px] min-w-[44px] py-1.5 transition-smooth focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-inset ${
                  isActive ? 'text-accent' : 'text-gray-500'
                }`}
              >
                <span className={isActive ? 'text-accent' : 'text-gray-600'}>{tab.icon}</span>
                <span className={`text-[10px] mt-0.5 leading-tight ${isActive ? 'font-semibold' : ''}`}>
                  {tab.label}
                </span>
              </NavLink>
            );
          })}
          {/* More tab — opens sidebar overlay */}
          <button
            onClick={() => setMobileOpen(true)}
            className={`flex flex-col items-center justify-center flex-1 min-h-[56px] min-w-[44px] py-1.5 transition-smooth ${
              mobileOpen ? 'text-accent' : 'text-gray-500'
            }`}
          >
            <MoreHorizontal size={20} className={mobileOpen ? 'text-accent' : 'text-gray-600'} />
            <span className={`text-[10px] mt-0.5 leading-tight ${mobileOpen ? 'font-semibold' : ''}`}>
              More
            </span>
          </button>
        </div>
        {/* Safe area inset for iOS */}
        <div className="h-[env(safe-area-inset-bottom)]" />
      </div>
    </div>
  );
}
