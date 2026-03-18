import { NavLink, Outlet } from 'react-router-dom';

const NAV = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/paper-trading', label: 'Paper Trading', icon: '💹' },
  { to: '/forward-testing', label: 'Forward Testing', icon: '🎯' },
  { to: '/multi-portfolio', label: 'Multi-Portfolio', icon: '📈' },
  { to: '/moby', label: 'Moby Analysis', icon: '🐋' },
];

export default function Layout() {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <nav className="w-56 bg-surface-light border-r border-surface-lighter flex-shrink-0 flex flex-col">
        <div className="p-4 border-b border-surface-lighter">
          <h1 className="text-lg font-bold text-white">Stock Planner</h1>
          <p className="text-xs text-muted mt-1">Trading Dashboard</p>
        </div>
        <div className="flex-1 py-2">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-accent/15 text-accent-light font-medium border-l-2 border-accent'
                    : 'text-gray-400 hover:bg-surface-lighter hover:text-gray-200'
                }`
              }
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
        <div className="p-4 border-t border-surface-lighter text-xs text-muted">
          Auto-refresh: 60s
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-surface p-6">
        <Outlet />
      </main>
    </div>
  );
}
