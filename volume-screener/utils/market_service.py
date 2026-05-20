"""
Market Simulation Service
Python port of marketService.ts - generates simulated market data
"""

import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from strategies.candlestick_patterns import detect_patterns
from utils.strategy_meta import SYMBOLS_UNIVERSE


def random_range(min_val: float, max_val: float) -> float:
    """Generate random number in range"""
    return random.random() * (max_val - min_val) + min_val


@dataclass
class OHLC:
    """OHLC candlestick data"""
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float] = None
    ema9: Optional[float] = None
    ema20: Optional[float] = None
    
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


@dataclass
class DailyStats:
    """Daily statistics for stock"""
    sma20: float = 0.0
    sma50: float = 0.0
    sma200: float = 0.0
    week52High: float = 0.0
    week52Low: float = 0.0
    avgVolume: float = 0.0
    previousClose: float = 0.0
    openPrice: float = 0.0


@dataclass
class StrategyResult:
    """Result from a trading strategy"""
    strategy: str
    signal: str  # BUY, SELL, NEUTRAL, HOLD
    score: int
    reason: str


@dataclass
class StockData:
    """Complete stock data with all indicators"""
    symbol: str
    name: str
    sector: str
    price: float
    changePercent: float
    volume: float
    rvol: float
    rsi: float
    history: List[OHLC]
    activeStrategies: List[StrategyResult]
    activePatterns: List[str]
    overallSignal: str
    stats: DailyStats


# Sector performance tracking
_current_sector_performance: Optional[Dict[str, float]] = None


def generate_intraday_data(base_price: float, periods: int = 75) -> List[OHLC]:
    """Generate simulated intraday OHLC data"""
    current_price = base_price
    data = []
    now = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    
    for i in range(periods):
        volatility = base_price * 0.002
        change = random_range(-volatility, volatility)
        open_price = current_price
        close_price = current_price + change
        high = max(open_price, close_price) + random_range(0, volatility * 0.5)
        low = min(open_price, close_price) - random_range(0, volatility * 0.5)
        volume = int(random_range(1000, 50000))
        
        # Simple mock VWAP/EMA
        vwap = (high + low + close_price) / 3
        
        current_price = close_price
        
        data.append(OHLC(
            time=now.strftime("%H:%M"),
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume,
            vwap=vwap,
            ema9=close_price * 0.999,
            ema20=close_price * 0.998
        ))
        
        now += timedelta(minutes=5)
    
    return data


def generate_sector_performance() -> Dict[str, float]:
    """Generate simulated sector performance"""
    sectors = list(set(s['sector'] for s in SYMBOLS_UNIVERSE))
    return {sector: random_range(-1.5, 1.5) for sector in sectors}


def generate_daily_stats(current_price: float) -> DailyStats:
    """Generate daily statistics"""
    previous_close = current_price / (1 + random_range(-0.02, 0.02))
    return DailyStats(
        sma20=current_price * random_range(0.95, 1.05),
        sma50=current_price * random_range(0.90, 1.10),
        sma200=current_price * random_range(0.80, 1.20),
        week52High=current_price * random_range(1.0, 1.3),
        week52Low=current_price * random_range(0.6, 0.9),
        avgVolume=int(random_range(100000, 2000000)),
        previousClose=previous_close,
        openPrice=previous_close * (1 + random_range(-0.01, 0.01))
    )


def generate_strategies(
    history: List[OHLC],
    rsi: float,
    rvol: float,
    change_percent: float,
    stats: DailyStats,
    sector_change: float
) -> List[StrategyResult]:
    """Generate trading strategy signals"""
    results = []
    
    if len(history) < 2:
        return results
    
    latest = history[-1]
    prev = history[-2]
    
    close = latest.close
    vwap = latest.vwap or close
    ema9 = latest.ema9 or close
    ema20 = latest.ema20 or close
    
    # 1. VWAP Trend + Pullback
    if close > vwap and ema9 > ema20:
        dist_to_vwap = (close - vwap) / vwap
        if abs(dist_to_vwap) < 0.002:  # Within 0.2% of VWAP
            results.append(StrategyResult(
                strategy="Pullback",
                signal="BUY",
                score=85,
                reason="Pullback to VWAP in Uptrend"
            ))
        else:
            results.append(StrategyResult(
                strategy="VWAP/EMA Trend",
                signal="BUY",
                score=75,
                reason="Price > VWAP & EMA9 > EMA20"
            ))
    elif close < vwap and ema9 < ema20:
        results.append(StrategyResult(
            strategy="VWAP/EMA Trend",
            signal="SELL",
            score=75,
            reason="Price < VWAP & EMA9 < EMA20"
        ))
    
    # 2. Momentum Breakout (20-bar high/low)
    if len(history) > 20:
        recent_high = max(h.high for h in history[-21:-1])
        recent_low = min(h.low for h in history[-21:-1])
        
        if close > recent_high and rvol > 1.5:
            results.append(StrategyResult(
                strategy="Momentum Breakout",
                signal="BUY",
                score=80,
                reason="Breakout above 20-bar high + Vol"
            ))
        elif close < recent_low and rvol > 1.5:
            results.append(StrategyResult(
                strategy="Momentum Breakout",
                signal="SELL",
                score=80,
                reason="Breakdown below 20-bar low + Vol"
            ))
    
    # 3. Gap and Go
    if stats.previousClose > 0:
        gap_percent = (stats.openPrice - stats.previousClose) / stats.previousClose * 100
        if abs(gap_percent) > 1.5:
            if gap_percent > 0 and close > stats.openPrice and rvol > 2.0:
                results.append(StrategyResult(
                    strategy="Gap & Go",
                    signal="BUY",
                    score=90,
                    reason=f"Gap Up {gap_percent:.1f}% & Holding"
                ))
            elif gap_percent < 0 and close < stats.openPrice and rvol > 2.0:
                results.append(StrategyResult(
                    strategy="Gap & Go",
                    signal="SELL",
                    score=90,
                    reason=f"Gap Down {abs(gap_percent):.1f}% & Weak"
                ))
    
    # 4. RSI Reversal
    if rsi > 80:
        results.append(StrategyResult(
            strategy="RSI Reversal",
            signal="SELL",
            score=85,
            reason=f"Extreme Overbought RSI ({rsi:.0f})"
        ))
    elif rsi < 20:
        results.append(StrategyResult(
            strategy="RSI Reversal",
            signal="BUY",
            score=88,
            reason=f"Extreme Oversold RSI ({rsi:.0f})"
        ))
    
    # 5. Volume Spike
    if rvol > 3.0:
        results.append(StrategyResult(
            strategy="Volume Spike",
            signal="BUY" if change_percent > 0 else "SELL",
            score=92,
            reason=f"Massive Volume ({rvol:.1f}x)"
        ))
    
    # 6. Sector Alignment
    if change_percent > 0 and sector_change > 0.5 and close > vwap:
        results.append(StrategyResult(
            strategy="Sector Alignment",
            signal="BUY",
            score=80,
            reason=f"Stock & Sector (+{sector_change:.1f}%) Aligned"
        ))
    elif change_percent < 0 and sector_change < -0.5 and close < vwap:
        results.append(StrategyResult(
            strategy="Sector Alignment",
            signal="SELL",
            score=80,
            reason=f"Stock & Sector ({sector_change:.1f}%) Aligned"
        ))
    
    return results


def fetch_market_data(symbols: Optional[List[Dict]] = None) -> List[StockData]:
    """
    Fetch simulated market data for given symbols.
    
    Args:
        symbols: Optional list of symbol dicts. If None, uses SYMBOLS_UNIVERSE.
    """
    global _current_sector_performance
    
    if _current_sector_performance is None:
        _current_sector_performance = generate_sector_performance()
    
    # Use provided symbols or fallback to universe
    stock_list = symbols if symbols else SYMBOLS_UNIVERSE
    
    stocks = []
    
    for stock_info in stock_list:
        base_price = random_range(100, 3000)
        change_percent = random_range(-3, 3)
        current_price = base_price * (1 + change_percent / 100)
        history = generate_intraday_data(base_price)
        
        rsi = random_range(15, 85)
        rvol = random_range(0.5, 4.0)
        stats = generate_daily_stats(current_price)
        
        sector_change = _current_sector_performance.get(stock_info['sector'], 0)
        
        strategies = generate_strategies(history, rsi, rvol, change_percent, stats, sector_change)
        patterns = detect_patterns(history)
        
        # Determine overall signal
        buy_count = sum(1 for s in strategies if s.signal == "BUY")
        sell_count = sum(1 for s in strategies if s.signal == "SELL")
        
        if buy_count > sell_count and buy_count >= 1:
            overall_signal = "BUY"
        elif sell_count > buy_count and sell_count >= 1:
            overall_signal = "SELL"
        else:
            overall_signal = "NEUTRAL"
        
        stocks.append(StockData(
            symbol=stock_info['symbol'],
            name=stock_info['name'],
            sector=stock_info['sector'],
            price=current_price,
            changePercent=change_percent,
            volume=int(random_range(500000, 5000000)),
            rvol=rvol,
            rsi=rsi,
            history=history,
            activeStrategies=strategies,
            activePatterns=patterns,
            overallSignal=overall_signal,
            stats=stats
        ))
    
    return stocks


def simulate_live_market(current_stocks: List[StockData]) -> List[StockData]:
    """Simulate real-time tick updates"""
    updated_stocks = []
    
    for stock in current_stocks:
        # Update ~40% of stocks per tick
        if random.random() > 0.4:
            updated_stocks.append(stock)
            continue
        
        # Micro-movement (0.03% max volatility)
        volatility = stock.price * 0.0003
        change = random_range(-volatility, volatility)
        new_price = max(0.05, stock.price + change)
        
        # Update change %
        percent_delta = (change / stock.price) * 100
        new_change_percent = stock.changePercent + percent_delta
        
        # Update volume
        volume_add = int(random.random() * 2500)
        new_volume = stock.volume + volume_add
        
        # Drift RSI
        new_rsi = max(0, min(100, stock.rsi + random_range(-1, 1)))
        
        # Update last candle
        if stock.history:
            last_candle = stock.history[-1]
            new_last = OHLC(
                time=last_candle.time,
                open=last_candle.open,
                high=max(last_candle.high, new_price),
                low=min(last_candle.low, new_price),
                close=new_price,
                volume=last_candle.volume + volume_add,
                vwap=last_candle.vwap,
                ema9=last_candle.ema9,
                ema20=last_candle.ema20
            )
            new_history = stock.history[:-1] + [new_last]
        else:
            new_history = stock.history
        
        # Re-detect patterns
        new_patterns = detect_patterns(new_history)
        
        # Re-run strategies
        sector_change = _current_sector_performance.get(stock.sector, 0) if _current_sector_performance else 0
        new_strategies = generate_strategies(new_history, new_rsi, stock.rvol, new_change_percent, stock.stats, sector_change)
        
        # Recalculate overall signal
        buy_count = sum(1 for s in new_strategies if s.signal == "BUY")
        sell_count = sum(1 for s in new_strategies if s.signal == "SELL")
        
        if buy_count > sell_count and buy_count >= 1:
            overall_signal = "BUY"
        elif sell_count > buy_count and sell_count >= 1:
            overall_signal = "SELL"
        else:
            overall_signal = "NEUTRAL"
        
        updated_stocks.append(StockData(
            symbol=stock.symbol,
            name=stock.name,
            sector=stock.sector,
            price=new_price,
            changePercent=new_change_percent,
            volume=new_volume,
            rvol=stock.rvol,
            rsi=new_rsi,
            history=new_history,
            activeStrategies=new_strategies,
            activePatterns=new_patterns,
            overallSignal=overall_signal,
            stats=stock.stats
        ))
    
    return updated_stocks
