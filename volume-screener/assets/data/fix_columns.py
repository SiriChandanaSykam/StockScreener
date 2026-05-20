import pandas as pd

# Load the file
df = pd.read_csv('indian_stocks_full.csv')

# Rename columns to match what the code expects
df = df.rename(columns={
    'symbol': 'Symbol',
    'company': 'Name',
    'isin': 'ISIN',
    'exchange': 'Exchange',
    'sector': 'Sector',
    'series': 'Series'
})

# Save with correct column names
df.to_csv('indian_stocks_full.csv', index=False)

print(f"✅ Fixed! File now has {len(df)} stocks with correct columns:")
print(f"   Columns: {list(df.columns)}")
