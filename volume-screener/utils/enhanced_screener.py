"""
Enhanced Stock Screener
Implements 7 trading strategies with dual-mode scoring (Win Rate vs Risk-Adjusted)
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import sys
sys.path.append('..')

from utils.technicals import calculate_rsi, calculate_macd, calculate_smoothed_ma
from strategies.indicators import (
    calculate_ema, calculate_vwap, calculate_atr,
    calculate_relative_volume, calculate_bollinger_bands
)
from strategies.candlestick_patterns import detect_patterns
from utils.price_predictor import perform_regression_analysis, PredictionResult
from utils.strategy_meta import STRATEGY_META, get_stock_score, BiasLevel


@dataclass
class StrategySignal:
    """Signal from a trading strategy"""
    strategy: str
    signal: str  # "BUY", "SELL", "HOLD"
    reason: str
    score: int = 0  # Confidence 0-100


class EnhancedScreener:
    """
    Multi-strategy screener with 7 trading strategies.
    
    Strategies:
    1. Momentum Breakout - 20-bar high/low + high RVOL
    2. Gap & Go - Gap >1.5% detection
    3. VWAP/EMA Trend - Golden/Death crosses
    4. Pullback - VWAP retracement in trend
    5. RSI Reversal - Mean reversion at extremes
    6. Volume Spike - RVOL >3.0
    7. Sector Alignment - Industry trend validation
    """
    
    def __init__(self):
        self.strategies = {
            "Momentum Breakout": self._momentum_breakout,
            "Gap & Go": self._gap_and_go,
            "VWAP/EMA Trend": self._vwap_ema_trend,
            "Pullback": self._pullback,
            "RSI Reversal": self._rsi_reversal,
            "Volume Spike": self._volume_spike,
            "Sector Alignment": self._sector_alignment,
        }
    
    def analyze_stock(self, df: pd.DataFrame, sector_trend: str = "neutral") -> Dict:
        """
        Analyze a stock using all strategies.
        
        Args:
            df: DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)
            sector_trend: "bullish", "bearish", or "neutral"
        
        Returns:
            Dictionary with signals, patterns, prediction, and overall signal
        """
        if df.empty or len(df) < 20:
            return {
                "signals": [],
                "patterns": [],
                "prediction": None,
                "overall_signal": "NEUTRAL",
                "indicators": {}
            }
        
        # Calculate indicators
        indicators = self._calculate_indicators(df)
        
        # Run all strategies
        signals = []
        for name, strategy_func in self.strategies.items():
            try:
                signal = strategy_func(df, indicators, sector_trend)
                if signal:
                    signals.append(signal)
            except Exception as e:
                print(f"Error in strategy {name}: {e}")
        
        # Detect candlestick patterns
        ohlc_list = self._df_to_ohlc_list(df)
        patterns = detect_patterns(ohlc_list[-5:]) if len(ohlc_list) >= 5 else []
        
        # Get price prediction
        prediction = None
        try:
            ohlc_dicts = [
                {"open": o.open, "high": o.high, "low": o.low, 
                 "close": o.close, "volume": o.volume}
                for o in ohlc_list
            ]
            prediction = perform_regression_analysis(ohlc_dicts)
        except Exception as e:
            print(f"Prediction error: {e}")
        
        # Determine overall signal
        overall_signal = self._calculate_overall_signal(signals)
        
        return {
            "signals": signals,
            "patterns": patterns,
            "prediction": prediction,
            "overall_signal": overall_signal,
            "indicators": indicators
        }
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate all required technical indicators"""
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        volume = df['Volume'].values
        
        # RSI
        rsi = calculate_rsi(close, 14)
        
        # EMAs
        ema9 = calculate_ema(close, 9)
        ema20 = calculate_ema(close, 20)
        
        # VWAP
        vwap = calculate_vwap(df)
        
        # Relative Volume
        rvol = calculate_relative_volume(volume, 20)
        
        # ATR
        atr = calculate_atr(df, 14)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close, 20, 2.0)
        
        # SMAs
        sma20 = calculate_smoothed_ma(close, 20)
        sma50 = calculate_smoothed_ma(close, 50) if len(close) >= 50 else np.full(len(close), np.nan)
        
        return {
            "rsi": rsi[-1] if len(rsi) > 0 else 50,
            "ema9": ema9[-1] if len(ema9) > 0 else close[-1],
            "ema20": ema20[-1] if len(ema20) > 0 else close[-1],
            "vwap": vwap[-1] if len(vwap) > 0 else close[-1],
            "rvol": rvol[-1] if len(rvol) > 0 else 1.0,
            "atr": atr[-1] if len(atr) > 0 else 0,
            "bb_upper": bb_upper[-1] if len(bb_upper) > 0 else close[-1],
            "bb_lower": bb_lower[-1] if len(bb_lower) > 0 else close[-1],
            "sma20": sma20[-1] if len(sma20) > 0 else close[-1],
            "sma50": sma50[-1] if len(sma50) > 0 and not np.isnan(sma50[-1]) else close[-1],
            "close": close[-1],
            "high_20": np.max(high[-20:]) if len(high) >= 20 else np.max(high),
            "low_20": np.min(low[-20:]) if len(low) >= 20 else np.min(low),
            "prev_close": close[-2] if len(close) >= 2 else close[-1],
            "open": df['Open'].iloc[-1],
            "ema9_array": ema9,
            "ema20_array": ema20,
            "rsi_array": rsi,
        }
    
    def _momentum_breakout(self, df: pd.DataFrame, ind: Dict, 
                           sector_trend: str) -> Optional[StrategySignal]:
        """
        Momentum Breakout Strategy
        - Price breaks above 20-bar high with high RVOL (>2.0)
        - Or breaks below 20-bar low
        """
        close = ind["close"]
        high_20 = ind["high_20"]
        low_20 = ind["low_20"]
        rvol = ind["rvol"]
        
        if close > high_20 and rvol > 2.0:
            score = min(100, int(50 + rvol * 10))
            return StrategySignal(
                strategy="Momentum Breakout",
                signal="BUY",
                reason=f"Breakout above 20-bar high with RVOL {rvol:.1f}x",
                score=score
            )
        
        if close < low_20 and rvol > 2.0:
            score = min(100, int(50 + rvol * 10))
            return StrategySignal(
                strategy="Momentum Breakout",
                signal="SELL",
                reason=f"Breakdown below 20-bar low with RVOL {rvol:.1f}x",
                score=score
            )
        
        return None
    
    def _gap_and_go(self, df: pd.DataFrame, ind: Dict,
                    sector_trend: str) -> Optional[StrategySignal]:
        """
        Gap & Go Strategy
        - Gap up/down >1.5% from previous close
        - Continuation in gap direction
        """
        prev_close = ind["prev_close"]
        open_price = ind["open"]
        close = ind["close"]
        
        if prev_close == 0:
            return None
        
        gap_percent = ((open_price - prev_close) / prev_close) * 100
        
        # Gap up > 1.5% and price continuing higher
        if gap_percent > 1.5 and close > open_price:
            score = min(100, int(50 + abs(gap_percent) * 10))
            return StrategySignal(
                strategy="Gap & Go",
                signal="BUY",
                reason=f"Gap up {gap_percent:.1f}% with bullish continuation",
                score=score
            )
        
        # Gap down > 1.5% and price continuing lower
        if gap_percent < -1.5 and close < open_price:
            score = min(100, int(50 + abs(gap_percent) * 10))
            return StrategySignal(
                strategy="Gap & Go",
                signal="SELL",
                reason=f"Gap down {abs(gap_percent):.1f}% with bearish continuation",
                score=score
            )
        
        return None
    
    def _vwap_ema_trend(self, df: pd.DataFrame, ind: Dict,
                        sector_trend: str) -> Optional[StrategySignal]:
        """
        VWAP/EMA Trend Strategy
        - Golden Cross: EMA9 crosses above EMA20, price above VWAP
        - Death Cross: EMA9 crosses below EMA20, price below VWAP
        """
        close = ind["close"]
        ema9 = ind["ema9"]
        ema20 = ind["ema20"]
        vwap = ind["vwap"]
        
        ema9_arr = ind["ema9_array"]
        ema20_arr = ind["ema20_array"]
        
        if len(ema9_arr) < 2 or len(ema20_arr) < 2:
            return None
        
        # Check for cross
        prev_diff = ema9_arr[-2] - ema20_arr[-2]
        curr_diff = ema9_arr[-1] - ema20_arr[-1]
        
        # Golden Cross
        if prev_diff <= 0 and curr_diff > 0 and close > vwap:
            return StrategySignal(
                strategy="VWAP/EMA Trend",
                signal="BUY",
                reason="Golden Cross (EMA9 > EMA20) above VWAP",
                score=75
            )
        
        # Death Cross
        if prev_diff >= 0 and curr_diff < 0 and close < vwap:
            return StrategySignal(
                strategy="VWAP/EMA Trend",
                signal="SELL",
                reason="Death Cross (EMA9 < EMA20) below VWAP",
                score=75
            )
        
        # Trend confirmation without cross
        if ema9 > ema20 and close > vwap:
            return StrategySignal(
                strategy="VWAP/EMA Trend",
                signal="BUY",
                reason="Uptrend: Price above VWAP and EMA9 > EMA20",
                score=60
            )
        
        if ema9 < ema20 and close < vwap:
            return StrategySignal(
                strategy="VWAP/EMA Trend",
                signal="SELL",
                reason="Downtrend: Price below VWAP and EMA9 < EMA20",
                score=60
            )
        
        return None
    
    def _pullback(self, df: pd.DataFrame, ind: Dict,
                  sector_trend: str) -> Optional[StrategySignal]:
        """
        Pullback Strategy
        - Price in uptrend (above EMA20)
        - Pullback to VWAP or EMA20
        - Bounce confirmation
        """
        close = ind["close"]
        ema20 = ind["ema20"]
        vwap = ind["vwap"]
        rsi = ind["rsi"]
        
        close_arr = df['Close'].values
        
        # Check for uptrend (price was above EMA20 for most of recent bars)
        if len(close_arr) < 10:
            return None
        
        avg_position = np.mean(close_arr[-10:] > ind["ema20_array"][-10:])
        
        # Bullish pullback: In uptrend, touching VWAP, RSI not overbought
        if avg_position > 0.7 and abs(close - vwap) / vwap < 0.005 and rsi < 65:
            return StrategySignal(
                strategy="Pullback",
                signal="BUY",
                reason="Pullback to VWAP in uptrend",
                score=70
            )
        
        # Bearish pullback: In downtrend, touching VWAP, RSI not oversold
        if avg_position < 0.3 and abs(close - vwap) / vwap < 0.005 and rsi > 35:
            return StrategySignal(
                strategy="Pullback",
                signal="SELL",
                reason="Pullback to VWAP in downtrend",
                score=70
            )
        
        return None
    
    def _rsi_reversal(self, df: pd.DataFrame, ind: Dict,
                      sector_trend: str) -> Optional[StrategySignal]:
        """
        RSI Reversal Strategy
        - RSI < 20: Oversold, potential bullish reversal
        - RSI > 80: Overbought, potential bearish reversal
        """
        rsi = ind["rsi"]
        rsi_arr = ind["rsi_array"]
        
        if len(rsi_arr) < 2:
            return None
        
        # Bullish reversal: RSI was below 20 and turning up
        if rsi < 30 and rsi > rsi_arr[-2]:
            score = int(80 - rsi)  # Lower RSI = higher score
            return StrategySignal(
                strategy="RSI Reversal",
                signal="BUY",
                reason=f"Oversold bounce: RSI {rsi:.0f} turning up",
                score=score
            )
        
        # Bearish reversal: RSI was above 80 and turning down
        if rsi > 70 and rsi < rsi_arr[-2]:
            score = int(rsi - 20)  # Higher RSI = higher score
            return StrategySignal(
                strategy="RSI Reversal",
                signal="SELL",
                reason=f"Overbought reversal: RSI {rsi:.0f} turning down",
                score=score
            )
        
        return None
    
    def _volume_spike(self, df: pd.DataFrame, ind: Dict,
                      sector_trend: str) -> Optional[StrategySignal]:
        """
        Volume Spike Strategy
        - RVOL > 3.0 indicates unusual activity
        - Direction determined by price action
        """
        rvol = ind["rvol"]
        close = ind["close"]
        open_price = ind["open"]
        
        if rvol < 3.0:
            return None
        
        score = min(100, int(50 + rvol * 10))
        
        if close > open_price:
            return StrategySignal(
                strategy="Volume Spike",
                signal="BUY",
                reason=f"Unusual volume {rvol:.1f}x with bullish price action",
                score=score
            )
        
        if close < open_price:
            return StrategySignal(
                strategy="Volume Spike",
                signal="SELL",
                reason=f"Unusual volume {rvol:.1f}x with bearish price action",
                score=score
            )
        
        return None
    
    def _sector_alignment(self, df: pd.DataFrame, ind: Dict,
                          sector_trend: str) -> Optional[StrategySignal]:
        """
        Sector Alignment Strategy
        - Validates trade against broader sector trend
        - Acts as a booster/filter for other signals
        """
        close = ind["close"]
        ema20 = ind["ema20"]
        
        stock_trend = "bullish" if close > ema20 else "bearish"
        
        if stock_trend == sector_trend and sector_trend == "bullish":
            return StrategySignal(
                strategy="Sector Alignment",
                signal="BUY",
                reason="Stock and sector both bullish",
                score=50
            )
        
        if stock_trend == sector_trend and sector_trend == "bearish":
            return StrategySignal(
                strategy="Sector Alignment",
                signal="SELL",
                reason="Stock and sector both bearish",
                score=50
            )
        
        return None
    
    def _calculate_overall_signal(self, signals: List[StrategySignal]) -> str:
        """Calculate overall signal from individual strategy signals"""
        if not signals:
            return "NEUTRAL"
        
        buy_score = sum(s.score for s in signals if s.signal == "BUY")
        sell_score = sum(s.score for s in signals if s.signal == "SELL")
        
        if buy_score > sell_score and buy_score > 50:
            return "BUY"
        elif sell_score > buy_score and sell_score > 50:
            return "SELL"
        else:
            return "HOLD"
    
    def _df_to_ohlc_list(self, df: pd.DataFrame) -> List:
        """Convert DataFrame to list of OHLC-like objects"""
        @dataclass
        class OHLCTemp:
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
        
        ohlc_list = []
        for idx, row in df.iterrows():
            ohlc_list.append(OHLCTemp(
                time=str(idx),
                open=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                volume=row['Volume']
            ))
        return ohlc_list


def screen_stocks(stock_data_list: List[Dict], mode: str = "WIN_RATE") -> List[Dict]:
    """
    Screen multiple stocks and sort by strategy score.
    
    Args:
        stock_data_list: List of dicts with 'symbol', 'df' (DataFrame), 'sector_trend'
        mode: "WIN_RATE" or "RISK_ADJUSTED"
    
    Returns:
        Sorted list of analysis results
    """
    screener = EnhancedScreener()
    results = []
    
    for stock_info in stock_data_list:
        symbol = stock_info.get('symbol', 'UNKNOWN')
        df = stock_info.get('df')
        sector_trend = stock_info.get('sector_trend', 'neutral')
        
        if df is None or df.empty:
            continue
        
        analysis = screener.analyze_stock(df, sector_trend)
        
        # Calculate score based on mode
        score = get_stock_score(analysis['signals'], mode)
        
        results.append({
            'symbol': symbol,
            'score': score,
            **analysis
        })
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results


def get_top_predictions(stock_data_list: List[Dict], top_n: int = 3) -> List[Dict]:
    """
    Get stocks with highest predicted upside.
    
    Args:
        stock_data_list: List of dicts with 'symbol', 'df', 'current_price'
        top_n: Number of top predictions to return
    
    Returns:
        List of prediction results sorted by upside
    """
    predictions = []
    
    for stock_info in stock_data_list:
        symbol = stock_info.get('symbol', 'UNKNOWN')
        df = stock_info.get('df')
        current_price = stock_info.get('current_price', 0)
        
        if df is None or df.empty or current_price <= 0:
            continue
        
        try:
            ohlc_dicts = [
                {"open": row['Open'], "high": row['High'], 
                 "low": row['Low'], "close": row['Close'], 
                 "volume": row['Volume']}
                for _, row in df.iterrows()
            ]
            
            result = perform_regression_analysis(ohlc_dicts)
            
            if result:
                upside = ((result.predictedClose - current_price) / current_price) * 100
                predictions.append({
                    'symbol': symbol,
                    'price': current_price,
                    'predictedClose': result.predictedClose,
                    'upside': upside,
                    'confidence': result.rSquared
                })
        except Exception as e:
            print(f"Prediction error for {symbol}: {e}")
    
    # Sort by upside (highest first)
    predictions.sort(key=lambda x: x['upside'], reverse=True)
    
    return predictions[:top_n]
