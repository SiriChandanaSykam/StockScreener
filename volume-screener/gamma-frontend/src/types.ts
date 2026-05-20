export enum SignalType {
    BUY = 'BUY',
    SELL = 'SELL',
    NEUTRAL = 'NEUTRAL',
    HOLD = 'HOLD'
}

export enum StrategyType {
    MOMENTUM_BREAKOUT = 'Momentum Breakout',
    GAP_AND_GO = 'Gap & Go',
    VWAP_EMA_TREND = 'VWAP + EMA Trend',
    PULLBACK = 'Pullback',
    REVERSAL_RSI = 'Reversal/RSI',
    VOLUME_SPIKE = 'Unusual Volume',
    SECTOR_ALIGNMENT = 'Sector Alignment'
}

export enum ImpactLevel {
    HIGH = 'HIGH',
    MEDIUM = 'MEDIUM',
    LOW = 'LOW'
}

export interface OHLC {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    vwap?: number;
    ema9?: number;
    ema20?: number;
}

export interface StrategyResult {
    strategy: string;
    signal: SignalType;
    score: number;
    reason: string;
}

export interface DailyStats {
    sma20: number;
    sma50: number;
    sma200: number;
    week52High: number;
    week52Low: number;
    avgVolume: number;
    previousClose: number;
    openPrice: number;
}

export interface StockData {
    symbol: string;
    name: string;
    sector: string;
    price: number;
    changePercent: number;
    volume: number;
    rvol: number;
    rsi: number;
    history: OHLC[];
    activeStrategies: StrategyResult[];
    activePatterns: string[];
    overallSignal: SignalType;
    stats: DailyStats;
}

export interface NewsItem {
    id: string;
    title: string;
    source: string;
    timestamp: string;
    relatedSymbols: string[];
    sentimentScore: number;
    impact: ImpactLevel;
    summary: string;
    categories: string[];
}

export interface ScreenerFilters {
    priceMin: number;
    priceMax: number;
    rsiMin: number;
    rsiMax: number;
    minVolume: number;
    aboveSMA20: boolean;
    aboveSMA50: boolean;
    aboveSMA200: boolean;
    onlyPositiveChange: boolean;
}

export type AiMode = 'standard' | 'search' | 'thinking';

export interface ChatMessage {
    id: string;
    role: 'user' | 'model';
    text: string;
    imageUrl?: string;
    mode?: AiMode;
    timestamp: number;
    sources?: { uri: string; title: string }[];
    isThinking?: boolean;
}
