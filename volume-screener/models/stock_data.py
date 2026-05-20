"""
Stock Data Models for Gamma Screener
Python dataclasses matching React TypeScript types
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
import numpy as np


class SignalType(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NEUTRAL = "NEUTRAL"


class StrategyType(Enum):
    """Available trading strategies"""
    MOMENTUM_BREAKOUT = "Momentum Breakout"
    GAP_AND_GO = "Gap & Go"
    VWAP_EMA_TREND = "VWAP/EMA Trend"
    PULLBACK = "Pullback"
    REVERSAL_RSI = "RSI Reversal"
    VOLUME_SPIKE = "Volume Spike"
    SECTOR_ALIGNMENT = "Sector Alignment"


class ImpactLevel(Enum):
    """News impact levels"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class OHLC:
    """OHLC candlestick data with extended fields"""
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float] = None
    ema9: Optional[float] = None
    ema20: Optional[float] = None
    rsi: Optional[float] = None
    
    @property
    def range(self) -> float:
        """High-Low range"""
        return self.high - self.low
    
    @property
    def body(self) -> float:
        """Candle body size (absolute)"""
        return abs(self.close - self.open)
    
    @property
    def is_bullish(self) -> bool:
        """True if close > open"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """True if close < open"""
        return self.close < self.open
    
    @property
    def upper_shadow(self) -> float:
        """Upper wick length"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """Lower wick length"""
        return min(self.open, self.close) - self.low


@dataclass
class StockStats:
    """Stock statistical data"""
    sma20: float = 0.0
    sma50: float = 0.0
    sma200: float = 0.0
    week52High: float = 0.0
    week52Low: float = 0.0
    avgVolume: float = 0.0


@dataclass
class ActiveStrategy:
    """Active strategy signal"""
    strategy: str
    signal: SignalType
    reason: str
    score: int = 0


@dataclass
class StockData:
    """Complete stock data with all indicators and signals"""
    symbol: str
    name: str
    sector: str
    price: float
    changePercent: float
    volume: float
    rvol: float  # Relative volume
    rsi: float
    vwap: float
    ema9: float
    ema20: float
    overallSignal: SignalType
    activeStrategies: List[ActiveStrategy] = field(default_factory=list)
    activePatterns: List[str] = field(default_factory=list)
    history: List[OHLC] = field(default_factory=list)
    stats: StockStats = field(default_factory=StockStats)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "price": self.price,
            "changePercent": self.changePercent,
            "volume": self.volume,
            "rvol": self.rvol,
            "rsi": self.rsi,
            "vwap": self.vwap,
            "ema9": self.ema9,
            "ema20": self.ema20,
            "overallSignal": self.overallSignal.value,
            "activeStrategies": [
                {"strategy": s.strategy, "signal": s.signal.value, "reason": s.reason, "score": s.score}
                for s in self.activeStrategies
            ],
            "activePatterns": self.activePatterns,
            "stats": {
                "sma20": self.stats.sma20,
                "sma50": self.stats.sma50,
                "sma200": self.stats.sma200,
                "week52High": self.stats.week52High,
                "week52Low": self.stats.week52Low,
                "avgVolume": self.stats.avgVolume,
            }
        }


@dataclass
class ScreenerFilters:
    """Filters for classic screener"""
    priceMin: float = 0
    priceMax: float = 10000
    rsiMin: float = 0
    rsiMax: float = 100
    minVolume: float = 0
    aboveSMA20: bool = False
    aboveSMA50: bool = False
    aboveSMA200: bool = False
    onlyPositiveChange: bool = False
    
    def apply(self, stock: StockData) -> bool:
        """Apply filters to a stock, returns True if passes all filters"""
        if stock.price < self.priceMin or stock.price > self.priceMax:
            return False
        if stock.rsi < self.rsiMin or stock.rsi > self.rsiMax:
            return False
        if stock.volume < self.minVolume:
            return False
        if self.onlyPositiveChange and stock.changePercent < 0:
            return False
        if self.aboveSMA20 and stock.price < stock.stats.sma20:
            return False
        if self.aboveSMA50 and stock.price < stock.stats.sma50:
            return False
        if self.aboveSMA200 and stock.price < stock.stats.sma200:
            return False
        return True


@dataclass
class PredictionResult:
    """Result from price prediction model"""
    predictedClose: float
    rSquared: float  # Confidence (0-1)
    modelType: str = "Ridge Regression"
    featureNames: List[str] = field(default_factory=list)
    coefficients: List[float] = field(default_factory=list)


@dataclass
class NewsItem:
    """News item with sentiment"""
    id: str
    title: str
    summary: str
    source: str
    timestamp: str
    sentimentScore: float  # -1 to 1
    impact: ImpactLevel
    relatedSymbols: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
