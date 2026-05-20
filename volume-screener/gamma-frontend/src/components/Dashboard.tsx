import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import type { NewsItem } from '../types';
import {
    fetchAnalyzedStocks,
    fetchNewsAnalysis,
    fetchTopPredictions,
    searchSymbols,
    fetchSectors,
    analyzeSector,
    getChartUrl,
    type AnalyzedStock,
    type SearchResult,
    type Sector
} from '../services/marketService';

type TabView = 'nifty50' | 'sectors' | 'search' | 'news';

const Dashboard: React.FC = () => {
    const navigate = useNavigate();

    // Main state
    const [stocks, setStocks] = useState<AnalyzedStock[]>([]);
    const [news, setNews] = useState<NewsItem[]>([]);
    const [selectedStock, setSelectedStock] = useState<AnalyzedStock | null>(null);
    const [loading, setLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState('');
    const [view, setView] = useState<TabView>('nifty50');
    const [aiPredictions, setAiPredictions] = useState<any[]>([]);
    const [chartPeriod, setChartPeriod] = useState('3mo');

    // Search state
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [searchLoading, setSearchLoading] = useState(false);

    // Sector state
    const [sectors, setSectors] = useState<Sector[]>([]);
    const [selectedSector, setSelectedSector] = useState<string | null>(null);
    const [sectorLoading, setSectorLoading] = useState(false);

    // Sort state
    type SortKey = 'rank' | 'symbol' | 'price' | 'change1d' | 'change5d' | 'rsi' | 'macdSignal' | 'compositeScore';
    type SortOrder = 'asc' | 'desc';
    const [sortKey, setSortKey] = useState<SortKey>('compositeScore');
    const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(key);
            setSortOrder('desc');
        }
    };

    const sortedStocks = useMemo(() => {
        return [...stocks].sort((a, b) => {
            let aVal: any, bVal: any;
            switch (sortKey) {
                case 'symbol': aVal = a.symbol; bVal = b.symbol; break;
                case 'price': aVal = a.price || 0; bVal = b.price || 0; break;
                case 'change1d': aVal = a.change1d || 0; bVal = b.change1d || 0; break;
                case 'change5d': aVal = a.change5d || 0; bVal = b.change5d || 0; break;
                case 'rsi': aVal = a.rsi || 50; bVal = b.rsi || 50; break;
                case 'macdSignal':
                    const signalOrder = { 'BULLISH': 2, 'BUY': 2, 'NEUTRAL': 1, 'BEARISH': 0, 'SELL': 0 };
                    aVal = signalOrder[a.macdSignal as keyof typeof signalOrder] ?? 1;
                    bVal = signalOrder[b.macdSignal as keyof typeof signalOrder] ?? 1;
                    break;
                case 'compositeScore': aVal = a.compositeScore || 0; bVal = b.compositeScore || 0; break;
                case 'rank': aVal = a.rank || 999; bVal = b.rank || 999; break;
                default: return 0;
            }
            if (typeof aVal === 'string') {
                return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }
            return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
        });
    }, [stocks, sortKey, sortOrder]);

    const SortIcon = ({ columnKey }: { columnKey: SortKey }) => {
        if (sortKey !== columnKey) return <span className="ml-1 opacity-30">↕</span>;
        return sortOrder === 'desc'
            ? <span className="ml-1 text-indigo-400">↓</span>
            : <span className="ml-1 text-indigo-400">↑</span>;
    };

    // Load Nifty 50 on initial mount (only Nifty 50 - fast!)
    useEffect(() => {
        const loadInitialData = async () => {
            setLoading(true);
            setLoadingMessage('🔍 Loading Nifty 50 stocks...');

            try {
                const [analyzedData, newsData, predictions, sectorsData] = await Promise.all([
                    fetchAnalyzedStocks(50, true, 50),  // Nifty 50 only
                    fetchNewsAnalysis(),
                    fetchTopPredictions(5),
                    fetchSectors()  // Load sector list (fast, no analysis)
                ]);

                setStocks(analyzedData);
                setNews(newsData);
                setAiPredictions(predictions);
                setSectors(sectorsData);

                if (analyzedData.length > 0) {
                    setSelectedStock(analyzedData[0]);
                }
            } catch (error) {
                console.error('Failed to load data:', error);
            }

            setLoading(false);
        };
        loadInitialData();
    }, []);

    // Handle sector click - load stocks for that sector
    const handleSectorClick = async (sectorName: string) => {
        setSelectedSector(sectorName);
        setSectorLoading(true);
        setLoadingMessage(`📊 Analyzing ${sectorName} stocks...`);

        try {
            const sectorStocks = await analyzeSector(sectorName, 30);
            setStocks(sectorStocks);
            if (sectorStocks.length > 0) {
                setSelectedStock(sectorStocks[0]);
            }
        } catch (error) {
            console.error(`Failed to analyze sector ${sectorName}:`, error);
        }

        setSectorLoading(false);
    };

    // Handle "Back to Nifty 50" button
    const handleBackToNifty = async () => {
        setSelectedSector(null);
        setView('nifty50');
        setLoading(true);
        setLoadingMessage('🔍 Loading Nifty 50 stocks...');

        try {
            const analyzedData = await fetchAnalyzedStocks(50, true, 50);
            setStocks(analyzedData);
            if (analyzedData.length > 0) {
                setSelectedStock(analyzedData[0]);
            }
        } catch (error) {
            console.error('Failed to load Nifty 50:', error);
        }

        setLoading(false);
    };

    // Search handler
    const handleSearch = useCallback(async (query: string) => {
        setSearchQuery(query);

        if (query.length < 2) {
            setSearchResults([]);
            return;
        }

        setSearchLoading(true);
        const results = await searchSymbols(query, 30);
        setSearchResults(results);
        setSearchLoading(false);
    }, []);

    const getScoreColor = (score: number) => {
        if (score >= 70) return 'text-green-400';
        if (score >= 50) return 'text-yellow-400';
        return 'text-red-400';
    };

    const getSignalBadge = (macdSignal: string) => {
        const colors: Record<string, string> = {
            'BUY': 'bg-green-500/20 text-green-400 border-green-500/50',
            'SELL': 'bg-red-500/20 text-red-400 border-red-500/50',
            'BULLISH': 'bg-green-500/10 text-green-300 border-green-500/30',
            'BEARISH': 'bg-red-500/10 text-red-300 border-red-500/30',
            'NEUTRAL': 'bg-gray-500/20 text-gray-400 border-gray-500/50',
        };
        return colors[macdSignal] || colors['NEUTRAL'];
    };

    // Loading state
    if (loading) {
        return (
            <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center">
                <div className="text-4xl mb-4">🔍</div>
                <div className="text-indigo-400 text-xl mb-2">Loading...</div>
                <div className="text-gray-500 text-sm text-center whitespace-pre-line max-w-md">
                    {loadingMessage}
                </div>
                <div className="mt-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-900 text-white">
            {/* Header */}
            <header className="bg-gradient-to-r from-gray-900 via-gray-850 to-gray-900 border-b border-gray-750 sticky top-0 z-50">
                <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <span className="text-2xl">🚀</span>
                        <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 text-transparent bg-clip-text">
                            Gamma Screener
                        </h1>
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
                            LIVE DATA
                        </span>
                    </div>

                    <div className="flex items-center gap-4">
                        {selectedSector && (
                            <button
                                onClick={handleBackToNifty}
                                className="px-3 py-1.5 bg-gray-800 text-gray-300 text-sm rounded-lg hover:bg-gray-700"
                            >
                                ← Back to Nifty 50
                            </button>
                        )}
                        <div className="text-sm text-gray-500">
                            📊 {stocks.length} stocks
                            {selectedSector && <span className="text-indigo-400"> • {selectedSector}</span>}
                        </div>
                    </div>
                </div>

                {/* Tab Navigation */}
                <div className="container mx-auto px-4 flex gap-4 border-t border-gray-800">
                    {[
                        { id: 'nifty50', label: '📈 Nifty 50', icon: '📈' },
                        { id: 'sectors', label: '🏢 Sectors', icon: '🏢' },
                        { id: 'search', label: '🔍 Search', icon: '🔍' },
                        { id: 'news', label: '📰 News', icon: '📰' },
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => {
                                if (tab.id === 'news') {
                                    navigate('/news');
                                } else {
                                    setView(tab.id as TabView);
                                }
                            }}
                            className={`py-3 px-4 text-sm font-medium border-b-2 transition-all ${view === tab.id
                                ? 'border-indigo-500 text-indigo-400'
                                : 'border-transparent text-gray-500 hover:text-gray-300'
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </header>

            {/* Main Content */}
            <main className="container mx-auto px-4 py-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Main Content Area */}
                    <div className="lg:col-span-2">

                        {/* SECTORS VIEW */}
                        {view === 'sectors' && (
                            <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                                <h2 className="text-lg font-bold mb-4">🏢 Browse by Sector</h2>
                                <p className="text-sm text-gray-500 mb-4">Click a sector to analyze its stocks</p>

                                {sectorLoading ? (
                                    <div className="flex items-center justify-center py-8">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mr-3"></div>
                                        <span className="text-gray-400">{loadingMessage}</span>
                                    </div>
                                ) : selectedSector ? (
                                    // Show sector stocks
                                    <div>
                                        <div className="flex items-center justify-between mb-4">
                                            <h3 className="text-lg font-bold text-indigo-400">{selectedSector}</h3>
                                            <button
                                                onClick={() => setSelectedSector(null)}
                                                className="text-sm text-gray-400 hover:text-white"
                                            >
                                                ← Back to sectors
                                            </button>
                                        </div>

                                        <div className="overflow-x-auto">
                                            <table className="w-full">
                                                <thead className="bg-gray-800/50 text-gray-400 text-xs uppercase">
                                                    <tr>
                                                        <th className="px-4 py-3 text-left cursor-pointer hover:text-indigo-400" onClick={() => handleSort('rank')}>
                                                            #<SortIcon columnKey="rank" />
                                                        </th>
                                                        <th className="px-4 py-3 text-left cursor-pointer hover:text-indigo-400" onClick={() => handleSort('symbol')}>
                                                            Symbol<SortIcon columnKey="symbol" />
                                                        </th>
                                                        <th className="px-4 py-3 text-right cursor-pointer hover:text-indigo-400" onClick={() => handleSort('price')}>
                                                            Price<SortIcon columnKey="price" />
                                                        </th>
                                                        <th className="px-4 py-3 text-right cursor-pointer hover:text-indigo-400" onClick={() => handleSort('change1d')}>
                                                            1D<SortIcon columnKey="change1d" />
                                                        </th>
                                                        <th className="px-4 py-3 text-center cursor-pointer hover:text-indigo-400" onClick={() => handleSort('rsi')}>
                                                            RSI<SortIcon columnKey="rsi" />
                                                        </th>
                                                        <th className="px-4 py-3 text-right cursor-pointer hover:text-indigo-400" onClick={() => handleSort('compositeScore')}>
                                                            Score<SortIcon columnKey="compositeScore" />
                                                        </th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-gray-750">
                                                    {sortedStocks.map((stock, idx) => (
                                                        <tr
                                                            key={stock.symbol}
                                                            onClick={() => navigate(`/stock/${stock.symbol}`)}
                                                            className="hover:bg-gray-800/50 cursor-pointer transition-colors"
                                                        >
                                                            <td className="px-4 py-3 text-gray-500 text-sm">{idx + 1}</td>
                                                            <td className="px-4 py-3">
                                                                <div className="font-bold">{stock.symbol}</div>
                                                                <div className="text-xs text-gray-500">{stock.name?.slice(0, 20)}</div>
                                                            </td>
                                                            <td className="px-4 py-3 text-right font-mono">₹{stock.price?.toFixed(2)}</td>
                                                            <td className={`px-4 py-3 text-right font-mono ${stock.change1d >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                {stock.change1d >= 0 ? '+' : ''}{stock.change1d?.toFixed(1)}%
                                                            </td>
                                                            <td className="px-4 py-3 text-center">
                                                                <span className={`${stock.rsi < 30 ? 'text-green-400' : stock.rsi > 70 ? 'text-red-400' : 'text-gray-400'}`}>
                                                                    {stock.rsi?.toFixed(0)}
                                                                </span>
                                                            </td>
                                                            <td className={`px-4 py-3 text-right font-bold ${getScoreColor(stock.compositeScore)}`}>
                                                                {stock.compositeScore?.toFixed(0)}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                ) : (
                                    // Show sector grid
                                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                        {sectors.map(sector => (
                                            <button
                                                key={sector.name}
                                                onClick={() => handleSectorClick(sector.name)}
                                                className="p-4 bg-gray-800 rounded-lg border border-gray-700 hover:border-indigo-500 hover:bg-gray-750 transition-all text-left"
                                            >
                                                <div className="font-bold text-white mb-1">{sector.name}</div>
                                                <div className="text-sm text-gray-400">{sector.count} stocks</div>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* SEARCH VIEW */}
                        {view === 'search' && (
                            <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                                <h2 className="text-lg font-bold mb-4">🔍 Search Any Stock</h2>

                                <div className="relative mb-4">
                                    <input
                                        type="text"
                                        value={searchQuery}
                                        onChange={(e) => handleSearch(e.target.value)}
                                        placeholder="Search by symbol or company name..."
                                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                                    />
                                    {searchLoading && (
                                        <div className="absolute right-3 top-3">
                                            <div className="animate-spin h-5 w-5 border-2 border-indigo-500 border-t-transparent rounded-full"></div>
                                        </div>
                                    )}
                                </div>

                                {searchResults.length > 0 ? (
                                    <div className="space-y-2 max-h-96 overflow-y-auto">
                                        {searchResults.map((result) => (
                                            <div
                                                key={result.symbol}
                                                className="flex items-center justify-between p-3 bg-gray-800 rounded-lg hover:bg-gray-750 transition-colors"
                                            >
                                                <div>
                                                    <div className="font-bold text-white">{result.symbol}</div>
                                                    <div className="text-sm text-gray-400">{result.name}</div>
                                                    <div className="text-xs text-gray-500">{result.sector}</div>
                                                </div>
                                                <button
                                                    onClick={() => navigate(`/stock/${result.symbol}`)}
                                                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg transition-colors"
                                                >
                                                    📊 View
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                ) : searchQuery.length >= 2 && !searchLoading ? (
                                    <div className="text-center py-8 text-gray-500">
                                        <p>No stocks found for "{searchQuery}"</p>
                                    </div>
                                ) : (
                                    <div className="text-center py-8 text-gray-500">
                                        <p className="text-lg mb-2">🔎 Search 4,000+ Indian stocks</p>
                                        <p className="text-sm">Type at least 2 characters to search</p>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* NIFTY 50 VIEW (Default Analysis View) */}
                        {view === 'nifty50' && (
                            <div className="bg-gray-850 rounded-lg border border-gray-750 overflow-hidden">
                                <div className="p-4 border-b border-gray-750">
                                    <h2 className="text-lg font-bold">🏆 Nifty 50 - Top Performers</h2>
                                    <p className="text-sm text-gray-500">Ranked by composite score (momentum + volume + technicals + trend)</p>
                                </div>

                                <div className="overflow-x-auto">
                                    <table className="w-full">
                                        <thead className="bg-gray-800/50 text-gray-400 text-xs uppercase">
                                            <tr>
                                                <th className="px-4 py-3 text-left cursor-pointer hover:text-indigo-400" onClick={() => handleSort('rank')}>
                                                    #<SortIcon columnKey="rank" />
                                                </th>
                                                <th className="px-4 py-3 text-left cursor-pointer hover:text-indigo-400" onClick={() => handleSort('symbol')}>
                                                    Symbol<SortIcon columnKey="symbol" />
                                                </th>
                                                <th className="px-4 py-3 text-right cursor-pointer hover:text-indigo-400" onClick={() => handleSort('price')}>
                                                    Price<SortIcon columnKey="price" />
                                                </th>
                                                <th className="px-4 py-3 text-right cursor-pointer hover:text-indigo-400" onClick={() => handleSort('change1d')}>
                                                    1D<SortIcon columnKey="change1d" />
                                                </th>
                                                <th className="px-4 py-3 text-right cursor-pointer hover:text-indigo-400" onClick={() => handleSort('change5d')}>
                                                    5D<SortIcon columnKey="change5d" />
                                                </th>
                                                <th className="px-4 py-3 text-center cursor-pointer hover:text-indigo-400" onClick={() => handleSort('rsi')}>
                                                    RSI<SortIcon columnKey="rsi" />
                                                </th>
                                                <th className="px-4 py-3 text-center cursor-pointer hover:text-indigo-400" onClick={() => handleSort('macdSignal')}>
                                                    MACD<SortIcon columnKey="macdSignal" />
                                                </th>
                                                <th className="px-4 py-3 text-right cursor-pointer hover:text-indigo-400" onClick={() => handleSort('compositeScore')}>
                                                    Score<SortIcon columnKey="compositeScore" />
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-750">
                                            {sortedStocks.map((stock, idx) => (
                                                <tr
                                                    key={stock.symbol}
                                                    onClick={() => navigate(`/stock/${stock.symbol}`)}
                                                    className="hover:bg-gray-800/50 cursor-pointer transition-colors"
                                                >
                                                    <td className="px-4 py-3 text-gray-500 text-sm">{stock.rank}</td>
                                                    <td className="px-4 py-3">
                                                        <div className="font-bold">{stock.symbol}</div>
                                                        <div className="text-xs text-gray-500">{stock.sector}</div>
                                                    </td>
                                                    <td className="px-4 py-3 text-right font-mono">₹{stock.price?.toFixed(2)}</td>
                                                    <td className={`px-4 py-3 text-right font-mono ${stock.change1d >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {stock.change1d >= 0 ? '+' : ''}{stock.change1d?.toFixed(1)}%
                                                    </td>
                                                    <td className={`px-4 py-3 text-right font-mono ${stock.change5d >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {stock.change5d >= 0 ? '+' : ''}{stock.change5d?.toFixed(1)}%
                                                    </td>
                                                    <td className="px-4 py-3 text-center">
                                                        <span className={`${stock.rsi < 30 ? 'text-green-400' : stock.rsi > 70 ? 'text-red-400' : 'text-gray-400'}`}>
                                                            {stock.rsi?.toFixed(0)}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-center">
                                                        <span className={`px-2 py-0.5 text-xs rounded border ${getSignalBadge(stock.macdSignal)}`}>
                                                            {stock.macdSignal}
                                                        </span>
                                                    </td>
                                                    <td className={`px-4 py-3 text-right font-bold ${getScoreColor(stock.compositeScore)}`}>
                                                        {stock.compositeScore?.toFixed(0)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* NEWS VIEW */}
                        {view === 'news' && (
                            <div className="space-y-4">
                                {news.map(item => (
                                    <div key={item.id} className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                                        <div className="flex justify-between items-start mb-2">
                                            <span className="text-xs text-gray-500">{item.source} • {item.timestamp}</span>
                                            <span className={`px-2 py-0.5 text-xs rounded ${item.impact === 'HIGH' ? 'bg-red-500/20 text-red-400' :
                                                item.impact === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' :
                                                    'bg-gray-500/20 text-gray-400'
                                                }`}>
                                                {item.impact}
                                            </span>
                                        </div>
                                        <h3 className="font-bold text-gray-200 mb-2">{item.title}</h3>
                                        <p className="text-sm text-gray-400">{item.summary}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Sidebar */}
                    <div className="lg:col-span-1 space-y-6">
                        {/* Selected Stock Details with Chart */}
                        {selectedStock && (
                            <div className="bg-gray-850 rounded-lg border border-gray-750 overflow-hidden">
                                <div className="p-4 border-b border-gray-750">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h3 className="text-xl font-bold">{selectedStock.symbol}</h3>
                                            <p className="text-sm text-gray-500">{selectedStock.name}</p>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-xl font-bold">₹{selectedStock.price?.toFixed(2)}</div>
                                            <div className={`text-sm ${selectedStock.change1d >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {selectedStock.change1d >= 0 ? '+' : ''}{selectedStock.change1d?.toFixed(2)}%
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* TradingView Chart */}
                                <div className="border-b border-gray-750">
                                    <div className="flex gap-2 p-2 bg-gray-800/50">
                                        {['1mo', '3mo', '6mo', '1y'].map(p => (
                                            <button
                                                key={p}
                                                onClick={() => setChartPeriod(p)}
                                                className={`px-3 py-1 text-xs rounded ${chartPeriod === p ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
                                            >
                                                {p.toUpperCase()}
                                            </button>
                                        ))}
                                    </div>
                                    <iframe
                                        key={`${selectedStock.symbol}-${chartPeriod}`}
                                        src={`${getChartUrl(selectedStock.symbol, chartPeriod)}&t=${Date.now()}`}
                                        className="w-full h-80 border-0"
                                        title={`${selectedStock.symbol} Chart`}
                                    />
                                </div>

                                {/* Score Breakdown */}
                                <div className="p-4 space-y-3">
                                    <h4 className="font-bold text-gray-300">Score Breakdown</h4>
                                    {[
                                        { label: 'Momentum', score: selectedStock.momentumScore, icon: '🚀' },
                                        { label: 'Volume', score: selectedStock.volumeScore, icon: '📊' },
                                        { label: 'Technical', score: selectedStock.technicalScore, icon: '📈' },
                                        { label: 'Trend', score: selectedStock.trendScore, icon: '🎯' },
                                    ].map(item => (
                                        <div key={item.label} className="flex items-center gap-2">
                                            <span>{item.icon}</span>
                                            <span className="text-sm text-gray-400 w-20">{item.label}</span>
                                            <div className="flex-1 bg-gray-700 rounded-full h-2">
                                                <div
                                                    className={`h-2 rounded-full ${item.score >= 70 ? 'bg-green-500' : item.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                                    style={{ width: `${item.score}%` }}
                                                />
                                            </div>
                                            <span className={`text-sm font-mono w-8 ${getScoreColor(item.score)}`}>{item.score?.toFixed(0)}</span>
                                        </div>
                                    ))}

                                    <div className="pt-2 border-t border-gray-700">
                                        <div className="flex items-center justify-between">
                                            <span className="font-bold">Composite Score</span>
                                            <span className={`text-2xl font-bold ${getScoreColor(selectedStock.compositeScore)}`}>
                                                {selectedStock.compositeScore?.toFixed(0)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* AI Predictions */}
                        <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                            <h3 className="text-lg font-bold text-gray-200 mb-4 flex items-center gap-2">
                                <span>🧠</span> AI Predictions
                            </h3>
                            <div className="space-y-3">
                                {aiPredictions.map((pred, idx) => (
                                    <div key={idx} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="font-bold text-indigo-400">{pred.symbol}</span>
                                            <span className={`text-sm font-bold ${pred.upside > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {pred.upside > 0 ? '+' : ''}{pred.upside?.toFixed(1)}%
                                            </span>
                                        </div>
                                        <div className="text-xs text-gray-400">
                                            Target: ₹{pred.predictedClose?.toFixed(2)}
                                        </div>
                                        <div className="text-xs text-gray-500 mt-1">
                                            Confidence: {(pred.confidence * 100)?.toFixed(0)}%
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default Dashboard;
