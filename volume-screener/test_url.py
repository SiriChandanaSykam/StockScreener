from jugaad_data.nse import stock_df
from datetime import date, timedelta

today = date.today()
start = today - timedelta(days=90)

symbols_to_test = [
    'AAKAAR',   # SME stock
    'TCS',       # Mainboard stock
]

for symbol in symbols_to_test:
    print(f"\n=== Testing {symbol} ===")
    try:
        df = stock_df(symbol=symbol, from_date=start, to_date=today, series="EQ")
        print(f"Rows: {len(df)}")
        if not df.empty:
            print(f"Columns: {list(df.columns)}")
            print(f"Sample:\n{df.head()}")
        else:
            print("Empty DataFrame")
    except Exception as e:
        print(f"Error with EQ series: {e}")
    
    # Try with SM series for AAKAAR
    if symbol == 'AAKAAR':
        try:
            df = stock_df(symbol=symbol, from_date=start, to_date=today, series="SM")
            print(f"\nWith SM series - Rows: {len(df)}")
            if not df.empty:
                print(f"Columns: {list(df.columns)}")
                print(f"Sample:\n{df.head()}")
        except Exception as e:
            print(f"Error with SM series: {e}")
