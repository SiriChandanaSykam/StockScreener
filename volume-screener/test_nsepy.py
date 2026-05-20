from nsepy import get_history
from datetime import date, timedelta

end = date.today()
start = end - timedelta(days=120)

# Test AAKAAR
print("Testing AAKAAR...")
try:
    df = get_history(symbol="AAKAAR", start=start, end=end)
    print(f"AAKAAR rows: {len(df) if df is not None and hasattr(df, '__len__') else 0}")
    if df is not None and not df.empty:
        print(df.tail())
    else:
        print("Empty or None")
except Exception as e:
    print(f"AAKAAR error: {e}")

# Test AARADHYA
print("\nTesting AARADHYA...")
try:
    df = get_history(symbol="AARADHYA", start=start, end=end)
    print(f"AARADHYA rows: {len(df) if df is not None and hasattr(df, '__len__') else 0}")
    if df is not None and not df.empty:
        print(df.tail())
    else:
        print("Empty or None")
except Exception as e:
    print(f"AARADHYA error: {e}")

# Test a known mainboard stock as control
print("\nTesting RELIANCE (control)...")
try:
    df = get_history(symbol="RELIANCE", start=start, end=end)
    print(f"RELIANCE rows: {len(df) if df is not None and hasattr(df, '__len__') else 0}")
    if df is not None and not df.empty:
        print("RELIANCE data loaded successfully!")
    else:
        print("Empty or None")
except Exception as e:
    print(f"RELIANCE error: {e}")
