import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import StockDetail from './components/StockDetail';
import NewsFeed from './components/NewsFeed';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/stock/:symbol" element={<StockDetail />} />
        <Route path="/news" element={<NewsFeed />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
