"""
Enhanced Data Fetcher with Multiple Sources
Supports: yfinance, NSE API (all series), persistent disk cache
"""

import yfinance as yf
from datetime import date, timedelta, datetime
import pandas as pd
import requests
import time
import random
import os
import json
from pathlib import Path

# ---------- Configuration ----------

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Cache directories
CACHE_DIR = Path(__file__).parent.parent / "assets" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory cache of failed symbols (reset every 30 minutes)
_failed_symbols = set()
_failed_symbols_expire = None

# Persistent cache of known-failed symbols (delisted/invalid)
FAILED_SYMBOLS_FILE = CACHE_DIR / "_failed_symbols.json"


def _load_persistent_failed():
    """Load known-failed symbols from disk"""
    try:
        if FAILED_SYMBOLS_FILE.exists():
            with open(FAILED_SYMBOLS_FILE, 'r') as f:
                data = json.load(f)
                # Only use if less than 7 days old
                if data.get('updated') and (datetime.now() - datetime.fromisoformat(data['updated'])).days < 7:
                    return set(data.get('symbols', []))
    except:
        pass
    return set()


def _save_persistent_failed(symbols: set):
    """Save known-failed symbols to disk"""
    try:
        with open(FAILED_SYMBOLS_FILE, 'w') as f:
            json.dump({
                'updated': datetime.now().isoformat(),
                'symbols': list(symbols)[:500]  # Keep max 500
            }, f)
    except:
        pass


_persistent_failed = _load_persistent_failed()


# ---------- yfinance source ----------

def _fetch_from_yfinance(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """Try NSE then BSE using yfinance."""
    for suffix in [".NS", ".BO"]:
        try:
            ticker = yf.Ticker(f"{symbol}{suffix}")
            df = ticker.history(period=period)
            if not df.empty and len(df) >= 5:
                return df
        except:
            continue
    return pd.DataFrame()


# ---------- NSE API with multi-series support ----------

def _fetch_from_nse_api(symbol: str, days: int = 90) -> pd.DataFrame:
    """
    Enhanced NSE API that tries multiple series:
    - EQ: Regular equity (mainboard)
    - SM: SME Emerge  
    - ST: SME Trade to Trade (CRITICAL for stocks like SHYAMDHANI)
    - BE: Trade to Trade (SME)
    - BZ: Trade to Trade (mainboard)
    """
    base = "https://www.nseindia.com"
    series_to_try = ["EQ", "SM", "ST", "BE", "BZ"]  # Added ST for SME Trade stocks
    
    # Create session with cookies
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": base,
        })
        
        # Get initial cookies
        r = s.get(base, timeout=10)
        if r.status_code != 200:
            return pd.DataFrame()
        
        time.sleep(0.5)  # Brief pause for cookies
        
        from_date = (datetime.now() - timedelta(days=days)).strftime('%d-%m-%Y')
        to_date = datetime.now().strftime('%d-%m-%Y')
        
        # Try each series
        for series in series_to_try:
            try:
                import urllib.parse
                series_param = urllib.parse.quote(f'["{series}"]')
                hist_url = f"{base}/api/historical/cm/equity?symbol={symbol}&series={series_param}&from={from_date}&to={to_date}"
                
                r2 = s.get(hist_url, timeout=10)
                
                if r2.status_code == 200:
                    data = r2.json()
                    
                    if "data" in data and isinstance(data["data"], list) and len(data["data"]) >= 5:
                        records = data["data"]
                        df = pd.DataFrame(records)
                        
                        # Rename columns
                        rename_map = {
                            "CH_TIMESTAMP": "Date",
                            "CH_OPENING_PRICE": "Open",
                            "CH_TRADE_HIGH_PRICE": "High",
                            "CH_TRADE_LOW_PRICE": "Low",
                            "CH_CLOSING_PRICE": "Close",
                            "CH_TOT_TRADED_QTY": "Volume",
                        }
                        df = df.rename(columns=rename_map)
                        
                        if "Date" in df.columns and "Close" in df.columns:
                            df["Date"] = pd.to_datetime(df["Date"])
                            df = df.set_index("Date")
                            df = df.sort_index()
                            
                            # Ensure all OHLCV columns exist
                            for col in ["Open", "High", "Low", "Close"]:
                                if col not in df.columns:
                                    df[col] = df["Close"]
                            if "Volume" not in df.columns:
                                df["Volume"] = 0
                            
                            print(f"✓ NSE API ({series}): {len(df)} records for {symbol}")
                            return df[["Open", "High", "Low", "Close", "Volume"]]
                
            except:
                continue
        
    except Exception as e:
        pass
    
    return pd.DataFrame()


# ---------- NSE Quote API (works for SME stocks!) ----------

def _fetch_from_nse_quote(symbol: str) -> pd.DataFrame:
    """
    Fetch current quote from NSE API.
    This works for SME stocks like SHYAMDHANI where historical API fails.
    Returns a minimal dataframe with the last trading day's data.
    """
    base = "https://www.nseindia.com"
    
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": base,
        })
        
        # Get cookies
        s.get(base, timeout=10)
        time.sleep(0.5)
        
        # Get quote
        quote_url = f"{base}/api/quote-equity?symbol={symbol}"
        r = s.get(quote_url, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            
            price_info = data.get('priceInfo', {})
            last_price = price_info.get('lastPrice')
            
            if last_price:
                # Get the actual last update date from API (e.g., "02-Jan-2026 16:00:00")
                last_update = data.get('metadata', {}).get('lastUpdateTime', '')
                try:
                    # Parse date like "02-Jan-2026 16:00:00"
                    trade_date = datetime.strptime(last_update.split()[0], '%d-%b-%Y').strftime('%Y-%m-%d')
                except:
                    # Fallback to last trading day (Friday if weekend)
                    now = datetime.now()
                    weekday = now.weekday()
                    if weekday == 5:  # Saturday -> Friday
                        trade_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
                    elif weekday == 6:  # Sunday -> Friday
                        trade_date = (now - timedelta(days=2)).strftime('%Y-%m-%d')
                    else:
                        trade_date = now.strftime('%Y-%m-%d')
                
                df = pd.DataFrame([{
                    'Date': trade_date,
                    'Open': price_info.get('open', last_price),
                    'High': price_info.get('intraDayHighLow', {}).get('max', last_price),
                    'Low': price_info.get('intraDayHighLow', {}).get('min', last_price),
                    'Close': last_price,
                    'Volume': data.get('preOpenMarket', {}).get('totalTradedVolume', 0)
                }])
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
                
                print(f"✓ NSE Quote API: {symbol} @ ₹{last_price} (date: {trade_date})")
                return df
                
    except Exception as e:
        pass
    
    return pd.DataFrame()


# ---------- Persistent Disk Cache ----------

def _get_cache_path(symbol: str) -> Path:
    """Get cache file path for a symbol"""
    return CACHE_DIR / f"{symbol}.csv"


def _fetch_from_disk_cache(symbol: str, max_age_days: int = 1) -> pd.DataFrame:
    """
    Check if we have cached data for this symbol on disk.
    Returns cached data if fresh enough.
    
    Cache is SKIPPED during market hours (9:15 AM - 6:00 PM IST) to ensure
    fresh data is always fetched during trading and shortly after.
    """
    try:
        cache_path = _get_cache_path(symbol)
        
        if cache_path.exists():
            now = datetime.now()
            current_hour = now.hour
            is_weekday = now.weekday() < 5  # Mon-Fri
            
            # Skip cache during market hours on weekdays (9 AM to 6 PM IST)
            # This ensures we always get fresh data during and after trading
            if is_weekday and 9 <= current_hour < 18:
                return pd.DataFrame()  # Force fresh fetch
            
            # Check file age
            mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age_hours = (now - mtime).total_seconds() / 3600
            
            # Use cache if less than 12 hours old (for after-hours/weekends)
            if age_hours < 12:
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                if not df.empty and len(df) >= 10:
                    return df
    except:
        pass
    
    return pd.DataFrame()


def _save_to_disk_cache(symbol: str, df: pd.DataFrame):
    """Save dataframe to disk cache"""
    try:
        if not df.empty and len(df) >= 10:
            cache_path = _get_cache_path(symbol)
            df.to_csv(cache_path)
    except:
        pass


# ---------- Google Finance (unofficial) ----------

def _fetch_from_google(symbol: str, days: int = 90) -> pd.DataFrame:
    """
    Try to fetch from Google Finance (unofficial, may not always work)
    Uses a simple CSV export URL
    """
    try:
        # Google Finance URL for Indian stocks
        for suffix in ["NSE", "BOM"]:
            url = f"https://www.google.com/finance/quote/{symbol}:{suffix}"
            
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml",
            }
            
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200 and symbol in r.text:
                # Google Finance doesn't provide easy CSV export
                # This is a placeholder - would need web scraping
                pass
    except:
        pass
    
    return pd.DataFrame()


# ---------- Public entry point ----------

def fetch_stock_data_with_fallback(
    symbol: str,
    period: str = "3mo",
    series: str = None,
    use_cache: bool = True,
):
    """
    Robust multi-source fetcher with cascading fallback.
    
    Priority order:
      0. Skip if known-failed symbol (instant skip)
      1. Disk cache (fastest - from previous fetches)
      2. yfinance (fast, works for ~70% of stocks)
      3. NSE API multi-series (works for SME/small-cap)
      4. Google Finance (experimental)
    
    Returns:
      {
        "mode": str,
        "df": DataFrame,
        "live_url": str,
      }
    """
    global _failed_symbols, _failed_symbols_expire, _persistent_failed
    
    live_url = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
    
    # Reset in-memory failed cache every 30 minutes
    if _failed_symbols_expire is None or datetime.now() > _failed_symbols_expire:
        _failed_symbols = set()
        _failed_symbols_expire = datetime.now() + timedelta(minutes=30)
    
    # FAST CHECK 1: Skip if in session failed cache
    if symbol in _failed_symbols:
        return {
            "mode": "skipped",
            "df": pd.DataFrame(),
            "live_url": live_url,
        }
    
    # FAST CHECK 2: Skip if known persistent failure
    if symbol in _persistent_failed:
        return {
            "mode": "known_failed",
            "df": pd.DataFrame(),
            "live_url": live_url,
        }
    
    # Map period to days
    period_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}
    days = period_map.get(period, 90)
    
    # Strategy 0: Check disk cache first (instant)
    if use_cache:
        df_cache = _fetch_from_disk_cache(symbol, max_age_days=1)
        if not df_cache.empty:
            return {
                "mode": "disk_cache",
                "df": df_cache,
                "live_url": None,
            }
    
    # Strategy 1: yfinance (fast, works for mainboard stocks)
    df_yf = _fetch_from_yfinance(symbol, period=period)
    if not df_yf.empty and len(df_yf) >= 5:
        # Check if yfinance has today's data
        today = datetime.now().date()
        last_date = df_yf.index[-1].date() if hasattr(df_yf.index[-1], 'date') else df_yf.index[-1]
        
        # If yfinance doesn't have today's data and it's during market hours or after,
        # try to append today's quote from NSE
        is_weekday = datetime.now().weekday() < 5
        current_hour = datetime.now().hour
        
        if is_weekday and current_hour >= 9 and last_date < today:
            # yfinance is stale, try to add today's price from NSE Quote
            df_quote = _fetch_from_nse_quote(symbol)
            if not df_quote.empty:
                # Append today's quote to historical data
                df_yf = pd.concat([df_yf, df_quote])
                print(f"✓ Supplemented {symbol} with today's NSE quote")
        
        _save_to_disk_cache(symbol, df_yf)  # Cache for next time
        return {
            "mode": "yfinance",
            "df": df_yf,
            "live_url": None,
        }
    
    # Strategy 2: NSE API with multi-series (works for SME stocks)
    df_nse = _fetch_from_nse_api(symbol, days=days)
    if not df_nse.empty and len(df_nse) >= 5:
        _save_to_disk_cache(symbol, df_nse)  # Cache for next time
        return {
            "mode": "nse_api",
            "df": df_nse,
            "live_url": live_url,
        }
    
    # Strategy 3: NSE Quote API (last resort for SME stocks like SHYAMDHANI)
    # This returns only today's data but at least confirms the stock is active
    df_quote = _fetch_from_nse_quote(symbol)
    if not df_quote.empty:
        # Note: Don't cache quote data as it's just 1 day
        return {
            "mode": "nse_quote",
            "df": df_quote,
            "live_url": live_url,
        }
    
    # No data found - add to failed caches
    _failed_symbols.add(symbol)
    _persistent_failed.add(symbol)
    
    # Save persistent failed every 100 failures
    if len(_persistent_failed) % 100 == 0:
        _save_persistent_failed(_persistent_failed)
    
    # Strategy 4: Last resort - no data available
    return {
        "mode": "none",
        "df": pd.DataFrame(),
        "live_url": live_url,
    }


def clear_cache(symbol: str = None):
    """Clear cache for a specific symbol or all symbols"""
    if symbol:
        cache_path = _get_cache_path(symbol)
        if cache_path.exists():
            cache_path.unlink()
            print(f"Cleared cache for {symbol}")
    else:
        for f in CACHE_DIR.glob("*.csv"):
            f.unlink()
        print("Cleared all cache files")


def get_cache_stats():
    """Get cache statistics"""
    csv_files = list(CACHE_DIR.glob("*.csv"))
    total_size = sum(f.stat().st_size for f in csv_files)
    return {
        "cached_symbols": len(csv_files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "failed_symbols": len(_persistent_failed),
    }
