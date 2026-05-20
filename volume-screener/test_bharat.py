# Test which import pattern works for Bharat-sm-data v4.0.1

print("Testing Bharat-sm-data imports...")

# Test 1: Direct module import
try:
    import Bharat_sm_data
    print("✓ Bharat_sm_data module exists")
    print("  Available attributes:", dir(Bharat_sm_data))
except ImportError as e:
    print("✗ Bharat_sm_data import failed:", e)

# Test 2: Try get_equity_data directly
try:
    from Bharat_sm_data import get_equity_data
    print("✓ get_equity_data imported directly")
except ImportError as e:
    print("✗ get_equity_data direct import failed:", e)

# Test 3: Try Technical.NSE namespace
try:
    from Technical.NSE import get_ohlc
    print("✓ Technical.NSE.get_ohlc imported")
except ImportError as e:
    print("✗ Technical.NSE import failed:", e)

# Test 4: Try fetching actual data
print("\nTesting data fetch for AAKAAR...")
try:
    # Try whichever import worked above
    from Bharat_sm_data import get_equity_data
    df = get_equity_data(symbol="AAKAAR", period="1y")
    if df is not None and not df.empty:
        print(f"✓ Got {len(df)} rows of data")
        print("Columns:", df.columns.tolist())
        print(df.tail(3))
    else:
        print("✗ Function returned empty/None")
except Exception as e:
    print(f"✗ Data fetch failed: {e}")
