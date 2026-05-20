"""
Stock Ticker Extractor

Automatically extracts Indian stock tickers from news headlines.
Uses company name → ticker mapping and pattern matching.
"""

import re
from typing import List, Optional, Tuple


# Major Indian stocks mapping (Company Name/Alias → NSE Ticker)
COMPANY_TO_TICKER = {
    # Nifty 50 & Major Stocks
    "reliance": "RELIANCE",
    "reliance industries": "RELIANCE",
    "ril": "RELIANCE",
    "tcs": "TCS",
    "tata consultancy": "TCS",
    "infosys": "INFY",
    "infy": "INFY",
    "hdfc bank": "HDFCBANK",
    "hdfc": "HDFC",
    "icici bank": "ICICIBANK",
    "icici": "ICICIBANK",
    "sbi": "SBIN",
    "state bank": "SBIN",
    "kotak": "KOTAKBANK",
    "kotak mahindra": "KOTAKBANK",
    "axis bank": "AXISBANK",
    "axis": "AXISBANK",
    "wipro": "WIPRO",
    "hcl tech": "HCLTECH",
    "hcl technologies": "HCLTECH",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "itc": "ITC",
    "larsen": "LT",
    "l&t": "LT",
    "maruti": "MARUTI",
    "maruti suzuki": "MARUTI",
    "asian paints": "ASIANPAINT",
    "bajaj finance": "BAJFINANCE",
    "bajaj finserv": "BAJAJFINSV",
    "hindustan unilever": "HINDUNILVR",
    "hul": "HINDUNILVR",
    "sun pharma": "SUNPHARMA",
    "titan": "TITAN",
    "nestle": "NESTLEIND",
    "ultratech": "ULTRACEMCO",
    "ultratech cement": "ULTRACEMCO",
    "power grid": "POWERGRID",
    "ntpc": "NTPC",
    "ongc": "ONGC",
    "coal india": "COALINDIA",
    "tata motors": "TATAMOTORS",
    "tata steel": "TATASTEEL",
    "jswsteel": "JSWSTEEL",
    "jsw steel": "JSWSTEEL",
    "hindalco": "HINDALCO",
    "vedanta": "VEDL",
    "adani": "ADANIENT",
    "adani enterprises": "ADANIENT",
    "adani ports": "ADANIPORTS",
    "adani green": "ADANIGREEN",
    "adani power": "ADANIPOWER",
    "tech mahindra": "TECHM",
    "mahindra": "M&M",
    "m&m": "M&M",
    "hero motocorp": "HEROMOTOCO",
    "hero": "HEROMOTOCO",
    "bajaj auto": "BAJAJ-AUTO",
    "eicher": "EICHERMOT",
    "eicher motors": "EICHERMOT",
    "dr reddy": "DRREDDY",
    "cipla": "CIPLA",
    "divi's": "DIVISLAB",
    "divis lab": "DIVISLAB",
    
    # Banks & NBFCs
    "indusind": "INDUSINDBK",
    "bandhan": "BANDHANBNK",
    "federal bank": "FEDERALBNK",
    "idfc first": "IDFCFIRSTB",
    "yes bank": "YESBANK",
    "pnb": "PNB",
    "bank of baroda": "BANKBARODA",
    "canara bank": "CANBK",
    "union bank": "UNIONBANK",
    "bajaj housing": "BAJAJHFL",
    "lic housing": "LICHSGFIN",
    "muthoot": "MUTHOOTFIN",
    "shriram": "SHRIRAMFIN",
    
    # IT & Tech
    "ltimindtree": "LTIM",
    "lti": "LTIM",
    "mphasis": "MPHASIS",
    "persistent": "PERSISTENT",
    "coforge": "COFORGE",
    "cyient": "CYIENT",
    "mindtree": "LTIM",
    "l&t infotech": "LTIM",
    "zensar": "ZENSARTECH",
    
    # Retail & Consumer
    "dmart": "DMART",
    "avenue supermarts": "DMART",
    "trent": "TRENT",
    "zomato": "ZOMATO",
    "nykaa": "NYKAA",
    "paytm": "PAYTM",
    "one97": "PAYTM",
    "policybazaar": "POLICYBZR",
    "pb fintech": "POLICYBZR",
    "info edge": "NAUKRI",
    "naukri": "NAUKRI",
    
    # Energy & Power
    "tata power": "TATAPOWER",
    "adani transmission": "ADANITRANS",
    "torrent power": "TORNTPOWER",
    "gail": "GAIL",
    "ioc": "IOC",
    "indian oil": "IOC",
    "bpcl": "BPCL",
    "hpcl": "HPCL",
    "petronet": "PETRONET",
    
    # Auto
    "tata motors": "TATAMOTORS",
    "ashok leyland": "ASHOKLEY",
    "tvs motor": "TVSMOTOR",
    "escorts": "ESCORTS",
    "motherson": "MOTHERSON",
    "mrf": "MRF",
    "apollo tyres": "APOLLOTYRE",
    
    # Pharma & Healthcare
    "lupin": "LUPIN",
    "aurobindo": "AUROPHARMA",
    "biocon": "BIOCON",
    "torrent pharma": "TORNTPHARM",
    "glenmark": "GLENMARK",
    "alkem": "ALKEM",
    "apollo hospitals": "APOLLOHOSP",
    "fortis": "FORTIS",
    "max healthcare": "MAXHEALTH",
    
    # Cement & Infrastructure
    "acc": "ACC",
    "ambuja": "AMBUJACEM",
    "shree cement": "SHREECEM",
    "dalmia bharat": "DALBHARAT",
    "ramco": "RAMCOCEM",
    "irb infra": "IRB",
    "larsen toubro": "LT",
    
    # Metals & Mining
    "tata steel": "TATASTEEL",
    "sail": "SAIL",
    "nmdc": "NMDC",
    "nalco": "NATIONALUM",
    "hindustan zinc": "HINDZINC",
    
    # Telecom & Media
    "vodafone idea": "IDEA",
    "vi": "IDEA",
    "jio": "RELIANCE",
    "zee": "ZEEL",
    "sun tv": "SUNTV",
    "pvr": "PVRINOX",
    "inox": "PVRINOX",
    
    # Real Estate
    "dlf": "DLF",
    "godrej properties": "GODREJPROP",
    "prestige": "PRESTIGE",
    "oberoi realty": "OBEROIRLTY",
    "brigade": "BRIGADE",
    "sobha": "SOBHA",
    "lodha": "LODHA",
    "macrotech": "LODHA",
    
    # Insurance
    "lic": "LICI",
    "sbi life": "SBILIFE",
    "hdfc life": "HDFCLIFE",
    "icici prudential": "ICICIPRULI",
    "max life": "MAXHEALTH",
    "bajaj allianz": "BAJAJALLIANZ",
    "star health": "STARHEALTH",
    
    # Indices (for general market news)
    "nifty": "NIFTY50",
    "sensex": "SENSEX",
    "bank nifty": "BANKNIFTY",
    "nifty it": "NIFTYIT",
    "nifty pharma": "NIFTYPHARMA",
}


def extract_tickers(headline: str, limit: int = 3) -> List[str]:
    """
    Extract stock tickers from a news headline.
    
    Args:
        headline: News headline text
        limit: Maximum tickers to return
        
    Returns:
        List of NSE ticker symbols found
    """
    if not headline:
        return []
    
    headline_lower = headline.lower()
    found_tickers = []
    
    # Skip very short company names that cause false positives
    min_name_length = 3
    
    # Sort by length (longer matches first to avoid partial matches)
    sorted_items = sorted(
        COMPANY_TO_TICKER.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )
    
    for company_name, ticker in sorted_items:
        # Skip very short names (too many false positives)
        if len(company_name) < min_name_length:
            continue
        
        # Use word boundary matching to avoid partial matches
        # e.g., "vi" should not match "video" or "investor"
        pattern = r'\b' + re.escape(company_name) + r'\b'
        
        if re.search(pattern, headline_lower):
            if ticker not in found_tickers:
                found_tickers.append(ticker)
                
                if len(found_tickers) >= limit:
                    break
    
    return found_tickers


def extract_ticker_with_context(headline: str) -> Tuple[List[str], str]:
    """
    Extract tickers and determine if news is company-specific or market-wide.
    
    Returns:
        (tickers, context) where context is 'company', 'sector', or 'market'
    """
    tickers = extract_tickers(headline)
    
    if len(tickers) >= 1:
        # Check for index mentions
        index_tickers = {"NIFTY50", "SENSEX", "BANKNIFTY", "NIFTYIT", "NIFTYPHARMA"}
        if any(t in index_tickers for t in tickers):
            return tickers, "market"
        return tickers, "company"
    
    # Check for sector-level news
    sector_keywords = [
        "banking sector", "it sector", "pharma sector", "auto sector",
        "metal stocks", "fmcg stocks", "realty stocks", "psu banks",
        "private banks", "small caps", "mid caps", "large caps"
    ]
    
    headline_lower = headline.lower()
    if any(kw in headline_lower for kw in sector_keywords):
        return [], "sector"
    
    return [], "market"


def get_primary_ticker(headline: str) -> Optional[str]:
    """
    Get the most relevant ticker for a headline.
    Returns None if no specific company mentioned.
    """
    tickers = extract_tickers(headline, limit=1)
    return tickers[0] if tickers else None


# Quick test
if __name__ == "__main__":
    test_headlines = [
        "Reliance Industries posts 45% profit growth in Q3",
        "TCS faces regulatory penalties from SEBI",
        "HDFC Bank merger with HDFC complete",
        "Nifty hits all-time high, Sensex follows",
        "Banking sector stocks rally on RBI policy",
        "Asian Paints Q3 Preview: PAT seen up 8% YoY",
        "Adani Group stocks crash 20% on fraud allegations",
        "Zomato, Paytm lead fintech rally",
        "Global markets dip on Fed uncertainty",
    ]
    
    print("=" * 60)
    print("🧪 Testing Ticker Extractor")
    print("=" * 60)
    
    for headline in test_headlines:
        tickers, context = extract_ticker_with_context(headline)
        ticker_str = ", ".join(tickers) if tickers else "MARKET"
        
        print(f"\n📰 {headline[:50]}...")
        print(f"   Tickers: {ticker_str}")
        print(f"   Context: {context}")
