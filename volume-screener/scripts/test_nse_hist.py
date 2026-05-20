"""Test NSE historical data endpoints for SHYAMDHANI"""
import requests
import time
from datetime import datetime, timedelta

# Setup session
s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
    'Accept': '*/*',
    'Referer': 'https://www.nseindia.com'
})

# Get cookies
print("Getting NSE cookies...")
s.get('https://www.nseindia.com', timeout=10)
time.sleep(0.5)

symbol = 'SHYAMDHANI'

# Try different endpoints
endpoints = [
    f'/api/historical/cm/equity?symbol={symbol}',
    f'/api/historical/securityArchives?from=30-12-2025&to=02-01-2026&symbol={symbol}&dataType=priceVolume',
    f'/api/quote-derivative?symbol={symbol}',
]

for endpoint in endpoints:
    url = f'https://www.nseindia.com{endpoint}'
    print(f"\nTrying: {endpoint}")
    try:
        r = s.get(url, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                print(f"Keys: {list(data.keys())[:5]}")
                if 'data' in data:
                    print(f"Data rows: {len(data['data'])}")
            elif isinstance(data, list):
                print(f"List with {len(data)} items")
    except Exception as e:
        print(f"Error: {e}")

# Try the series-specific historical
print("\n\nTrying series-specific historical...")
series_list = ['ST', 'SM', 'EQ']
for series in series_list:
    url = f'https://www.nseindia.com/api/historical/cm/equity?symbol={symbol}&series=["{series}"]'
    try:
        r = s.get(url, timeout=10)
        print(f"\n{series} series: Status {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if 'data' in data:
                print(f"Data rows: {len(data['data'])}")
                if len(data['data']) > 0:
                    print(f"Sample: {data['data'][0]}")
    except Exception as e:
        print(f"Error: {e}")
