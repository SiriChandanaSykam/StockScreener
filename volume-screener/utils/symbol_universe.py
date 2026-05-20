"""
Stock Universe Loader
Loads all Indian stocks from CSV files
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import os

# Path to data files
DATA_DIR = Path(__file__).parent.parent / "assets" / "data"


def load_stock_universe(limit: Optional[int] = None) -> List[Dict[str, str]]:
    """
    Load all Indian stocks from INDIA_STOCKS_MASTER.csv
    
    Args:
        limit: Optional limit on number of stocks to return (for testing)
    
    Returns:
        List of stock dictionaries with symbol, name, sector
    """
    csv_path = DATA_DIR / "INDIA_STOCKS_MASTER.csv"
    
    if not csv_path.exists():
        print(f"Warning: {csv_path} not found. Using fallback list.")
        return get_fallback_stocks()
    
    try:
        df = pd.read_csv(csv_path)
        
        # Clean and prepare data
        stocks = []
        
        # Patterns to exclude (ETF NAVs, iNAVs, special instruments)
        EXCLUDE_PATTERNS = [
            'NAV', 'INAV', 'BEES', 'NETF', 'ETF',  # ETF related
            'LIQUIDCASE', 'LIQUID', 'GILT',  # Debt instruments
            'DUMMY', 'TEST',  # Test symbols
        ]
        
        for _, row in df.iterrows():
            # Prefer NSE symbol, fallback to BSE
            symbol = row.get('Symbol_NSE') or row.get('Symbol') or row.get('Symbol_BSE')
            name = row.get('Name_NSE') or row.get('Name') or row.get('Name_BSE')
            
            if pd.isna(symbol) or pd.isna(name):
                continue
            
            # Clean symbol (remove .NS or .BO suffix if present)
            symbol = str(symbol).strip().replace('.NS', '').replace('.BO', '')
            symbol_upper = symbol.upper()
            
            # Skip ETFs and special instruments by series
            series = row.get('Series', '')
            if str(series) in ['ETF', 'IVP', 'GB', 'SG', 'IV', 'IF', 'GC']:
                continue
            
            # Skip symbols ending with NAV, INAV patterns (ETF NAV indicators)
            if symbol_upper.endswith('NAV') or symbol_upper.endswith('INAV'):
                continue
            
            # Skip symbols containing exclude patterns
            if any(pattern in symbol_upper for pattern in EXCLUDE_PATTERNS):
                continue
            
            # Skip very short symbols (likely invalid)
            if len(symbol) < 2:
                continue
            
            # Infer sector (you can enhance this with actual sector data)
            sector = infer_sector(name, symbol)
            
            stocks.append({
                'symbol': symbol,
                'name': str(name).strip(),
                'sector': sector
            })
        
        # Remove duplicates
        seen = set()
        unique_stocks = []
        for stock in stocks:
            if stock['symbol'] not in seen:
                seen.add(stock['symbol'])
                unique_stocks.append(stock)
        
        print(f"Loaded {len(unique_stocks)} stocks from CSV")
        
        if limit:
            return unique_stocks[:limit]
        
        return unique_stocks
        
    except Exception as e:
        print(f"Error loading stocks: {e}")
        return get_fallback_stocks()


def infer_sector(name: str, symbol: str) -> str:
    """
    Infer sector from stock name/symbol.
    This is a simple heuristic - can be enhanced with actual sector data.
    """
    name_lower = name.lower()
    symbol_upper = symbol.upper()
    
    # Banking & Finance
    if any(kw in name_lower for kw in ['bank', 'finance', 'capital', 'hdfc', 'icici', 'kotak', 'axis']):
        return 'Financials'
    if any(kw in symbol_upper for kw in ['BANK', 'FIN', 'HDFC', 'ICICI', 'KOTAK', 'AXIS', 'BAJAJ']):
        return 'Financials'
    
    # Technology
    if any(kw in name_lower for kw in ['tech', 'software', 'infosys', 'tcs', 'wipro', 'hcl', 'digital']):
        return 'Technology'
    if any(kw in symbol_upper for kw in ['INFY', 'TCS', 'WIPRO', 'HCLTECH', 'TECHM', 'LTIM']):
        return 'Technology'
    
    # Pharma & Healthcare
    if any(kw in name_lower for kw in ['pharma', 'drug', 'health', 'hospital', 'medic', 'bio']):
        return 'Healthcare'
    if any(kw in symbol_upper for kw in ['PHARMA', 'DRUG', 'CIPLA', 'SUNPHARMA', 'DRREDDY']):
        return 'Healthcare'
    
    # Energy & Oil
    if any(kw in name_lower for kw in ['oil', 'gas', 'petrol', 'energy', 'power', 'reliance']):
        return 'Energy'
    if any(kw in symbol_upper for kw in ['RELIANCE', 'ONGC', 'IOC', 'BPCL', 'HPCL', 'COAL']):
        return 'Energy'
    
    # Automobiles
    if any(kw in name_lower for kw in ['motor', 'auto', 'vehicle', 'car', 'tata motors', 'maruti']):
        return 'Auto'
    if any(kw in symbol_upper for kw in ['MARUTI', 'TATAMOTORS', 'M&M', 'HERO', 'BAJAJ-AUTO']):
        return 'Auto'
    
    # Consumer Goods
    if any(kw in name_lower for kw in ['consumer', 'fmcg', 'hindustan', 'nestle', 'itc', 'food']):
        return 'Consumer Goods'
    if any(kw in symbol_upper for kw in ['ITC', 'HUL', 'HINDUNILVR', 'NESTLE', 'BRITANNIA']):
        return 'Consumer Goods'
    
    # Metals & Mining
    if any(kw in name_lower for kw in ['steel', 'metal', 'mining', 'iron', 'alumin']):
        return 'Metals & Mining'
    if any(kw in symbol_upper for kw in ['TATASTEEL', 'HINDALCO', 'JSWSTEEL', 'VEDL', 'NMDC']):
        return 'Metals & Mining'
    
    # Telecom
    if any(kw in name_lower for kw in ['telecom', 'airtel', 'jio', 'vodafone']):
        return 'Telecom'
    if any(kw in symbol_upper for kw in ['BHARTIARTL', 'IDEA', 'VIL']):
        return 'Telecom'
    
    # Real Estate
    if any(kw in name_lower for kw in ['real estate', 'property', 'housing', 'realty']):
        return 'Real Estate'
    
    # Infrastructure
    if any(kw in name_lower for kw in ['infra', 'construction', 'cement', 'engineer']):
        return 'Infrastructure'
    if any(kw in symbol_upper for kw in ['LT', 'L&T', 'ULTRACEMCO', 'ACC', 'AMBUJACEM']):
        return 'Infrastructure'
    
    return 'Others'


def get_fallback_stocks() -> List[Dict[str, str]]:
    """Fallback list of major stocks if CSV is not available"""
    return [
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


def get_nifty50_stocks() -> List[Dict[str, str]]:
    """Get Nifty 50 stocks"""
    nifty50_symbols = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "BHARTIARTL",
        "ITC", "LICI", "BAJFINANCE", "KOTAKBANK", "HINDUNILVR", "LT", "AXISBANK",
        "WIPRO", "HCLTECH", "SUNPHARMA", "MARUTI", "TITAN", "ASIANPAINT",
        "ULTRACEMCO", "ONGC", "NESTLEIND", "NTPC", "M&M", "POWERGRID",
        "TATASTEEL", "JSWSTEEL", "ADANIENT", "ADANIPORTS", "BAJAJ-AUTO",
        "DRREDDY", "DIVISLAB", "BRITANNIA", "HINDALCO", "CIPLA", "EICHERMOT",
        "COALINDIA", "INDUSINDBK", "UPL", "BPCL", "TECHM", "GRASIM",
        "TATAMOTORS", "HEROMOTOCO", "APOLLOHOSP", "SBILIFE", "HDFCLIFE", "BAJAJFINSV"
    ]
    
    all_stocks = load_stock_universe()
    nifty50 = [s for s in all_stocks if s['symbol'] in nifty50_symbols]
    
    # Add any missing ones with defaults
    existing_symbols = {s['symbol'] for s in nifty50}
    for sym in nifty50_symbols:
        if sym not in existing_symbols:
            nifty50.append({"symbol": sym, "name": sym, "sector": "Others"})
    
    return nifty50


def search_stocks(query: str, limit: int = 20) -> List[Dict[str, str]]:
    """
    Search for stocks by symbol or name.
    
    Args:
        query: Search query
        limit: Max results to return
    
    Returns:
        List of matching stocks
    """
    all_stocks = load_stock_universe()
    query_lower = query.lower()
    
    matches = []
    for stock in all_stocks:
        if query_lower in stock['symbol'].lower() or query_lower in stock['name'].lower():
            matches.append(stock)
            if len(matches) >= limit:
                break
    
    return matches


# Test
if __name__ == "__main__":
    stocks = load_stock_universe(limit=20)
    print(f"\nSample stocks:")
    for s in stocks[:10]:
        print(f"  {s['symbol']}: {s['name']} ({s['sector']})")
