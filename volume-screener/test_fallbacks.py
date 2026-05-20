import yfinance as yf
import requests
import pandas as pd
from datetime import datetime
import time

# Function to test yahoo finance
def test_yfinance(symbol_suffix):
    symbol = f"AAKAAR{symbol_suffix}"
    print(f"\nTesting {symbol} via yfinance...")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1mo")
        print(f"Status: {'Success' if not df.empty else 'Empty'}")
        if not df.empty:
            print(f"Rows: {len(df)}")
            print(df.head())
        else:
            print("No data found.")
    except Exception as e:
        print(f"Error: {e}")

# Function to test screener.in (page content search for price)
def test_screener_in(symbol):
    url = f"https://www.screener.in/company/{symbol}/"
    print(f"\nTesting {url}...")
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            if "Current Price" in r.text:
                print("Found 'Current Price' in page text.")
            else:
                print("'Current Price' not found.")
    except Exception as e:
        print(f"Error: {e}")

print("--- Starting Fallback Tests ---")
test_yfinance(".NS")
test_yfinance(".BO")
test_screener_in("AAKAAR")
