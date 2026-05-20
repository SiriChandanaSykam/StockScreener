"""
Stock Data Processor - Merges NSE & BSE Downloads
==================================================
Processes 4 downloaded CSV files and creates a clean, unified stock list.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path(r"d:\STOCK SCREENER\volume-screener")
RAW_DIR = BASE_DIR / "assets" / "raw_downloads"
DATA_DIR = BASE_DIR / "assets" / "data"
OUTPUT_FILE = DATA_DIR / "INDIA_STOCKS_MASTER.csv"

# Exclusion patterns
EXCLUDE_SUFFIXES = ['NAV', 'INAV', '-RE', '-RE1', 'DVR', '-PP', '-W', '-BE', '-BZ']
EXCLUDE_PATTERNS = ['NAV', 'INAV', 'BEES', 'NETF', 'ETF', 'LIQUID', 'GILT', 'DUMMY', 'TEST', 'INDEX']
EXCLUDE_SERIES = ['ETF', 'IV', 'IF', 'GC', 'N1', 'N2', 'N3', 'MF', 'GS', 'TB', 'GB', 'SG']

def is_valid_symbol(symbol: str, series: str = None) -> bool:
    """Check if a symbol is valid for trading"""
    if not symbol or len(symbol) < 2:
        return False
    
    symbol = str(symbol).upper().strip()
    
    # Skip if ends with bad suffix
    for suffix in EXCLUDE_SUFFIXES:
        if symbol.endswith(suffix):
            return False
    
    # Skip if contains bad pattern
    for pattern in EXCLUDE_PATTERNS:
        if pattern in symbol:
            return False
    
    # Skip special characters
    if any(c in symbol for c in ['&', '(', ')', '#', '*']):
        return False
    
    # Skip bad series
    if series and str(series).upper().strip() in EXCLUDE_SERIES:
        return False
    
    return True


def process_nse_equity(filepath: Path) -> pd.DataFrame:
    """Process NSE EQUITY_L.csv (Mainboard stocks)"""
    print(f"\n📄 Processing: {filepath.name}")
    
    df = pd.read_csv(filepath)
    print(f"   Raw rows: {len(df)}")
    
    stocks = []
    for _, row in df.iterrows():
        symbol = str(row.get('SYMBOL', '')).strip()
        name = str(row.get('NAME OF COMPANY', '')).strip()
        series = str(row.get(' SERIES', row.get('SERIES', 'EQ'))).strip()
        isin = str(row.get('ISIN NUMBER', row.get('ISIN', ''))).strip() if pd.notna(row.get('ISIN NUMBER', row.get('ISIN'))) else ''
        
        if symbol and is_valid_symbol(symbol, series):
            stocks.append({
                'Symbol': symbol,
                'Name': name,
                'ISIN': isin,
                'Series': series,
                'Exchange': 'NSE',
                'Type': 'Mainboard'
            })
    
    result = pd.DataFrame(stocks)
    print(f"   ✅ Valid: {len(result)} stocks")
    return result


def process_nse_sme(filepath: Path) -> pd.DataFrame:
    """Process NSE SME_EQUITY_L.csv (SME stocks)"""
    print(f"\n📄 Processing: {filepath.name}")
    
    df = pd.read_csv(filepath)
    print(f"   Raw rows: {len(df)}")
    print(f"   Columns: {df.columns.tolist()}")
    
    stocks = []
    for _, row in df.iterrows():
        symbol = str(row.get('SYMBOL', '')).strip()
        name = str(row.get('NAME_OF_COMPANY', row.get('NAME OF COMPANY', ''))).strip()
        series = str(row.get('SERIES', 'SM')).strip()
        # Fix: SME file uses ISIN_NUMBER not ISIN
        isin = str(row.get('ISIN_NUMBER', row.get('ISIN', ''))).strip() if pd.notna(row.get('ISIN_NUMBER', row.get('ISIN'))) else ''
        
        # Skip empty symbols
        if not symbol or symbol == 'nan':
            continue
        
        if is_valid_symbol(symbol, series):
            stocks.append({
                'Symbol': symbol,
                'Name': name,
                'ISIN': isin,
                'Series': series,
                'Exchange': 'NSE',
                'Type': 'SME'
            })
    
    result = pd.DataFrame(stocks)
    print(f"   ✅ Valid: {len(result)} stocks")
    return result


def process_bse_equity(filepath: Path) -> pd.DataFrame:
    """Process BSE Equity.csv"""
    print(f"\n📄 Processing: {filepath.name}")
    
    # Try different encodings
    for encoding in ['utf-8', 'latin1', 'cp1252']:
        try:
            df = pd.read_csv(filepath, encoding=encoding)
            break
        except:
            continue
    
    print(f"   Raw rows: {len(df)}")
    print(f"   Columns: {df.columns.tolist()}")
    
    stocks = []
    for _, row in df.iterrows():
        # BSE uses Security Id for trading symbol
        symbol = str(row.get('Security Id', '')).strip()
        name = str(row.get('Issuer Name', '')).strip()
        status = str(row.get('Status', 'Active')).strip()
        group = str(row.get('Group', '')).strip()
        isin = str(row.get('ISIN No', '')).strip() if pd.notna(row.get('ISIN No')) else ''
        
        # Skip if no symbol
        if not symbol or symbol == 'nan':
            continue
        
        # Skip suspended/delisted stocks
        if 'suspend' in status.lower() or 'delist' in status.lower():
            continue
        
        # Clean symbol - remove # and special chars
        symbol = symbol.replace('#', '').replace('*', '').strip()
        
        if symbol and is_valid_symbol(symbol):
            stocks.append({
                'Symbol': symbol,
                'Name': name,
                'ISIN': isin,
                'Series': group.strip(),
                'Exchange': 'BSE',
                'Type': 'Mainboard' if group.strip() in ['A', 'B', 'T', 'S', 'M', 'MT', 'W'] else 'SME'
            })
    
    result = pd.DataFrame(stocks)
    print(f"   ✅ Valid: {len(result)} stocks")
    return result


def main():
    print("=" * 70)
    print("🔧 STOCK DATA PROCESSOR")
    print("=" * 70)
    print(f"📁 Source folder: {RAW_DIR}")
    print(f"📁 Output file: {OUTPUT_FILE}")
    
    all_stocks = []
    
    # Process each file
    for filepath in RAW_DIR.glob("*.csv"):
        filename_lower = filepath.name.lower()
        
        if 'equity_l' in filename_lower and 'sme' not in filename_lower:
            df = process_nse_equity(filepath)
        elif 'sme' in filename_lower:
            df = process_nse_sme(filepath)
        elif 'equity' in filename_lower or 'eqt' in filename_lower:
            df = process_bse_equity(filepath)
        else:
            print(f"\n⚠️ Skipping unknown format: {filepath.name}")
            continue
        
        if not df.empty:
            all_stocks.append(df)
    
    if not all_stocks:
        print("\n❌ No valid data found!")
        return
    
    # Combine all
    print("\n" + "=" * 70)
    print("📊 MERGING DATA")
    print("=" * 70)
    
    combined = pd.concat(all_stocks, ignore_index=True)
    print(f"   Combined total: {len(combined)}")
    
    # Remove duplicates (keep NSE over BSE if same symbol)
    combined['ExchangePriority'] = combined['Exchange'].map({'NSE': 0, 'BSE': 1})
    combined = combined.sort_values('ExchangePriority')
    combined = combined.drop_duplicates(subset=['Symbol'], keep='first')
    combined = combined.drop(columns=['ExchangePriority'])
    
    print(f"   After deduplication: {len(combined)}")
    
    # Add metadata
    combined['UpdatedAt'] = datetime.now().strftime('%Y-%m-%d')
    
    # Sort by symbol
    combined = combined.sort_values('Symbol').reset_index(drop=True)
    
    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_FILE, index=False)
    
    # Summary
    print("\n" + "=" * 70)
    print("📈 FINAL SUMMARY")
    print("=" * 70)
    print(f"\n✅ Total stocks saved: {len(combined)}")
    print(f"\n� By Exchange:")
    print(combined['Exchange'].value_counts().to_string())
    print(f"\n📊 By Type:")
    print(combined['Type'].value_counts().to_string())
    print(f"\n💾 Saved to: {OUTPUT_FILE}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
