import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import { useAuth } from './hooks/useAuth';
import Login from './pages/Login';
import { PageSkeleton } from './components/Skeleton';

// Eager-load the dashboard (most visited)
import Dashboard from './pages/Dashboard';

// Lazy-load all other pages for code-splitting
const PaperTrading = lazy(() => import('./pages/PaperTrading'));
const ForwardTesting = lazy(() => import('./pages/ForwardTesting'));
const MultiPortfolio = lazy(() => import('./pages/MultiPortfolio'));
const MobyAnalysis = lazy(() => import('./pages/MobyAnalysis'));
const RealtimeMonitoring = lazy(() => import('./pages/RealtimeMonitoring'));
const EarningsCalendar = lazy(() => import('./pages/EarningsCalendar'));
const WatchlistComparison = lazy(() => import('./pages/WatchlistComparison'));
const AlertManagement = lazy(() => import('./pages/AlertManagement'));
const Notifications = lazy(() => import('./pages/Notifications'));
const SignalTracker = lazy(() => import('./pages/SignalTracker'));
const Sentiment = lazy(() => import('./pages/Sentiment'));
const TickerDetail = lazy(() => import('./pages/TickerDetail'));
const WatchlistBrowser = lazy(() => import('./pages/WatchlistBrowser'));
const Settings = lazy(() => import('./pages/Settings'));
const RecommendationTracking = lazy(() => import('./pages/RecommendationTracking'));
const PortfolioOverview = lazy(() => import('./pages/PortfolioOverview'));
const DailyActions = lazy(() => import('./pages/DailyActions'));
const Changelog = lazy(() => import('./pages/Changelog'));

function Page({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageSkeleton />}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
}

export default function App() {
  const { user, loading, error, login, logout } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-surface p-8">
        <PageSkeleton />
      </div>
    );
  }

  if (!user) {
    return <Login onLogin={login} error={error} />;
  }

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout user={user} onLogout={logout} />}>
            <Route index element={<Page><Dashboard /></Page>} />
            <Route path="paper-trading" element={<Page><PaperTrading /></Page>} />
            <Route path="forward-testing" element={<Page><ForwardTesting /></Page>} />
            <Route path="multi-portfolio" element={<Page><MultiPortfolio /></Page>} />
            <Route path="portfolio-overview" element={<Page><PortfolioOverview /></Page>} />
            <Route path="daily-actions" element={<Page><DailyActions /></Page>} />
            <Route path="moby" element={<Page><MobyAnalysis /></Page>} />
            <Route path="realtime-monitoring" element={<Page><RealtimeMonitoring /></Page>} />
            <Route path="earnings-calendar" element={<Page><EarningsCalendar /></Page>} />
            <Route path="watchlist-comparison" element={<Page><WatchlistComparison /></Page>} />
            <Route path="alerts" element={<Page><AlertManagement /></Page>} />
            <Route path="notifications" element={<Page><Notifications /></Page>} />
            <Route path="signals" element={<Page><SignalTracker /></Page>} />
            <Route path="sentiment" element={<Page><Sentiment /></Page>} />
            <Route path="ticker/:ticker" element={<Page><TickerDetail /></Page>} />
            <Route path="watchlists" element={<Page><WatchlistBrowser /></Page>} />
            <Route path="recommendations" element={<Page><RecommendationTracking /></Page>} />
            <Route path="settings" element={<Page><Settings /></Page>} />
            <Route path="changelog" element={<Page><Changelog /></Page>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
