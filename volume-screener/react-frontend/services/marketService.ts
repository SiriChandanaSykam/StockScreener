/**
 * Market Service - Updated to call Python FastAPI backend
 * Replace your original marketService.ts with this file
 */

import { StockData, NewsItem, OHLC } from '../types';

const API_BASE = 'http://localhost:8000';

// Helper to handle API responses
const fetchAPI = async <T>(endpoint: string): Promise<T> => {
    const response = await fetch(`${API_BASE}${endpoint}`);
    if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
    }
    return response.json();
};

/**
 * Fetch market data from Python backend
 * Replaces the original mock data generation
 */
export const fetchMarketData = async (): Promise<StockData[]> => {
    try {
        const data = await fetchAPI<{ stocks: StockData[]; lastUpdated: string }>('/market-data');
        return data.stocks;
    } catch (error) {
        console.error('Failed to fetch market data:', error);
        return [];
    }
};

/**
 * Fetch live market updates (simulated tick)
 */
export const fetchLiveMarketData = async (): Promise<StockData[]> => {
    try {
        const data = await fetchAPI<{ stocks: StockData[]; lastUpdated: string }>('/market-data/live');
        return data.stocks;
    } catch (error) {
        console.error('Failed to fetch live data:', error);
        return [];
    }
};

/**
 * Simulate live market by polling the API
 * Call this in place of the original simulateLiveMarket function
 */
export const simulateLiveMarket = async (currentStocks: StockData[]): Promise<StockData[]> => {
    // Call the live endpoint which handles simulation on the backend
    return fetchLiveMarketData();
};

/**
 * Fetch AI prediction for a specific stock
 */
export const fetchPrediction = async (symbol: string): Promise<{
    predictedClose: number;
    rSquared: number;
    upside: number;
    modelType: string;
    featureNames: string[];
} | null> => {
    try {
        const data = await fetchAPI<any>(`/prediction/${symbol}`);
        if (data.error) {
            console.warn(data.error);
            return null;
        }
        return data;
    } catch (error) {
        console.error('Failed to fetch prediction:', error);
        return null;
    }
};

/**
 * Fetch top predictions (AI Projected Breakouts)
 */
export const fetchTopPredictions = async (n: number = 3): Promise<{
    symbol: string;
    price: number;
    predictedClose: number;
    upside: number;
    confidence: number;
}[]> => {
    try {
        return await fetchAPI(`/predictions/top?n=${n}`);
    } catch (error) {
        console.error('Failed to fetch top predictions:', error);
        return [];
    }
};

/**
 * Fetch news with sentiment analysis
 */
export const fetchNewsAnalysis = async (): Promise<NewsItem[]> => {
    try {
        return await fetchAPI<NewsItem[]>('/news');
    } catch (error) {
        console.error('Failed to fetch news:', error);
        return [];
    }
};

/**
 * Fetch available symbols
 */
export const fetchSymbols = async (): Promise<{ symbol: string; name: string; sector: string }[]> => {
    try {
        return await fetchAPI('/symbols');
    } catch (error) {
        console.error('Failed to fetch symbols:', error);
        return [];
    }
};

/**
 * Fetch strategy metadata
 */
export const fetchStrategies = async (): Promise<Record<string, {
    style: string;
    winRateBias: string;
    riskAdjustedBias: string;
}>> => {
    try {
        return await fetchAPI('/strategies');
    } catch (error) {
        console.error('Failed to fetch strategies:', error);
        return {};
    }
};

/**
 * WebSocket connection for real-time updates
 * Use this for live market data instead of polling
 */
export class MarketWebSocket {
    private ws: WebSocket | null = null;
    private onUpdate: ((stocks: StockData[]) => void) | null = null;

    connect(onUpdate: (stocks: StockData[]) => void): void {
        this.onUpdate = onUpdate;
        this.ws = new WebSocket('ws://localhost:8000/ws');

        this.ws.onopen = () => {
            console.log('WebSocket connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'market_update' && this.onUpdate) {
                this.onUpdate(data.stocks);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            // Reconnect after 3 seconds
            setTimeout(() => this.connect(this.onUpdate!), 3000);
        };
    }

    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Export a singleton instance for easy use
export const marketSocket = new MarketWebSocket();
