import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import { useAuth } from './hooks/useAuth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import PaperTrading from './pages/PaperTrading';
import ForwardTesting from './pages/ForwardTesting';
import MultiPortfolio from './pages/MultiPortfolio';
import MobyAnalysis from './pages/MobyAnalysis';

export default function App() {
  const { user, loading, error, login, logout } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-muted text-sm">Loading...</div>
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
            <Route index element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
            <Route path="paper-trading" element={<ErrorBoundary><PaperTrading /></ErrorBoundary>} />
            <Route path="forward-testing" element={<ErrorBoundary><ForwardTesting /></ErrorBoundary>} />
            <Route path="multi-portfolio" element={<ErrorBoundary><MultiPortfolio /></ErrorBoundary>} />
            <Route path="moby" element={<ErrorBoundary><MobyAnalysis /></ErrorBoundary>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
