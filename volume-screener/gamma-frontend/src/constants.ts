import { StrategyType } from './types';

export const SYMBOLS_UNIVERSE = [
    { symbol: 'RELIANCE', name: 'Reliance Industries', sector: 'Energy' },
    { symbol: 'HDFCBANK', name: 'HDFC Bank', sector: 'Financials' },
    { symbol: 'INFY', name: 'Infosys', sector: 'Technology' },
    { symbol: 'TCS', name: 'Tata Consultancy Svcs', sector: 'Technology' },
    { symbol: 'ICICIBANK', name: 'ICICI Bank', sector: 'Financials' },
    { symbol: 'ITC', name: 'ITC Limited', sector: 'Consumer Goods' },
    { symbol: 'SBIN', name: 'State Bank of India', sector: 'Financials' },
    { symbol: 'BHARTIARTL', name: 'Bharti Airtel', sector: 'Telecom' },
    { symbol: 'LICI', name: 'LIC India', sector: 'Financials' },
    { symbol: 'TATAMOTORS', name: 'Tata Motors', sector: 'Auto' },
    { symbol: 'ADANIENT', name: 'Adani Enterprises', sector: 'Metals & Mining' },
    { symbol: 'BAJFINANCE', name: 'Bajaj Finance', sector: 'Financials' },
    { symbol: 'MARUTI', name: 'Maruti Suzuki', sector: 'Auto' },
    { symbol: 'SUNPHARMA', name: 'Sun Pharma', sector: 'Healthcare' },
    { symbol: 'AXISBANK', name: 'Axis Bank', sector: 'Financials' }
];

export const AVAILABLE_STRATEGIES = [
    StrategyType.MOMENTUM_BREAKOUT,
    StrategyType.GAP_AND_GO,
    StrategyType.VWAP_EMA_TREND,
    StrategyType.PULLBACK,
    StrategyType.REVERSAL_RSI,
    StrategyType.VOLUME_SPIKE,
    StrategyType.SECTOR_ALIGNMENT
];

export const STRATEGY_META: Record<string, { style: string, winRateBias: 'HIGH' | 'MEDIUM' | 'BOOSTER', riskAdjustedBias: 'HIGH' | 'MEDIUM' | 'BOOSTER' }> = {
    [StrategyType.REVERSAL_RSI]: {
        style: 'Mean Reversion',
        winRateBias: 'HIGH',
        riskAdjustedBias: 'MEDIUM'
    },
    [StrategyType.VWAP_EMA_TREND]: {
        style: 'Trend',
        winRateBias: 'HIGH',
        riskAdjustedBias: 'HIGH'
    },
    [StrategyType.PULLBACK]: {
        style: 'Trend',
        winRateBias: 'HIGH',
        riskAdjustedBias: 'HIGH'
    },
    [StrategyType.SECTOR_ALIGNMENT]: {
        style: 'Filter',
        winRateBias: 'BOOSTER',
        riskAdjustedBias: 'BOOSTER'
    },
    [StrategyType.MOMENTUM_BREAKOUT]: {
        style: 'Momentum',
        winRateBias: 'MEDIUM',
        riskAdjustedBias: 'HIGH'
    },
    [StrategyType.GAP_AND_GO]: {
        style: 'Momentum',
        winRateBias: 'MEDIUM',
        riskAdjustedBias: 'HIGH'
    },
    [StrategyType.VOLUME_SPIKE]: {
        style: 'Vol',
        winRateBias: 'MEDIUM',
        riskAdjustedBias: 'MEDIUM'
    }
};

export const MOCK_NEWS_SOURCES = ['Reuters', 'Bloomberg', 'MoneyControl', 'CNBC', 'Economic Times'];
export const NEWS_CATEGORIES = ['Earnings', 'Regulatory', 'Corporate Action', 'Analyst Rating', 'Macro'];
