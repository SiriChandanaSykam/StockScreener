"""
Smart Stock Analyzer
Scans stocks using real historical data and ranks by multiple performance factors.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import concurrent.futures
import time

# Import existing utilities
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_fetcher import fetch_stock_data_with_fallback
from utils.symbol_universe import load_stock_universe, get_nifty50_stocks
from utils.technicals import calculate_rsi, calculate_macd


@dataclass
class StockScore:
    """Comprehensive stock score with breakdown"""
    symbol: str
    name: str
    sector: str
    
    # Current data
    price: float = 0.0
    change_1d: float = 0.0
    change_5d: float = 0.0
    change_20d: float = 0.0
    change_3m: float = 0.0
    
    # Technical indicators
    rsi: float = 50.0
    macd_signal: str = "NEUTRAL"  # BUY, SELL, NEUTRAL
    above_sma20: bool = False
    above_sma50: bool = False
    above_sma200: bool = False
    
    # Volume
    rvol: float = 1.0  # Relative volume
    volume_surge: bool = False
    
    # Breakout
    pct_from_52w_high: float = 0.0
    pct_from_52w_low: float = 0.0
    near_breakout: bool = False
    
    # Scores (0-100)
    momentum_score: float = 0.0
    volume_score: float = 0.0
    technical_score: float = 0.0
    trend_score: float = 0.0
    
    # Final
    composite_score: float = 0.0
    rank: int = 0
    
    # Analysis summary
    signals: List[str] = field(default_factory=list)
    analysis: str = ""


def calculate_returns(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate price returns over various periods"""
    if df.empty or 'Close' not in df.columns:
        return {'1d': 0, '5d': 0, '20d': 0, '3m': 0}
    
    close = df['Close']
    current = close.iloc[-1]
    
    returns = {}
    
    # 1 day
    if len(close) >= 2:
        returns['1d'] = ((current - close.iloc[-2]) / close.iloc[-2]) * 100
    else:
        returns['1d'] = 0
    
    # 5 days
    if len(close) >= 5:
        returns['5d'] = ((current - close.iloc[-5]) / close.iloc[-5]) * 100
    else:
        returns['5d'] = returns['1d']
    
    # 20 days
    if len(close) >= 20:
        returns['20d'] = ((current - close.iloc[-20]) / close.iloc[-20]) * 100
    else:
        returns['20d'] = returns['5d']
    
    # 3 months (~60 trading days)
    if len(close) >= 60:
        returns['3m'] = ((current - close.iloc[-60]) / close.iloc[-60]) * 100
    else:
        returns['3m'] = returns['20d']
    
    return returns


def calculate_momentum_score(returns: Dict[str, float]) -> float:
    """
    Calculate momentum score (0-100) from returns.
    Weights: 1d=10%, 5d=20%, 20d=35%, 3m=35%
    """
    # Normalize returns (-50% to +50% -> 0 to 100)
    def normalize(r: float) -> float:
        return min(100, max(0, 50 + r))
    
    score = (
        normalize(returns['1d'] * 5) * 0.10 +    # Amplify daily
        normalize(returns['5d'] * 2) * 0.20 +    # Amplify weekly
        normalize(returns['20d']) * 0.35 +
        normalize(returns['3m'] * 0.5) * 0.35    # Dampen 3m for stability
    )
    
    return min(100, max(0, score))


def calculate_volume_score(df: pd.DataFrame) -> Tuple[float, float, bool]:
    """
    Calculate volume score and relative volume.
    Returns: (score, rvol, is_surge)
    """
    if df.empty or 'Volume' not in df.columns:
        return 50.0, 1.0, False
    
    volume = df['Volume']
    
    if len(volume) < 20:
        return 50.0, 1.0, False
    
    # Average volume (20-day)
    avg_vol = volume.iloc[-21:-1].mean()
    if avg_vol <= 0:
        return 50.0, 1.0, False
    
    # Today's volume
    today_vol = volume.iloc[-1]
    
    # Relative volume
    rvol = today_vol / avg_vol
    
    # Volume surge (>2x average)
    is_surge = rvol > 2.0
    
    # Score: RVOL of 1.0 = 50, 2.0 = 75, 3.0 = 100
    score = min(100, 50 + (rvol - 1) * 25)
    
    return score, rvol, is_surge


def calculate_technical_score(df: pd.DataFrame) -> Tuple[float, float, str, dict]:
    """
    Calculate technical score from RSI, MACD, SMAs.
    Returns: (score, rsi, macd_signal, sma_status)
    """
    if df.empty or 'Close' not in df.columns or len(df) < 30:
        return 50.0, 50.0, "NEUTRAL", {}
    
    close = df['Close']
    
    # RSI
    rsi = calculate_rsi(close, 14)
    rsi_value = rsi.iloc[-1] if not rsi.empty else 50
    
    # RSI score: 30 (oversold) = bullish (80), 70 (overbought) = bearish (20)
    if rsi_value < 30:
        rsi_score = 80  # Oversold = buying opportunity
    elif rsi_value > 70:
        rsi_score = 30  # Overbought = caution
    else:
        rsi_score = 50  # Neutral
    
    # MACD
    try:
        macd_line, signal_line, hist = calculate_macd(close)
        if len(hist) >= 2:
            # MACD crossover
            if hist.iloc[-1] > 0 and hist.iloc[-2] <= 0:
                macd_signal = "BUY"
                macd_score = 80
            elif hist.iloc[-1] < 0 and hist.iloc[-2] >= 0:
                macd_signal = "SELL"
                macd_score = 20
            elif hist.iloc[-1] > 0:
                macd_signal = "BULLISH"
                macd_score = 65
            else:
                macd_signal = "BEARISH"
                macd_score = 35
        else:
            macd_signal = "NEUTRAL"
            macd_score = 50
    except:
        macd_signal = "NEUTRAL"
        macd_score = 50
    
    # SMAs
    current_price = close.iloc[-1]
    sma_status = {}
    sma_score = 50
    
    if len(close) >= 20:
        sma20 = close.iloc[-20:].mean()
        sma_status['above_sma20'] = current_price > sma20
        if sma_status['above_sma20']:
            sma_score += 10
    
    if len(close) >= 50:
        sma50 = close.iloc[-50:].mean()
        sma_status['above_sma50'] = current_price > sma50
        if sma_status['above_sma50']:
            sma_score += 15
    
    if len(close) >= 200:
        sma200 = close.iloc[-200:].mean()
        sma_status['above_sma200'] = current_price > sma200
        if sma_status['above_sma200']:
            sma_score += 20
    
    # Combined score
    score = (rsi_score * 0.3 + macd_score * 0.4 + sma_score * 0.3)
    
    return score, rsi_value, macd_signal, sma_status


def calculate_trend_score(df: pd.DataFrame) -> Tuple[float, float, float, bool]:
    """
    Calculate trend/breakout score.
    Returns: (score, pct_from_high, pct_from_low, near_breakout)
    """
    if df.empty or 'Close' not in df.columns or 'High' not in df.columns:
        return 50.0, 0.0, 0.0, False
    
    current = df['Close'].iloc[-1]
    
    # 52-week (252 trading days) high/low
    period = min(252, len(df))
    high_52w = df['High'].iloc[-period:].max()
    low_52w = df['Low'].iloc[-period:].min()
    
    if high_52w <= 0:
        return 50.0, 0.0, 0.0, False
    
    # Distance from high/low
    pct_from_high = ((current - high_52w) / high_52w) * 100  # Negative = below high
    pct_from_low = ((current - low_52w) / low_52w) * 100    # Positive = above low
    
    # Near breakout: within 5% of 52-week high
    near_breakout = pct_from_high >= -5
    
    # Score: closer to high = better
    # At high = 100, 10% below = 80, 20% below = 60
    score = 100 + (pct_from_high * 2)  # Each 1% below high = -2 points
    score = min(100, max(0, score))
    
    if near_breakout:
        score = min(100, score + 10)  # Bonus for near breakout
    
    return score, pct_from_high, pct_from_low, near_breakout


def analyze_stock(symbol: str, name: str, sector: str) -> Optional[StockScore]:
    """
    Analyze a single stock and return comprehensive score.
    """
    try:
        # Fetch data
        result = fetch_stock_data_with_fallback(symbol, period="6mo")
        df = result.get('df', pd.DataFrame())
        
        if df.empty:
            return None
        
        # Handle stocks with limited data (e.g., from Quote API - only 1 row)
        if len(df) < 20:
            # Create a minimal response with available data
            price = df['Close'].iloc[-1] if 'Close' in df.columns else 0
            
            return StockScore(
                symbol=symbol,
                name=name,
                sector=sector,
                price=float(price),
                change_1d=0.0,
                change_5d=0.0,
                change_20d=0.0,
                change_3m=0.0,
                momentum_score=50.0,  # Neutral scores
                volume_score=50.0,
                technical_score=50.0,
                trend_score=50.0,
                composite_score=50.0,
                rsi=50.0,
                rvol=1.0,
                macd_signal="N/A",
                near_breakout=False,
                volume_surge=False,
                rank=0,
                signals=["📊 Limited data - price from NSE Quote API"],
                analysis=f"SME stock trading at ₹{price:.2f}. Historical data not available for full technical analysis.",
            )
        
        # Current price
        price = df['Close'].iloc[-1]
        
        # Calculate all scores
        returns = calculate_returns(df)
        momentum_score = calculate_momentum_score(returns)
        
        volume_score, rvol, volume_surge = calculate_volume_score(df)
        
        technical_score, rsi, macd_signal, sma_status = calculate_technical_score(df)
        
        trend_score, pct_from_high, pct_from_low, near_breakout = calculate_trend_score(df)
        
        # Composite score (weighted average)
        composite = (
            momentum_score * 0.30 +
            volume_score * 0.20 +
            technical_score * 0.30 +
            trend_score * 0.20
        )
        
        # Generate signals
        signals = []
        if returns['1d'] > 3:
            signals.append(f"📈 +{returns['1d']:.1f}% today")
        if returns['5d'] > 10:
            signals.append(f"🚀 +{returns['5d']:.1f}% this week")
        if rvol > 2:
            signals.append(f"📊 Volume surge {rvol:.1f}x")
        if rsi < 30:
            signals.append("💎 Oversold (RSI < 30)")
        if near_breakout:
            signals.append("🎯 Near 52-week high")
        if macd_signal == "BUY":
            signals.append("📈 MACD Buy Signal")
        if sma_status.get('above_sma20') and sma_status.get('above_sma50'):
            signals.append("✅ Above SMA20 & SMA50")
        
        # Generate analysis summary
        if composite >= 80:
            analysis = "Strong momentum with multiple bullish signals"
        elif composite >= 70:
            analysis = "Good upward momentum, watch for confirmation"
        elif composite >= 60:
            analysis = "Moderate strength, technical setup forming"
        elif composite >= 50:
            analysis = "Neutral, consolidating"
        else:
            analysis = "Weak momentum, caution advised"
        
        return StockScore(
            symbol=symbol,
            name=name,
            sector=sector,
            price=price,
            change_1d=returns['1d'],
            change_5d=returns['5d'],
            change_20d=returns['20d'],
            change_3m=returns['3m'],
            rsi=rsi,
            macd_signal=macd_signal,
            above_sma20=sma_status.get('above_sma20', False),
            above_sma50=sma_status.get('above_sma50', False),
            above_sma200=sma_status.get('above_sma200', False),
            rvol=rvol,
            volume_surge=volume_surge,
            pct_from_52w_high=pct_from_high,
            pct_from_52w_low=pct_from_low,
            near_breakout=near_breakout,
            momentum_score=momentum_score,
            volume_score=volume_score,
            technical_score=technical_score,
            trend_score=trend_score,
            composite_score=composite,
            signals=signals,
            analysis=analysis
        )
        
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None


def analyze_stocks_batch(
    symbols: List[Dict[str, str]],
    max_workers: int = 5,
    progress_callback=None
) -> List[StockScore]:
    """
    Analyze multiple stocks in parallel.
    
    Args:
        symbols: List of {symbol, name, sector} dicts
        max_workers: Number of parallel workers
        progress_callback: Optional callback(current, total) for progress
    
    Returns:
        List of StockScore sorted by composite_score descending
    """
    results = []
    total = len(symbols)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                analyze_stock, 
                s['symbol'], 
                s.get('name', s['symbol']), 
                s.get('sector', 'Others')
            ): s['symbol'] 
            for s in symbols
        }
        
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            symbol = futures[future]
            try:
                score = future.result()
                if score:
                    results.append(score)
            except Exception as e:
                print(f"Error with {symbol}: {e}")
            
            if progress_callback:
                progress_callback(i + 1, total)
    
    # Sort by composite score
    results.sort(key=lambda x: x.composite_score, reverse=True)
    
    # Assign ranks
    for i, score in enumerate(results):
        score.rank = i + 1
    
    return results


def get_top_stocks(n: int = 50, use_nifty50: bool = True, universe_limit: int = 500) -> List[StockScore]:
    """
    Get top N stocks by composite score.
    
    Args:
        n: Number of top stocks to return
        use_nifty50: If True, analyze Nifty 50 stocks only (fast)
        universe_limit: Max stocks to scan from full universe (default 500)
    
    If use_nifty50=True, analyzes Nifty 50 stocks.
    Otherwise analyzes up to universe_limit stocks from full universe.
    """
    print(f"🔍 Analyzing stocks...")
    start = time.time()
    
    if use_nifty50:
        symbols = get_nifty50_stocks()
    else:
        # Get stocks up to universe_limit for broader analysis
        symbols = load_stock_universe(limit=universe_limit)
    
    print(f"📊 Fetching data for {len(symbols)} stocks...")
    
    def progress(current, total):
        if current % 10 == 0 or current == total:
            print(f"  Progress: {current}/{total} ({current*100//total}%)")
    
    results = analyze_stocks_batch(symbols, max_workers=5, progress_callback=progress)
    
    elapsed = time.time() - start
    print(f"✅ Analyzed {len(results)} stocks in {elapsed:.1f}s")
    
    return results[:n]


def _to_python(val):
    """Convert numpy types to native Python types for JSON serialization"""
    if hasattr(val, 'item'):  # numpy scalar
        return val.item()
    if isinstance(val, (np.bool_, np.generic)):
        return val.item()
    if isinstance(val, (np.ndarray,)):
        return val.tolist()
    return val


def score_to_dict(score: StockScore) -> Dict:
    """Convert StockScore to JSON-serializable dict"""
    return {
        'symbol': str(score.symbol),
        'name': str(score.name),
        'sector': str(score.sector),
        'price': float(_to_python(score.price)),
        'change1d': float(_to_python(score.change_1d)),
        'change5d': float(_to_python(score.change_5d)),
        'change20d': float(_to_python(score.change_20d)),
        'change3m': float(_to_python(score.change_3m)),
        'rsi': float(_to_python(score.rsi)),
        'macdSignal': str(score.macd_signal),
        'aboveSma20': bool(_to_python(score.above_sma20)),
        'aboveSma50': bool(_to_python(score.above_sma50)),
        'aboveSma200': bool(_to_python(score.above_sma200)),
        'rvol': float(_to_python(score.rvol)),
        'volumeSurge': bool(_to_python(score.volume_surge)),
        'pctFrom52wHigh': float(_to_python(score.pct_from_52w_high)),
        'pctFrom52wLow': float(_to_python(score.pct_from_52w_low)),
        'nearBreakout': bool(_to_python(score.near_breakout)),
        'momentumScore': float(_to_python(score.momentum_score)),
        'volumeScore': float(_to_python(score.volume_score)),
        'technicalScore': float(_to_python(score.technical_score)),
        'trendScore': float(_to_python(score.trend_score)),
        'compositeScore': float(_to_python(score.composite_score)),
        'rank': int(score.rank),
        'signals': list(score.signals),
        'analysis': str(score.analysis)
    }


# Test
if __name__ == "__main__":
    # Analyze Nifty 50
    top_stocks = get_top_stocks(n=10, use_nifty50=True)
    
    print("\n" + "=" * 60)
    print("🏆 TOP 10 STOCKS BY COMPOSITE SCORE")
    print("=" * 60)
    
    for stock in top_stocks:
        print(f"\n#{stock.rank} {stock.symbol} - Score: {stock.composite_score:.1f}")
        print(f"   Price: ₹{stock.price:.2f} | 1D: {stock.change_1d:+.1f}% | 5D: {stock.change_5d:+.1f}%")
        print(f"   RSI: {stock.rsi:.0f} | RVOL: {stock.rvol:.1f}x | From 52W High: {stock.pct_from_52w_high:.1f}%")
        if stock.signals:
            print(f"   Signals: {', '.join(stock.signals[:3])}")
        print(f"   Analysis: {stock.analysis}")
