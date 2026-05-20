"""
Strategy Metadata Configuration
Defines win rate and risk-adjusted biases for scoring
"""

from enum import Enum
from typing import Dict, Literal
from dataclasses import dataclass


class BiasLevel(Enum):
    """Strategy bias levels for scoring"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    BOOSTER = "BOOSTER"


@dataclass
class StrategyMeta:
    """Metadata for a trading strategy"""
    style: str
    win_rate_bias: BiasLevel
    risk_adjusted_bias: BiasLevel
    
    # Score weights for different modes
    @property
    def win_rate_score(self) -> int:
        """Score contribution in WIN_RATE mode"""
        if self.win_rate_bias == BiasLevel.HIGH:
            return 10
        elif self.win_rate_bias == BiasLevel.MEDIUM:
            return 5
        else:  # BOOSTER
            return 3
    
    @property
    def risk_adjusted_score(self) -> int:
        """Score contribution in RISK_ADJUSTED mode"""
        if self.risk_adjusted_bias == BiasLevel.HIGH:
            return 10
        elif self.risk_adjusted_bias == BiasLevel.MEDIUM:
            return 5
        else:  # BOOSTER
            return 3


# Strategy metadata matching React constants.ts
STRATEGY_META: Dict[str, StrategyMeta] = {
    "RSI Reversal": StrategyMeta(
        style="Mean Reversion",
        win_rate_bias=BiasLevel.HIGH,
        risk_adjusted_bias=BiasLevel.MEDIUM
    ),
    "VWAP/EMA Trend": StrategyMeta(
        style="Trend",
        win_rate_bias=BiasLevel.HIGH,
        risk_adjusted_bias=BiasLevel.HIGH
    ),
    "Pullback": StrategyMeta(
        style="Trend",
        win_rate_bias=BiasLevel.HIGH,
        risk_adjusted_bias=BiasLevel.HIGH
    ),
    "Sector Alignment": StrategyMeta(
        style="Filter",
        win_rate_bias=BiasLevel.BOOSTER,
        risk_adjusted_bias=BiasLevel.BOOSTER
    ),
    "Momentum Breakout": StrategyMeta(
        style="Momentum",
        win_rate_bias=BiasLevel.MEDIUM,
        risk_adjusted_bias=BiasLevel.HIGH
    ),
    "Gap & Go": StrategyMeta(
        style="Momentum",
        win_rate_bias=BiasLevel.MEDIUM,
        risk_adjusted_bias=BiasLevel.HIGH
    ),
    "Volume Spike": StrategyMeta(
        style="Vol",
        win_rate_bias=BiasLevel.MEDIUM,
        risk_adjusted_bias=BiasLevel.MEDIUM
    ),
}


# Stock universe matching React constants.ts
SYMBOLS_UNIVERSE = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Energy"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Financials"},
    {"symbol": "INFY", "name": "Infosys", "sector": "Technology"},
    {"symbol": "TCS", "name": "Tata Consultancy Svcs", "sector": "Technology"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Financials"},
    {"symbol": "ITC", "name": "ITC Limited", "sector": "Consumer Goods"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Financials"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
    {"symbol": "LICI", "name": "LIC India", "sector": "Financials"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors", "sector": "Auto"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises", "sector": "Metals & Mining"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Financials"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Auto"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharma", "sector": "Healthcare"},
    {"symbol": "AXISBANK", "name": "Axis Bank", "sector": "Financials"},
]


def get_stock_score(active_strategies: list, mode: str = "WIN_RATE") -> int:
    """
    Calculate stock score based on active strategies and scoring mode.
    
    Args:
        active_strategies: List of ActiveStrategy objects with 'strategy' attribute
        mode: "WIN_RATE" or "RISK_ADJUSTED"
    
    Returns:
        Total score for the stock
    """
    score = 0
    
    for strategy in active_strategies:
        strategy_name = strategy.strategy if hasattr(strategy, 'strategy') else strategy.get('strategy', '')
        meta = STRATEGY_META.get(strategy_name)
        
        if meta:
            if mode == "WIN_RATE":
                score += meta.win_rate_score
            else:
                score += meta.risk_adjusted_score
    
    return score


def sort_stocks_by_score(stocks: list, mode: str = "WIN_RATE") -> list:
    """
    Sort stocks by their strategy score.
    
    Args:
        stocks: List of StockData objects
        mode: "WIN_RATE" or "RISK_ADJUSTED"
    
    Returns:
        Sorted list of stocks (highest score first)
    """
    return sorted(
        stocks,
        key=lambda s: get_stock_score(s.activeStrategies, mode),
        reverse=True
    )
