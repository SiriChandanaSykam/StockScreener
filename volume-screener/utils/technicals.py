import numpy as np
import pandas as pd

def calculate_rsi(prices, period=14):
    """
    Calculate RSI (Relative Strength Index).
    Returns pandas Series for consistent indexing.
    """
    # Convert to pandas Series if not already
    if not isinstance(prices, pd.Series):
        prices = pd.Series(prices)
    
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    avg_gain = gain.rolling(period, min_periods=1).mean()
    avg_loss = loss.rolling(period, min_periods=1).mean()
    
    # Avoid division by zero
    avg_loss = avg_loss.replace(0, 1e-10)
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """
    Calculate MACD (Moving Average Convergence Divergence).
    Returns: (macd_line, signal_line, histogram) as pandas Series.
    """
    # Convert to pandas Series if not already
    if not isinstance(prices, pd.Series):
        prices = pd.Series(prices)
    
    ema_fast = prices.ewm(span=fast, min_periods=1, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, min_periods=1, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, min_periods=1, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_smoothed_ma(prices, window=20):
    """Calculate Simple Moving Average."""
    if not isinstance(prices, pd.Series):
        prices = pd.Series(prices)
    return prices.rolling(window, min_periods=1).mean()

def calculate_ema(prices, span=20):
    """Calculate Exponential Moving Average."""
    if not isinstance(prices, pd.Series):
        prices = pd.Series(prices)
    return prices.ewm(span=span, min_periods=1, adjust=False).mean()
