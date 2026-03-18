import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import PaperTrading from './pages/PaperTrading';
import ForwardTesting from './pages/ForwardTesting';
import MultiPortfolio from './pages/MultiPortfolio';
import MobyAnalysis from './pages/MobyAnalysis';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="paper-trading" element={<PaperTrading />} />
          <Route path="forward-testing" element={<ForwardTesting />} />
          <Route path="multi-portfolio" element={<MultiPortfolio />} />
          <Route path="moby" element={<MobyAnalysis />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
