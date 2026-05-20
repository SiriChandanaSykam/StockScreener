"""
Candlestick Pattern Recognition Engine
Detects 15+ classic candlestick patterns for trading signals
"""

from typing import List, Tuple
from dataclasses import dataclass
import sys
sys.path.append('..')

try:
    from models.stock_data import OHLC
except ImportError:
    # Fallback for standalone testing
    @dataclass
    class OHLC:
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


def is_doji(candle: OHLC, threshold: float = 0.1) -> bool:
    """
    Doji: Very small body relative to range
    Indicates indecision
    """
    if candle.range == 0:
        return False
    body_ratio = candle.body / candle.range
    return body_ratio < threshold


def is_hammer(candle: OHLC) -> bool:
    """
    Hammer (Bullish): 
    - Small body at top
    - Long lower shadow (>= 2x body)
    - Little to no upper shadow
    """
    if candle.range == 0 or candle.body == 0:
        return False
    
    lower_shadow = candle.lower_shadow
    upper_shadow = candle.upper_shadow
    body = candle.body
    
    return (
        lower_shadow >= 2 * body and
        upper_shadow <= body * 0.3 and
        body / candle.range < 0.4
    )


def is_shooting_star(candle: OHLC) -> bool:
    """
    Shooting Star (Bearish):
    - Small body at bottom
    - Long upper shadow (>= 2x body)
    - Little to no lower shadow
    """
    if candle.range == 0 or candle.body == 0:
        return False
    
    lower_shadow = candle.lower_shadow
    upper_shadow = candle.upper_shadow
    body = candle.body
    
    return (
        upper_shadow >= 2 * body and
        lower_shadow <= body * 0.3 and
        body / candle.range < 0.4
    )


def is_marubozu(candle: OHLC, threshold: float = 0.05) -> Tuple[bool, str]:
    """
    Marubozu: Strong candle with no shadows
    Returns (is_marubozu, direction)
    """
    if candle.range == 0:
        return False, ""
    
    shadow_ratio = (candle.upper_shadow + candle.lower_shadow) / candle.range
    
    if shadow_ratio <= threshold:
        if candle.is_bullish:
            return True, "Bullish Marubozu"
        else:
            return True, "Bearish Marubozu"
    return False, ""


def is_bullish_engulfing(prev: OHLC, curr: OHLC) -> bool:
    """
    Bullish Engulfing:
    - Previous candle is bearish
    - Current candle is bullish
    - Current body completely engulfs previous body
    """
    return (
        prev.is_bearish and
        curr.is_bullish and
        curr.open < prev.close and
        curr.close > prev.open
    )


def is_bearish_engulfing(prev: OHLC, curr: OHLC) -> bool:
    """
    Bearish Engulfing:
    - Previous candle is bullish
    - Current candle is bearish
    - Current body completely engulfs previous body
    """
    return (
        prev.is_bullish and
        curr.is_bearish and
        curr.open > prev.close and
        curr.close < prev.open
    )


def is_bullish_harami(prev: OHLC, curr: OHLC) -> bool:
    """
    Bullish Harami:
    - Previous candle is bearish with large body
    - Current candle is bullish with small body inside previous
    """
    return (
        prev.is_bearish and
        curr.is_bullish and
        curr.open > prev.close and
        curr.close < prev.open and
        curr.body < prev.body * 0.5
    )


def is_bearish_harami(prev: OHLC, curr: OHLC) -> bool:
    """
    Bearish Harami:
    - Previous candle is bullish with large body
    - Current candle is bearish with small body inside previous
    """
    return (
        prev.is_bullish and
        curr.is_bearish and
        curr.open < prev.close and
        curr.close > prev.open and
        curr.body < prev.body * 0.5
    )


def is_morning_star(c1: OHLC, c2: OHLC, c3: OHLC) -> bool:
    """
    Morning Star (Bullish Reversal):
    1. First candle: Long bearish
    2. Second candle: Small body (gaps down)
    3. Third candle: Long bullish, closes into first candle
    """
    # First is bearish with significant body
    if not c1.is_bearish or c1.body < c1.range * 0.5:
        return False
    
    # Second has small body (doji-like)
    if c2.body > c2.range * 0.3 and c2.range > 0:
        return False
    
    # Third is bullish and closes into first candle's body
    if not c3.is_bullish or c3.body < c3.range * 0.5:
        return False
    
    return c3.close > (c1.open + c1.close) / 2


def is_evening_star(c1: OHLC, c2: OHLC, c3: OHLC) -> bool:
    """
    Evening Star (Bearish Reversal):
    1. First candle: Long bullish
    2. Second candle: Small body (gaps up)
    3. Third candle: Long bearish, closes into first candle
    """
    # First is bullish with significant body
    if not c1.is_bullish or c1.body < c1.range * 0.5:
        return False
    
    # Second has small body
    if c2.body > c2.range * 0.3 and c2.range > 0:
        return False
    
    # Third is bearish and closes into first candle's body
    if not c3.is_bearish or c3.body < c3.range * 0.5:
        return False
    
    return c3.close < (c1.open + c1.close) / 2


def is_three_white_soldiers(c1: OHLC, c2: OHLC, c3: OHLC) -> bool:
    """
    Three White Soldiers (Strong Bullish):
    - Three consecutive bullish candles
    - Each opens within previous body
    - Each closes higher than previous
    """
    # All three must be bullish
    if not (c1.is_bullish and c2.is_bullish and c3.is_bullish):
        return False
    
    # Each should have substantial body
    if c1.body < c1.range * 0.5 or c2.body < c2.range * 0.5 or c3.body < c3.range * 0.5:
        return False
    
    # Progressive closes
    return c2.close > c1.close and c3.close > c2.close


def is_three_black_crows(c1: OHLC, c2: OHLC, c3: OHLC) -> bool:
    """
    Three Black Crows (Strong Bearish):
    - Three consecutive bearish candles
    - Each opens within previous body
    - Each closes lower than previous
    """
    # All three must be bearish
    if not (c1.is_bearish and c2.is_bearish and c3.is_bearish):
        return False
    
    # Each should have substantial body
    if c1.body < c1.range * 0.5 or c2.body < c2.range * 0.5 or c3.body < c3.range * 0.5:
        return False
    
    # Progressive closes
    return c2.close < c1.close and c3.close < c2.close


def is_piercing_pattern(prev: OHLC, curr: OHLC) -> bool:
    """
    Piercing Pattern (Bullish Reversal):
    - Previous is bearish
    - Current opens below previous low
    - Current closes above midpoint of previous body
    """
    if not (prev.is_bearish and curr.is_bullish):
        return False
    
    prev_midpoint = (prev.open + prev.close) / 2
    return curr.open < prev.low and curr.close > prev_midpoint


def is_dark_cloud_cover(prev: OHLC, curr: OHLC) -> bool:
    """
    Dark Cloud Cover (Bearish Reversal):
    - Previous is bullish
    - Current opens above previous high
    - Current closes below midpoint of previous body
    """
    if not (prev.is_bullish and curr.is_bearish):
        return False
    
    prev_midpoint = (prev.open + prev.close) / 2
    return curr.open > prev.high and curr.close < prev_midpoint


def detect_patterns(candles: List[OHLC]) -> List[str]:
    """
    Scan candles and return list of detected patterns.
    Typically scans last 3-5 candles.
    
    Args:
        candles: List of OHLC candles (most recent last)
    
    Returns:
        List of pattern names detected
    """
    patterns = []
    
    if len(candles) < 1:
        return patterns
    
    # Get recent candles
    curr = candles[-1]
    
    # Single candle patterns
    if is_doji(curr):
        patterns.append("Doji")
    
    if is_hammer(curr):
        patterns.append("Hammer")
    
    if is_shooting_star(curr):
        patterns.append("Shooting Star")
    
    is_maru, maru_type = is_marubozu(curr)
    if is_maru:
        patterns.append(maru_type)
    
    # Two candle patterns
    if len(candles) >= 2:
        prev = candles[-2]
        
        if is_bullish_engulfing(prev, curr):
            patterns.append("Bullish Engulfing")
        
        if is_bearish_engulfing(prev, curr):
            patterns.append("Bearish Engulfing")
        
        if is_bullish_harami(prev, curr):
            patterns.append("Bullish Harami")
        
        if is_bearish_harami(prev, curr):
            patterns.append("Bearish Harami")
        
        if is_piercing_pattern(prev, curr):
            patterns.append("Piercing Pattern")
        
        if is_dark_cloud_cover(prev, curr):
            patterns.append("Dark Cloud Cover")
    
    # Three candle patterns
    if len(candles) >= 3:
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        if is_morning_star(c1, c2, c3):
            patterns.append("Morning Star")
        
        if is_evening_star(c1, c2, c3):
            patterns.append("Evening Star")
        
        if is_three_white_soldiers(c1, c2, c3):
            patterns.append("Three White Soldiers")
        
        if is_three_black_crows(c1, c2, c3):
            patterns.append("Three Black Crows")
    
    return patterns


def get_pattern_bias(pattern: str) -> str:
    """
    Get the bias (bullish/bearish/neutral) for a pattern.
    
    Args:
        pattern: Pattern name
    
    Returns:
        "bullish", "bearish", or "neutral"
    """
    bullish_keywords = ['bullish', 'hammer', 'morning', 'piercing', 'soldiers', 'white']
    bearish_keywords = ['bearish', 'shooting', 'evening', 'cloud', 'crows', 'black']
    
    pattern_lower = pattern.lower()
    
    if any(kw in pattern_lower for kw in bullish_keywords):
        return "bullish"
    elif any(kw in pattern_lower for kw in bearish_keywords):
        return "bearish"
    else:
        return "neutral"
