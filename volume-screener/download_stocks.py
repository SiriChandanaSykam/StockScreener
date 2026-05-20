"""
Download All Indian Stocks from NSE and BSE

This script downloads the complete list of tradeable stocks from:
1. NSE (National Stock Exchange) - ~2,400 stocks
2. BSE (Bombay Stock Exchange) - ~5,000 stocks

Run this periodically to keep your stock list updated.
"""

import pandas as pd
import requests
from pathlib import Path
import time

DATA_DIR = Path(__file__).parent / "assets" / "data"


def download_nse_stocks() -> pd.DataFrame:
    """
    Download NSE equity list from official NSE website.
    URL: https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O
    """
    print("📥 Downloading NSE stocks...")
    
    # NSE requires proper headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/'
    }
    
    try:
        # Create session to handle cookies
        session = requests.Session()
        
        # First get the main page to set cookies
        session.get('https://www.nseindia.com/', headers=headers, timeout=10)
        time.sleep(1)
        
        # Get all equity list
        url = 'https://www.nseindia.com/api/market-data-pre-open?key=ALL'
        response = session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            stocks = data.get('data', [])
            
            df = pd.DataFrame([{
                'Symbol': s.get('metadata', {}).get('symbol'),
                'Name': s.get('metadata', {}).get('companyName'),
                'Series': s.get('metadata', {}).get('series'),
                'Source': 'NSE'
            } for s in stocks if s.get('metadata', {}).get('symbol')])
            
            print(f"  ✅ Downloaded {len(df)} stocks from NSE")
            return df
        else:
            print(f"  ❌ NSE API error: {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"  ❌ Error downloading NSE: {e}")
        return pd.DataFrame()


def download_bse_stocks() -> pd.DataFrame:
    """
    Download BSE equity list.
    BSE provides a simpler API.
    """
    print("📥 Downloading BSE stocks...")
    
    try:
        url = 'https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.bseindia.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            df = pd.DataFrame([{
                'Symbol': s.get('scrip_cd'),
                'Name': s.get('scripname'),
                'BSE_Code': s.get('scrip_cd'),
                'ISIN': s.get('isin_cd'),
                'Source': 'BSE'
            } for s in data if s.get('scrip_cd')])
            
            print(f"  ✅ Downloaded {len(df)} stocks from BSE")
            return df
        else:
            print(f"  ❌ BSE API error: {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"  ❌ Error downloading BSE: {e}")
        return pd.DataFrame()


def download_from_csv_urls() -> pd.DataFrame:
    """
    Alternative: Download from NSE's downloadable CSV.
    This is more reliable than the API.
    """
    print("📥 Trying NSE CSV download...")
    
    try:
        # This URL provides all securities
        url = 'https://www.nseindia.com/content/equities/EQUITY_L.csv'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            print(f"  ✅ Downloaded {len(df)} stocks from NSE CSV")
            return df
        else:
            print(f"  ⚠️ NSE CSV not available (status: {response.status_code})")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"  ⚠️ NSE CSV error: {e}")
        return pd.DataFrame()


def merge_and_save(nse_df: pd.DataFrame, bse_df: pd.DataFrame):
    """Merge NSE and BSE data and save to CSV."""
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save individual files
    if not nse_df.empty:
        nse_path = DATA_DIR / "NSE_STOCKS.csv"
        nse_df.to_csv(nse_path, index=False)
        print(f"  💾 Saved {len(nse_df)} NSE stocks to {nse_path.name}")
    
    if not bse_df.empty:
        bse_path = DATA_DIR / "BSE_STOCKS.csv"
        bse_df.to_csv(bse_path, index=False)
        print(f"  💾 Saved {len(bse_df)} BSE stocks to {bse_path.name}")
    
    # Merge
    if not nse_df.empty or not bse_df.empty:
        all_stocks = pd.concat([nse_df, bse_df], ignore_index=True)
        all_stocks = all_stocks.drop_duplicates(subset=['Symbol'], keep='first')
        
        master_path = DATA_DIR / "ALL_INDIAN_STOCKS.csv"
        all_stocks.to_csv(master_path, index=False)
        print(f"\n✅ Total: {len(all_stocks)} unique stocks saved to {master_path.name}")
        
        return all_stocks
    
    return pd.DataFrame()


def main():
    print("=" * 50)
    print("🇮🇳 Indian Stock List Downloader")
    print("=" * 50)
    print()
    
    # Download from both exchanges
    nse_stocks = download_nse_stocks()
    
    if nse_stocks.empty:
        nse_stocks = download_from_csv_urls()
    
    time.sleep(1)  # Be nice to servers
    
    bse_stocks = download_bse_stocks()
    
    print()
    
    # Merge and save
    all_stocks = merge_and_save(nse_stocks, bse_stocks)
    
    print()
    print("=" * 50)
    
    if not all_stocks.empty:
        print(f"✅ Successfully downloaded {len(all_stocks)} stocks!")
        print(f"📂 Files saved in: {DATA_DIR}")
    else:
        print("❌ Could not download stocks. Check your internet connection.")
        print()
        print("Alternative: Download manually from:")
        print("  NSE: https://www.nseindia.com/market-data/live-equity-market")
        print("  BSE: https://www.bseindia.com/corporates/List_Scrips.html")
    
    print("=" * 50)


if __name__ == "__main__":
    main()
