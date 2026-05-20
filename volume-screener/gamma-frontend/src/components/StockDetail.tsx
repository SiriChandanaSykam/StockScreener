import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    fetchStockAnalysis,
    getChartUrl,
    fetchPatterns,
    fetchSignals,
    type AnalyzedStock,
    type Pattern,
    type SignalsResponse
} from '../services/marketService';

const StockDetail: React.FC = () => {
    const { symbol } = useParams<{ symbol: string }>();
    const navigate = useNavigate();
    const [stock, setStock] = useState<AnalyzedStock | null>(null);
    const [patterns, setPatterns] = useState<Pattern[]>([]);
    const [signals, setSignals] = useState<SignalsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [chartPeriod, setChartPeriod] = useState('3mo');

    useEffect(() => {
        const loadStock = async () => {
            if (!symbol) {
                setError('No symbol provided');
                setLoading(false);
                return;
            }

            setLoading(true);
            setError(null);

            try {
                // Fetch all data in parallel
                const [analysis, patternsData, signalsData] = await Promise.all([
                    fetchStockAnalysis(symbol),
                    fetchPatterns(symbol),
                    fetchSignals(symbol)
                ]);

                if (analysis && !('error' in analysis)) {
                    setStock(analysis);
                } else {
                    setError(`Could not load data for ${symbol}. The stock may not be available.`);
                }

                setPatterns(patternsData);
                setSignals(signalsData);
            } catch (err) {
                setError(`Failed to analyze ${symbol}`);
            }

            setLoading(false);
        };

        loadStock();
    }, [symbol]);

    const getScoreColor = (score: number) => {
        if (score >= 70) return 'text-green-400';
        if (score >= 50) return 'text-yellow-400';
        return 'text-red-400';
    };

    const getScoreBgColor = (score: number) => {
        if (score >= 70) return 'bg-green-500';
        if (score >= 50) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center">
                <div className="text-4xl mb-4">📊</div>
                <div className="text-indigo-400 text-xl mb-2">Analyzing {symbol}...</div>
                <div className="text-gray-500 text-sm">Fetching real market data</div>
                <div className="mt-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                </div>
            </div>
        );
    }

    if (error || !stock) {
        return (
            <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center">
                <div className="text-4xl mb-4">⚠️</div>
                <div className="text-red-400 text-xl mb-2">Error</div>
                <div className="text-gray-500 text-sm mb-4">{error}</div>
                <button
                    onClick={() => navigate('/')}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
                >
                    ← Back to Screener
                </button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-900 text-white">
            {/* Header */}
            <header className="bg-gradient-to-r from-gray-900 via-gray-850 to-gray-900 border-b border-gray-750 sticky top-0 z-50">
                <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => navigate('/')}
                            className="text-gray-400 hover:text-white transition-colors"
                        >
                            ← Back
                        </button>
                        <div>
                            <h1 className="text-2xl font-bold">{stock.symbol}</h1>
                            <p className="text-sm text-gray-500">{stock.name} • {stock.sector}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="text-right">
                            <div className="text-2xl font-bold">₹{stock.price?.toFixed(2)}</div>
                            <div className={`text-lg ${stock.change1d >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {stock.change1d >= 0 ? '+' : ''}{stock.change1d?.toFixed(2)}% today
                            </div>
                        </div>
                        <div className={`px-4 py-2 rounded-lg ${getScoreBgColor(stock.compositeScore)} text-white font-bold text-xl`}>
                            {stock.compositeScore?.toFixed(0)}
                        </div>
                    </div>
                </div>
            </header>

            <main className="container mx-auto px-4 py-6">
                {/* Chart Section - Full Width */}
                <div className="bg-gray-850 rounded-lg border border-gray-750 overflow-hidden mb-6">
                    <div className="flex items-center justify-between p-4 border-b border-gray-750">
                        <h2 className="text-lg font-bold">📈 TradingView Chart</h2>
                        <div className="flex gap-2">
                            {['1mo', '3mo', '6mo', '1y'].map(p => (
                                <button
                                    key={p}
                                    onClick={() => setChartPeriod(p)}
                                    className={`px-4 py-2 text-sm rounded-lg transition-colors ${chartPeriod === p
                                        ? 'bg-indigo-600 text-white'
                                        : 'bg-gray-800 text-gray-400 hover:text-white'
                                        }`}
                                >
                                    {p.toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>
                    <iframe
                        key={`${stock.symbol}-${chartPeriod}`}
                        src={`${getChartUrl(stock.symbol, chartPeriod)}&t=${Date.now()}`}
                        className="w-full border-0"
                        style={{ height: '600px' }}
                        title={`${stock.symbol} Chart`}
                    />
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    {/* Price Stats */}
                    <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                        <h3 className="text-sm text-gray-500 mb-3">Price Performance</h3>
                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <span className="text-gray-400">1 Day</span>
                                <span className={stock.change1d >= 0 ? 'text-green-400' : 'text-red-400'}>
                                    {stock.change1d >= 0 ? '+' : ''}{stock.change1d?.toFixed(2)}%
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-400">5 Days</span>
                                <span className={stock.change5d >= 0 ? 'text-green-400' : 'text-red-400'}>
                                    {stock.change5d >= 0 ? '+' : ''}{stock.change5d?.toFixed(2)}%
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-400">20 Days</span>
                                <span className={stock.change20d >= 0 ? 'text-green-400' : 'text-red-400'}>
                                    {stock.change20d >= 0 ? '+' : ''}{stock.change20d?.toFixed(2)}%
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-400">3 Months</span>
                                <span className={stock.change3m >= 0 ? 'text-green-400' : 'text-red-400'}>
                                    {stock.change3m >= 0 ? '+' : ''}{stock.change3m?.toFixed(2)}%
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Technical Indicators */}
                    <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                        <h3 className="text-sm text-gray-500 mb-3">Technical Indicators</h3>
                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <span className="text-gray-400">RSI (14)</span>
                                <span className={stock.rsi < 30 ? 'text-green-400' : stock.rsi > 70 ? 'text-red-400' : 'text-gray-300'}>
                                    {stock.rsi?.toFixed(1)}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-400">MACD</span>
                                <span className={stock.macdSignal === 'BUY' || stock.macdSignal === 'BULLISH' ? 'text-green-400' : 'text-red-400'}>
                                    {stock.macdSignal}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-400">RVOL</span>
                                <span className={stock.rvol > 2 ? 'text-green-400' : 'text-gray-300'}>
                                    {stock.rvol?.toFixed(2)}x
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-400">52W High</span>
                                <span className={stock.pctFrom52wHigh >= -5 ? 'text-green-400' : 'text-gray-300'}>
                                    {stock.pctFrom52wHigh?.toFixed(1)}%
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* SMA Status */}
                    <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                        <h3 className="text-sm text-gray-500 mb-3">Moving Averages</h3>
                        <div className="space-y-2">
                            <div className="flex justify-between items-center">
                                <span className="text-gray-400">Above SMA20</span>
                                <span className={stock.aboveSma20 ? 'text-green-400' : 'text-red-400'}>
                                    {stock.aboveSma20 ? '✓ Yes' : '✗ No'}
                                </span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-gray-400">Above SMA50</span>
                                <span className={stock.aboveSma50 ? 'text-green-400' : 'text-red-400'}>
                                    {stock.aboveSma50 ? '✓ Yes' : '✗ No'}
                                </span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-gray-400">Above SMA200</span>
                                <span className={stock.aboveSma200 ? 'text-green-400' : 'text-red-400'}>
                                    {stock.aboveSma200 ? '✓ Yes' : '✗ No'}
                                </span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-gray-400">Near Breakout</span>
                                <span className={stock.nearBreakout ? 'text-green-400' : 'text-gray-400'}>
                                    {stock.nearBreakout ? '🎯 Yes' : 'No'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Score Breakdown */}
                    <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                        <h3 className="text-sm text-gray-500 mb-3">Score Breakdown</h3>
                        <div className="space-y-3">
                            {[
                                { label: 'Momentum', score: stock.momentumScore, icon: '🚀' },
                                { label: 'Volume', score: stock.volumeScore, icon: '📊' },
                                { label: 'Technical', score: stock.technicalScore, icon: '📈' },
                                { label: 'Trend', score: stock.trendScore, icon: '🎯' },
                            ].map(item => (
                                <div key={item.label} className="flex items-center gap-2">
                                    <span>{item.icon}</span>
                                    <span className="text-sm text-gray-400 w-16">{item.label}</span>
                                    <div className="flex-1 bg-gray-700 rounded-full h-2">
                                        <div
                                            className={`h-2 rounded-full ${getScoreBgColor(item.score)}`}
                                            style={{ width: `${item.score}%` }}
                                        />
                                    </div>
                                    <span className={`text-sm font-mono w-8 ${getScoreColor(item.score)}`}>
                                        {item.score?.toFixed(0)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Signals and Analysis */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {/* Candlestick Patterns */}
                    <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                        <h3 className="text-lg font-bold mb-4">🕯️ Candlestick Patterns</h3>
                        {patterns.length > 0 ? (
                            <div className="space-y-2">
                                {patterns.map((pattern, idx) => (
                                    <div
                                        key={idx}
                                        className={`p-3 rounded-lg flex items-center justify-between ${pattern.bias === 'bullish' ? 'bg-green-500/10 border border-green-500/30' :
                                            pattern.bias === 'bearish' ? 'bg-red-500/10 border border-red-500/30' :
                                                'bg-gray-800 border border-gray-700'
                                            }`}
                                    >
                                        <span className="font-medium">{pattern.name}</span>
                                        <span className={`px-2 py-1 text-xs rounded ${pattern.signal === 'BUY' ? 'bg-green-500/20 text-green-400' :
                                            pattern.signal === 'SELL' ? 'bg-red-500/20 text-red-400' :
                                                'bg-gray-500/20 text-gray-400'
                                            }`}>
                                            {pattern.signal}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-4 text-gray-500">
                                <p>No patterns detected</p>
                                <p className="text-xs mt-1">in the last 10 candles</p>
                            </div>
                        )}
                    </div>

                    {/* Strategy Signals */}
                    <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                        <h3 className="text-lg font-bold mb-4">📊 Strategy Signals</h3>
                        {signals && signals.signals && signals.signals.length > 0 ? (
                            <>
                                <div className={`text-center p-3 rounded-lg mb-4 ${signals.overallSignal === 'BUY' ? 'bg-green-500/20' :
                                    signals.overallSignal === 'SELL' ? 'bg-red-500/20' :
                                        'bg-gray-800'
                                    }`}>
                                    <span className="text-sm text-gray-400">Overall Signal</span>
                                    <div className={`text-xl font-bold ${signals.overallSignal === 'BUY' ? 'text-green-400' :
                                        signals.overallSignal === 'SELL' ? 'text-red-400' :
                                            'text-gray-400'
                                        }`}>
                                        {signals.overallSignal}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">
                                        {signals.buyVotes} Buy • {signals.sellVotes} Sell
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    {signals.signals.map((sig, idx) => (
                                        <div key={idx} className="p-3 bg-gray-800 rounded-lg">
                                            <div className="flex justify-between items-center mb-1">
                                                <span className="font-medium text-sm">{sig.strategy}</span>
                                                <span className={`px-2 py-0.5 text-xs rounded ${sig.signal === 'BUY' ? 'bg-green-500/20 text-green-400' :
                                                    'bg-red-500/20 text-red-400'
                                                    }`}>
                                                    {sig.signal}
                                                </span>
                                            </div>
                                            <p className="text-xs text-gray-500">{sig.reason}</p>
                                        </div>
                                    ))}
                                </div>
                            </>
                        ) : (
                            <div className="text-center py-4 text-gray-500">
                                <p>No active signals</p>
                                <p className="text-xs mt-1">Market is neutral</p>
                            </div>
                        )}
                    </div>

                    {/* Analysis Summary */}
                    <div className="bg-gray-850 rounded-lg border border-gray-750 p-4">
                        <h3 className="text-lg font-bold mb-4">📝 Analysis Summary</h3>
                        <div className="p-4 bg-gray-800 rounded-lg">
                            <div className="flex items-center gap-3 mb-3">
                                <div className={`px-3 py-1 rounded-lg ${getScoreBgColor(stock.compositeScore)} text-white font-bold`}>
                                    Score: {stock.compositeScore?.toFixed(0)}
                                </div>
                                <span className="text-gray-400">out of 100</span>
                            </div>
                            <p className="text-gray-300 mb-4">{stock.analysis}</p>

                            {/* Show stock.signals if any */}
                            {stock.signals && stock.signals.length > 0 && (
                                <div className="pt-3 border-t border-gray-700">
                                    <div className="text-sm text-gray-500 mb-2">Quick Signals:</div>
                                    <div className="flex flex-wrap gap-2">
                                        {stock.signals.slice(0, 4).map((sig, idx) => (
                                            <span key={idx} className="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-1 rounded">
                                                {sig}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default StockDetail;
