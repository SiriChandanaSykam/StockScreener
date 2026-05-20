import pandas as pd
import re

df = pd.read_csv('indian_stocks_full.csv')
print(f"Before cleanup: {len(df)} stocks")

# 1. Apply symbol fixes
df.loc[df['Symbol'] == 'AMBUJELCST', 'Symbol'] = 'AMBUJACEM'
df.loc[df['Symbol'] == 'ALOKTEXT', 'Symbol'] = 'ALOKINDS'

# 2. Remove bad patterns
df = df[~df['Symbol'].str.contains(r'PP|RE|DEPO|-RE|-PP', case=False, na=False, regex=True)]

# 3. Remove known delisted/suspended
delisted = ['BALCO', 'WEBSL', 'CITYON', 'ZELIO', 'OML', 'RDGAIL', 'JDL', 'ECOPP', 'ADHIRAJ', 'GALLARD', 'SUNSKY', 'VALPLAST', 'ZAPPFRESH', 'INFINITY', 'MITTALSTL', 'SODHACAP', 'AMEENJI', 'MPKSTEELS', 'BHAVIK', 'KVSCASTING', 'EARKART', 'GPAPL', 'CHTR', 'TELGE', 'SOLVEX', 'PRARUH', 'SYSTEMATIC', 'CHIRAHARIT', 'NSBBPO']
df = df[~df['Symbol'].isin(delisted)]

# 4. Remove illiquid patterns (symbols starting with numbers or special chars)
df = df[~df['Symbol'].str.match(r'^\d', na=False)]
df = df[~df['Symbol'].str.contains(r'[-/\\]', na=False, regex=True)]

print(f"After cleanup: {len(df)} stocks")
print("\nExchange breakdown:")
print(df['Exchange'].value_counts())

# Save cleaned file
df.to_csv('indian_stocks_full_cleaned.csv', index=False)
print("\n✅ Saved: indian_stocks_full_cleaned.csv")

# Replace original
import shutil
shutil.move('indian_stocks_full_cleaned.csv', 'indian_stocks_full.csv')
print("✅ Overwrote indian_stocks_full.csv with cleaned version")
