import pandas as pd
import numpy as np

def score_stock(df: pd.DataFrame):
    """
    Scores a stock based on technical indicators.
    Returns (score: int, signals: list[str])
    """
    # Guard against insufficient data (needs at least 20 rows for indicators)
    if len(df) < 20:
        return 0, ["Insufficient historical data for scoring (need 20+ days)"]
    
    score = 0
    signals = []
    
    try:
        close = df['Close'].values
        volume = df['Volume'].values
        
        # Volume spike detection (needs at least 20 days)
        if len(volume) >= 20:
            avg_vol_20 = np.mean(volume[-20:])
            avg_vol_3 = np.mean(volume[-3:])
            
            # Prevent division by zero
            if avg_vol_20 > 0:
                vol_ratio = avg_vol_3 / avg_vol_20
                
                if vol_ratio > 2:
                    score += 3
                    signals.append("🔥 High Volume")
                elif vol_ratio > 1.5:
                    score += 2
                    signals.append("📊 Moderate Volume Increase")
        
        # RSI calculation (needs at least 15 days)
        if len(close) >= 15:
            delta = np.diff(close)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            
            avg_gain = np.mean(gain[-14:])
            avg_loss = np.mean(loss[-14:])
            
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
                if rsi > 60:
                    score += 2
                    signals.append("💪 RSI Strong Momentum Zone")
                elif rsi < 30:
                    score += 1
                    signals.append("📉 RSI Oversold")
        
        # MACD calculation (needs at least 26 days)
        if len(close) >= 26:
            ema_12 = pd.Series(close).ewm(span=12, adjust=False).mean().iloc[-1]
            ema_26 = pd.Series(close).ewm(span=26, adjust=False).mean().iloc[-1]
            macd = ema_12 - ema_26
            
            if macd > 0:
                score += 2
                signals.append("⚡ MACD Above Signal")
        
        # Price momentum (1-day change)
        if len(close) >= 2:
            pct_change = ((close[-1] - close[-2]) / close[-2]) * 100
            
            if pct_change > 2:
                score += 2
                signals.append("☑️ Moderate 1 Day Move +2%")
            elif pct_change > 5:
                score += 3
                signals.append("🚀 Strong 1 Day Move +5%")
        
        # 20-day high breakout
        if len(close) >= 20:
            high_20 = np.max(close[-20:])
            if close[-1] >= high_20 * 0.98:  # Within 2% of 20-day high
                score += 2
                signals.append("🎉 20-Day High Breakout")
        
        # Moving average alignment (needs at least 50 days for proper analysis)
        if len(close) >= 50:
            ma_20 = np.mean(close[-20:])
            ma_50 = np.mean(close[-50:])
            
            if close[-1] > ma_20 > ma_50:
                score += 2
                signals.append("✅ Bullish MA Alignment")
        
    except Exception as e:
        return 0, [f"Scoring error: {str(e)}"]
    
    return score, signals
