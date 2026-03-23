import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './pages/Dashboard';
import PaperTrading from './pages/PaperTrading';
import ForwardTesting from './pages/ForwardTesting';
import MultiPortfolio from './pages/MultiPortfolio';
import MobyAnalysis from './pages/MobyAnalysis';

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
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
