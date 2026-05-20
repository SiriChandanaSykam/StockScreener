"""
FastAPI Backend for Gamma Screener
Serves market data, predictions, and news for React frontend
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import asyncio
import sys
import json
from datetime import datetime

sys.path.append('..')

from utils.market_service import fetch_market_data, simulate_live_market, StockData
from utils.price_predictor import perform_regression_analysis
from utils.strategy_meta import STRATEGY_META
from utils.symbol_universe import load_stock_universe, search_stocks, get_nifty50_stocks
from utils.stock_analyzer import get_top_stocks, analyze_stock, score_to_dict
from utils.data_fetcher import fetch_stock_data_with_fallback
from utils.charting import create_tv_chart
from utils.technicals import calculate_rsi, calculate_macd

app = FastAPI(
    title="Gamma Screener API",
    description="Python backend for Gamma Screener React frontend",
    version="2.0.0"
)

# CORS - Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
_market_data: List[StockData] = []
_connected_clients: List[WebSocket] = []
_all_symbols: List[Dict] = []


def stock_to_dict(stock: StockData) -> Dict[str, Any]:
    """Convert StockData to JSON-serializable dict"""
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "sector": stock.sector,
        "price": stock.price,
        "changePercent": stock.changePercent,
        "volume": stock.volume,
        "rvol": stock.rvol,
        "rsi": stock.rsi,
        "history": [
            {
                "time": h.time,
                "open": h.open,
                "high": h.high,
                "low": h.low,
                "close": h.close,
                "volume": h.volume,
                "vwap": h.vwap,
                "ema9": h.ema9,
                "ema20": h.ema20
            }
            for h in stock.history
        ],
        "activeStrategies": [
            {
                "strategy": s.strategy,
                "signal": s.signal,
                "score": s.score,
                "reason": s.reason
            }
            for s in stock.activeStrategies
        ],
        "activePatterns": stock.activePatterns,
        "overallSignal": stock.overallSignal,
        "stats": {
            "sma20": stock.stats.sma20,
            "sma50": stock.stats.sma50,
            "sma200": stock.stats.sma200,
            "week52High": stock.stats.week52High,
            "week52Low": stock.stats.week52Low,
            "avgVolume": stock.stats.avgVolume,
            "previousClose": stock.stats.previousClose,
            "openPrice": stock.stats.openPrice
        }
    }


@app.on_event("startup")
async def startup_event():
    """Load stock universe on startup"""
    global _all_symbols
    _all_symbols = load_stock_universe()
    print(f"Loaded {len(_all_symbols)} stocks from universe")


@app.get("/")
async def root():
    return {
        "message": "Gamma Screener API",
        "version": "2.0.0",
        "totalSymbols": len(_all_symbols),
        "endpoints": [
            "/market-data",
            "/market-data?limit=50&page=1",
            "/symbols",
            "/symbols/search?q=RELIANCE",
            "/symbols/nifty50",
            "/prediction/{symbol}",
            "/news"
        ]
    }


@app.get("/market-data")
async def get_market_data(
    limit: int = Query(50, ge=1, le=500, description="Number of stocks per page"),
    page: int = Query(1, ge=1, description="Page number"),
    sector: Optional[str] = Query(None, description="Filter by sector")
):
    """
    Fetch market data with pagination.
    
    - **limit**: Number of stocks per page (1-500, default 50)
    - **page**: Page number starting from 1
    - **sector**: Optional sector filter
    """
    global _market_data, _all_symbols
    
    # Filter by sector if specified
    filtered_symbols = _all_symbols
    if sector:
        filtered_symbols = [s for s in _all_symbols if s['sector'].lower() == sector.lower()]
    
    # Calculate pagination
    total = len(filtered_symbols)
    start = (page - 1) * limit
    end = start + limit
    page_symbols = filtered_symbols[start:end]
    
    # Fetch data for this page
    _market_data = fetch_market_data(symbols=page_symbols)
    
    return {
        "stocks": [stock_to_dict(s) for s in _market_data],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        },
        "lastUpdated": datetime.now().isoformat()
    }


@app.get("/market-data/live")
async def get_live_market_data():
    """Get live-updated market data (simulated tick)."""
    global _market_data
    
    if not _market_data:
        _market_data = fetch_market_data()
    
    _market_data = simulate_live_market(_market_data)
    
    return {
        "stocks": [stock_to_dict(s) for s in _market_data],
        "lastUpdated": datetime.now().isoformat()
    }


@app.get("/symbols")
async def get_symbols(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get all available stock symbols with pagination.
    Returns 6,832+ Indian stocks.
    """
    global _all_symbols
    
    total = len(_all_symbols)
    symbols_page = _all_symbols[offset:offset + limit]
    
    return {
        "symbols": symbols_page,
        "total": total,
        "offset": offset,
        "limit": limit
    }


@app.get("/symbols/search")
async def search_symbols(q: str = Query(..., min_length=1, description="Search query")):
    """
    Search for stocks by symbol or name.
    
    Example: /symbols/search?q=TATA
    """
    results = search_stocks(q, limit=30)
    return {
        "query": q,
        "results": results,
        "count": len(results)
    }


@app.get("/symbols/nifty50")
async def get_nifty50():
    """Get Nifty 50 stocks"""
    stocks = get_nifty50_stocks()
    return {
        "stocks": stocks,
        "count": len(stocks)
    }


@app.get("/symbols/sectors")
async def get_sectors():
    """Get list of all sectors with stock counts"""
    global _all_symbols
    
    sector_counts = {}
    for s in _all_symbols:
        sector = s.get('sector', 'Others')
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    
    return {
        "sectors": [
            {"name": name, "count": count}
            for name, count in sorted(sector_counts.items(), key=lambda x: -x[1])
        ]
    }


@app.get("/prediction/{symbol}")
async def get_prediction(symbol: str):
    """Get AI price prediction for a specific stock."""
    global _market_data
    
    stock = next((s for s in _market_data if s.symbol == symbol), None)
    
    if not stock:
        return {"error": f"Stock {symbol} not found in current data"}
    
    ohlc_dicts = [
        {
            "open": h.open, "high": h.high, "low": h.low,
            "close": h.close, "volume": h.volume, "vwap": h.vwap
        }
        for h in stock.history
    ]
    
    result = perform_regression_analysis(ohlc_dicts)
    
    if not result:
        return {"error": "Not enough data for prediction"}
    
    upside = ((result.predictedClose - stock.price) / stock.price) * 100
    
    return {
        "symbol": symbol,
        "currentPrice": stock.price,
        "predictedClose": result.predictedClose,
        "upside": upside,
        "rSquared": result.rSquared,
        "modelType": result.modelType,
        "featureNames": result.featureNames,
        "coefficients": result.coefficients
    }


@app.get("/predictions/top")
async def get_top_predictions(n: int = 3):
    """Get top N stocks by predicted upside."""
    global _market_data
    
    if not _market_data:
        _market_data = fetch_market_data()
    
    predictions = []
    
    for stock in _market_data:
        ohlc_dicts = [
            {"open": h.open, "high": h.high, "low": h.low,
             "close": h.close, "volume": h.volume, "vwap": h.vwap}
            for h in stock.history
        ]
        
        result = perform_regression_analysis(ohlc_dicts)
        
        if result:
            upside = ((result.predictedClose - stock.price) / stock.price) * 100
            predictions.append({
                "symbol": stock.symbol,
                "price": stock.price,
                "predictedClose": result.predictedClose,
                "upside": upside,
                "confidence": result.rSquared
            })
    
    predictions.sort(key=lambda x: x["upside"], reverse=True)
    return predictions[:n]


@app.get("/news")
async def get_news():
    """Get simulated news items with sentiment."""
    import random
    
    global _all_symbols
    
    headlines = [
        {"t": "Quarterly profits exceed estimates driven by growth", "s": 0.8, "i": "HIGH"},
        {"t": "Regulatory body investigates irregularities", "s": -0.9, "i": "HIGH"},
        {"t": "New strategic partnership announced", "s": 0.6, "i": "MEDIUM"},
        {"t": "CEO steps down amid restructuring concerns", "s": -0.5, "i": "MEDIUM"},
        {"t": "Sector outlook upgraded by brokerage", "s": 0.7, "i": "MEDIUM"},
        {"t": "Market sell-off impacts sector", "s": -0.6, "i": "HIGH"},
    ]
    
    sources = ["Reuters", "Bloomberg", "MoneyControl", "CNBC", "Economic Times"]
    categories = ["Earnings", "Regulatory", "Corporate Action", "Analyst Rating", "Macro"]
    
    news_items = []
    sample_stocks = random.sample(_all_symbols[:200], min(12, len(_all_symbols)))
    
    for i, stock in enumerate(sample_stocks):
        template = random.choice(headlines)
        
        news_items.append({
            "id": f"news-{i}",
            "title": f"{stock['name']}: {template['t']}",
            "source": random.choice(sources),
            "timestamp": f"{random.randint(1, 8)}h ago",
            "relatedSymbols": [stock['symbol']],
            "sentimentScore": template['s'] + random.uniform(-0.1, 0.1),
            "impact": template['i'],
            "summary": "AI Summary: This news suggests a shift in market perception.",
            "categories": [random.choice(categories)]
        })
    
    return news_items


@app.get("/strategies")
async def get_strategies():
    """Get list of available strategies with metadata"""
    return {
        name: {
            "style": meta.style,
            "winRateBias": meta.win_rate_bias.value,
            "riskAdjustedBias": meta.risk_adjusted_bias.value
        }
        for name, meta in STRATEGY_META.items()
    }


# ============================================================
# SMART STOCK ANALYSIS ENDPOINTS
# ============================================================

# Cache for analyzed stocks
_analyzed_cache: Dict[str, Any] = {}
_cache_timestamp: Optional[datetime] = None


@app.get("/analyze")
async def analyze_top_stocks(
    n: int = Query(50, ge=1, le=200, description="Number of top stocks to return"),
    use_nifty50: bool = Query(True, description="Use Nifty 50 (fast) or broader universe"),
    universe_limit: int = Query(500, ge=50, le=5000, description="Max stocks to scan from full universe (ignored if use_nifty50=true)")
):
    """
    Analyze stocks and return top performers ranked by composite score.
    
    This endpoint scans stocks using real historical data and ranks them by:
    - Momentum (1d, 5d, 20d, 3m returns)
    - Volume (relative volume, surge indicator)
    - Technical (RSI, MACD, SMA alignment)
    - Trend (52-week high proximity, breakout signals)
    
    **Parameters**:
    - **n**: Number of top stocks to return (max 200)
    - **use_nifty50**: If true, scan Nifty 50 only (fast). If false, scan broader universe.
    - **universe_limit**: Max stocks to scan from full universe (50-5000, default 500)
    
    **Note**: First call may take 30-60 seconds to fetch real data.
    Results are cached for 5 minutes.
    """
    global _analyzed_cache, _cache_timestamp
    
    # Check cache (5 minute TTL) - include universe_limit in cache key
    cache_key = f"top_{n}_{use_nifty50}_{universe_limit}"
    if _cache_timestamp and (datetime.now() - _cache_timestamp).seconds < 300:
        if cache_key in _analyzed_cache:
            return _analyzed_cache[cache_key]
    
    # Run analysis with configurable limit
    top_stocks = get_top_stocks(n=n, use_nifty50=use_nifty50, universe_limit=universe_limit)
    
    result = {
        "stocks": [score_to_dict(s) for s in top_stocks],
        "analyzedCount": len(top_stocks),
        "universeLimit": universe_limit if not use_nifty50 else 50,
        "timestamp": datetime.now().isoformat(),
        "source": "Nifty50" if use_nifty50 else f"Full Universe (limit={universe_limit})"
    }
    
    # Cache result
    _analyzed_cache[cache_key] = result
    _cache_timestamp = datetime.now()
    
    return result


@app.get("/analyze/{symbol}")
async def analyze_single_stock(symbol: str):
    """
    Get detailed analysis for a single stock.
    
    Returns comprehensive scoring with:
    - Price momentum across multiple timeframes
    - Technical indicator signals
    - Volume analysis
    - Breakout proximity
    - Trading signals and summary
    """
    global _all_symbols
    
    # Find stock info
    stock_info = next((s for s in _all_symbols if s['symbol'].upper() == symbol.upper()), None)
    
    if not stock_info:
        stock_info = {'symbol': symbol.upper(), 'name': symbol.upper(), 'sector': 'Unknown'}
    
    # Analyze
    score = analyze_stock(
        stock_info['symbol'],
        stock_info.get('name', stock_info['symbol']),
        stock_info.get('sector', 'Unknown')
    )
    
    if not score:
        return {"error": f"Could not analyze {symbol}. No data available."}
    
    return score_to_dict(score)


@app.get("/chart/{symbol}")
async def get_stock_chart(
    symbol: str,
    period: str = Query("3mo", description="Period: 1mo, 3mo, 6mo, 1y")
):
    """
    Get TradingView-style chart data for a stock.
    
    Returns Plotly JSON that can be rendered as an interactive chart with:
    - Candlestick OHLC
    - RSI subplot
    - MACD subplot  
    - Volume bars
    """
    import pandas as pd
    
    # Fetch data
    result = fetch_stock_data_with_fallback(symbol, period=period)
    df = result.get('df', pd.DataFrame())
    
    if df.empty:
        return {"error": f"No data available for {symbol}"}
    
    # Ensure required columns exist
    if not all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume']):
        return {"error": "Invalid data format"}
    
    # Calculate indicators
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['RSI'] = calculate_rsi(df['Close'], 14)
    
    try:
        macd, signal, hist = calculate_macd(df['Close'])
        df['MACD'] = macd
        df['MACD_Signal'] = signal
    except:
        pass
    
    # Create TradingView chart
    fig = create_tv_chart(df, symbol)
    
    # Return as JSON
    return {
        "symbol": symbol,
        "period": period,
        "dataSource": result.get('mode', 'unknown'),
        "chart": fig.to_json(),
        "lastPrice": float(df['Close'].iloc[-1]),
        "change1d": float(((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100) if len(df) >= 2 else 0,
        "high52w": float(df['High'].max()),
        "low52w": float(df['Low'].min()),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/chart-html/{symbol}")
async def get_chart_html(
    symbol: str,
    period: str = Query("3mo", description="Period: 1mo, 3mo, 6mo, 1y")
):
    """
    Get TradingView-style chart as embeddable HTML.
    Use this in an iframe or directly embed in the page.
    """
    from fastapi.responses import HTMLResponse
    import pandas as pd
    
    # Fetch data
    result = fetch_stock_data_with_fallback(symbol, period=period)
    df = result.get('df', pd.DataFrame())
    
    if df.empty:
        return HTMLResponse(f"<h3>No data available for {symbol}</h3>")
    
    # Calculate indicators
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['RSI'] = calculate_rsi(df['Close'], 14)
    
    try:
        macd, signal, hist = calculate_macd(df['Close'])
        df['MACD'] = macd
        df['MACD_Signal'] = signal
    except:
        pass
    
    # Create chart
    fig = create_tv_chart(df, symbol)
    
    # Return as full HTML page
    html = fig.to_html(full_html=True, include_plotlyjs='cdn')
    
    return HTMLResponse(content=html)


# ============================================================
# CANDLESTICK PATTERNS ENDPOINT
# ============================================================

from strategies.candlestick_patterns import detect_patterns, get_pattern_bias
from dataclasses import dataclass as dc_dataclass

@dc_dataclass
class OHLCData:
    """OHLC data for pattern detection"""
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def range(self) -> float:
        return self.high - self.low
    
    @property
    def body(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open
    
    @property
    def upper_shadow(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        return min(self.open, self.close) - self.low


@app.get("/patterns/{symbol}")
async def get_candlestick_patterns(
    symbol: str,
    period: str = Query("3mo", description="Period: 1mo, 3mo, 6mo, 1y")
):
    """
    Detect candlestick patterns for a stock.
    
    Returns 15+ patterns including:
    - Single candle: Doji, Hammer, Shooting Star, Marubozu
    - Two candle: Engulfing, Harami, Piercing, Dark Cloud
    - Three candle: Morning Star, Evening Star, Three White Soldiers, Three Black Crows
    """
    import pandas as pd
    
    # Fetch data
    result = fetch_stock_data_with_fallback(symbol, period=period)
    df = result.get('df', pd.DataFrame())
    
    if df.empty or len(df) < 5:
        return {"error": f"Not enough data for {symbol}"}
    
    # Convert to OHLC objects
    ohlc_list = []
    for idx, row in df.tail(10).iterrows():  # Last 10 candles
        ohlc_list.append(OHLCData(
            time=str(idx),
            open=float(row['Open']),
            high=float(row['High']),
            low=float(row['Low']),
            close=float(row['Close']),
            volume=float(row['Volume'])
        ))
    
    # Detect patterns
    patterns = detect_patterns(ohlc_list)
    
    # Build response with pattern details
    pattern_details = []
    for p in patterns:
        bias = get_pattern_bias(p)
        pattern_details.append({
            "name": p,
            "bias": bias,
            "signal": "BUY" if bias == "bullish" else "SELL" if bias == "bearish" else "NEUTRAL"
        })
    
    return {
        "symbol": symbol,
        "patterns": pattern_details,
        "patternCount": len(patterns),
        "lastPrice": float(df['Close'].iloc[-1]),
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# SECTOR ANALYSIS ENDPOINT  
# ============================================================

@app.get("/sectors")
async def get_sector_analysis():
    """
    Get sector-wise breakdown of the stock universe with counts.
    """
    global _all_symbols
    
    sector_data = {}
    for s in _all_symbols:
        sector = s.get('sector', 'Others')
        if sector not in sector_data:
            sector_data[sector] = {"name": sector, "count": 0, "stocks": []}
        sector_data[sector]["count"] += 1
        # Only include first 10 stocks per sector
        if len(sector_data[sector]["stocks"]) < 10:
            sector_data[sector]["stocks"].append({
                "symbol": s['symbol'],
                "name": s['name']
            })
    
    # Sort by count
    sectors = sorted(sector_data.values(), key=lambda x: x['count'], reverse=True)
    
    return {
        "sectors": sectors,
        "totalSectors": len(sectors),
        "totalStocks": len(_all_symbols)
    }


@app.get("/sectors/{sector_name}/analyze")
async def analyze_sector_stocks(
    sector_name: str,
    limit: int = Query(20, ge=1, le=100, description="Number of stocks to analyze")
):
    """
    Analyze top stocks in a specific sector.
    """
    global _all_symbols
    
    # Filter stocks by sector
    sector_stocks = [s for s in _all_symbols if s.get('sector', '').lower() == sector_name.lower()]
    
    if not sector_stocks:
        return {"error": f"Sector '{sector_name}' not found"}
    
    # Limit stocks to analyze
    stocks_to_analyze = sector_stocks[:limit]
    
    # Run analysis
    results = []
    for stock_info in stocks_to_analyze:
        score = analyze_stock(
            stock_info['symbol'],
            stock_info.get('name', stock_info['symbol']),
            stock_info.get('sector', 'Unknown')
        )
        if score:
            results.append(score_to_dict(score))
    
    # Sort by composite score
    results.sort(key=lambda x: x['compositeScore'], reverse=True)
    
    return {
        "sector": sector_name,
        "stocks": results,
        "analyzedCount": len(results),
        "totalInSector": len(sector_stocks),
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# MULTI-STRATEGY SIGNALS ENDPOINT
# ============================================================

@app.get("/signals/{symbol}")
async def get_trading_signals(
    symbol: str,
    period: str = Query("3mo", description="Period for analysis")
):
    """
    Generate trading signals from multiple strategies for a stock.
    
    Strategies include:
    - RSI Reversal
    - VWAP/EMA Trend
    - Volume Spike
    - Momentum Breakout
    - Gap & Go
    """
    import pandas as pd
    import numpy as np
    from strategies.indicators import calculate_ema, calculate_vwap, calculate_relative_volume
    
    # Fetch data
    result = fetch_stock_data_with_fallback(symbol, period=period)
    df = result.get('df', pd.DataFrame())
    
    if df.empty or len(df) < 20:
        return {"error": f"Not enough data for {symbol}"}
    
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    volume = df['Volume'].values
    
    # Calculate indicators
    rsi = calculate_rsi(df['Close'], 14)
    ema9 = calculate_ema(close, 9)
    ema20 = calculate_ema(close, 20)
    vwap = calculate_vwap(df)
    rvol = calculate_relative_volume(volume, 20)
    
    signals = []
    current_price = float(close[-1])
    
    # RSI Reversal
    rsi_value = float(rsi.iloc[-1]) if hasattr(rsi, 'iloc') else float(rsi[-1])
    if rsi_value < 30:
        signals.append({"strategy": "RSI Reversal", "signal": "BUY", "reason": f"Oversold: RSI {rsi_value:.0f}", "confidence": 4})
    elif rsi_value > 70:
        signals.append({"strategy": "RSI Reversal", "signal": "SELL", "reason": f"Overbought: RSI {rsi_value:.0f}", "confidence": 4})
    
    # VWAP/EMA Trend
    if ema9[-1] > ema20[-1] and current_price > vwap[-1]:
        signals.append({"strategy": "VWAP/EMA Trend", "signal": "BUY", "reason": "Bullish trend above VWAP", "confidence": 3})
    elif ema9[-1] < ema20[-1] and current_price < vwap[-1]:
        signals.append({"strategy": "VWAP/EMA Trend", "signal": "SELL", "reason": "Bearish trend below VWAP", "confidence": 3})
    
    # Volume Spike
    if rvol[-1] > 3.0:
        direction = "BUY" if current_price > df['Open'].iloc[-1] else "SELL"
        signals.append({"strategy": "Volume Spike", "signal": direction, "reason": f"RVOL {rvol[-1]:.1f}x", "confidence": 4})
    
    # Momentum Breakout
    high_20 = np.max(high[-20:])
    low_20 = np.min(low[-20:])
    if current_price > high_20 and rvol[-1] > 2.0:
        signals.append({"strategy": "Momentum Breakout", "signal": "BUY", "reason": "20-bar breakout", "confidence": 5})
    elif current_price < low_20 and rvol[-1] > 2.0:
        signals.append({"strategy": "Momentum Breakout", "signal": "SELL", "reason": "20-bar breakdown", "confidence": 5})
    
    # Gap & Go
    if len(df) >= 2:
        prev_close = df['Close'].iloc[-2]
        open_price = df['Open'].iloc[-1]
        gap_pct = ((open_price - prev_close) / prev_close) * 100
        if gap_pct > 1.5 and current_price > open_price:
            signals.append({"strategy": "Gap & Go", "signal": "BUY", "reason": f"Gap up {gap_pct:.1f}%", "confidence": 4})
        elif gap_pct < -1.5 and current_price < open_price:
            signals.append({"strategy": "Gap & Go", "signal": "SELL", "reason": f"Gap down {abs(gap_pct):.1f}%", "confidence": 4})
    
    # Calculate overall signal
    buy_count = sum(1 for s in signals if s["signal"] == "BUY")
    sell_count = sum(1 for s in signals if s["signal"] == "SELL")
    
    if buy_count > sell_count:
        overall = "BUY"
    elif sell_count > buy_count:
        overall = "SELL"
    else:
        overall = "NEUTRAL"
    
    return {
        "symbol": symbol,
        "currentPrice": current_price,
        "signals": signals,
        "signalCount": len(signals),
        "overallSignal": overall,
        "buyVotes": buy_count,
        "sellVotes": sell_count,
        "timestamp": datetime.now().isoformat()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market updates."""
    await websocket.accept()
    _connected_clients.append(websocket)
    
    global _market_data
    if not _market_data:
        _market_data = fetch_market_data()
    
    try:
        while True:
            _market_data = simulate_live_market(_market_data)
            
            message = {
                "type": "market_update",
                "stocks": [stock_to_dict(s) for s in _market_data],
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send_json(message)
            await asyncio.sleep(1.5)
            
    except WebSocketDisconnect:
        _connected_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
