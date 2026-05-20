"""
NSE + BSE EQUITY MERGER - FIXED VERSION
Combines cleaned NSE data (3,953 stocks) with BSE T+1 and T+0 data
Final output: ~5,200 unique equity stocks
"""

import pandas as pd
import shutil

print("=" * 80)
print("🔗 MERGING NSE + BSE EQUITY STOCKS")
print("=" * 80)

# Step 1: Load cleaned NSE data
print("\n[1/6] Loading cleaned NSE data...")
try:
    nse = pd.read_csv("INDIA_STOCKS_CLEAN_DETAILED.csv")
    print(f"   ✅ NSE stocks: {len(nse)}")
except:
    print("   ❌ INDIA_STOCKS_CLEAN_DETAILED.csv not found!")
    print("   Run clean_equity_stocks.py first!")
    exit()

# Step 2: Load BSE T+1 data (FIX: read correctly)
print("\n[2/6] Loading BSE T+1 data...")
bse_t1 = pd.read_csv("Equity.csv", index_col=False)
# Extract actual data from concatenated index
if bse_t1.index.name is None and len(bse_t1.columns) == 9:
    # Data is in the right place
    pass
print(f"   ✅ BSE T+1 stocks: {len(bse_t1)}")

# Step 3: Load BSE T+0 data  
print("\n[3/6] Loading BSE T+0 data...")
bse_t0 = pd.read_csv("EQT0.csv", index_col=False)
print(f"   ✅ BSE T+0 stocks: {len(bse_t0)}")

# Step 4: Combine and clean BSE data
print("\n[4/6] Cleaning and combining BSE data...")

# Combine both BSE files
bse_combined = pd.concat([bse_t1, bse_t0], ignore_index=True)
print(f"   📊 Combined BSE rows: {len(bse_combined)}")

# CORRECTED: The actual ISIN is in 'Security Id' column!
bse_clean = pd.DataFrame({
    'Symbol': bse_combined['Security Id'].astype(str).str.strip().str.upper(),  # This is the ticker
    'Name': bse_combined['Issuer Name'].astype(str).str.strip(),
    'ISIN': bse_combined['Security Id'].astype(str).str.strip().str.upper(),  # ISIN is here!
    'BSE_Code': bse_combined['Security Code'],
    'Status': bse_combined['Status'],
    'Group': bse_combined['Group'].astype(str).str.strip(),
    'Exchange': 'BSE'
})

# For proper mapping, let's extract the actual ticker symbol from 'Security Id' column
# which actually contains ticker in some rows and ISIN in others
# Let's use a different approach - parse the raw data properly

print("\n   🔧 Re-parsing BSE data with correct column mapping...")

# Read BSE files again with proper parsing
def parse_bse_file(filename):
    data = []
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        header = lines[0].strip().split(',')
        
        for line in lines[1:]:
            parts = line.strip().split(',')
            if len(parts) >= 9:
                data.append({
                    'Security_Code': parts[0],
                    'Issuer_Name': parts[1],
                    'Security_Id': parts[2],
                    'Security_Name': parts[3],
                    'Status': parts[4],
                    'Group': parts[5].strip(),
                    'Face_Value': parts[6],
                    'ISIN': parts[7],
                    'Instrument': parts[8]
                })
    return pd.DataFrame(data)

bse_t1_fixed = parse_bse_file("Equity.csv")
bse_t0_fixed = parse_bse_file("EQT0.csv")

bse_combined_fixed = pd.concat([bse_t1_fixed, bse_t0_fixed], ignore_index=True)
print(f"   📊 Re-parsed BSE rows: {len(bse_combined_fixed)}")

# Now clean properly
bse_clean = pd.DataFrame({
    'Symbol': bse_combined_fixed['Security_Id'].str.strip().str.upper(),
    'Name': bse_combined_fixed['Issuer_Name'].str.strip(),
    'ISIN': bse_combined_fixed['ISIN'].str.strip().str.upper(),
    'BSE_Code': bse_combined_fixed['Security_Code'],
    'Status': bse_combined_fixed['Status'].str.strip(),
    'Group': bse_combined_fixed['Group'],
    'Exchange': 'BSE'
})

# Remove invalid entries
original = len(bse_clean)
bse_clean = bse_clean[bse_clean['Symbol'].notna()]
bse_clean = bse_clean[bse_clean['Symbol'] != '']
bse_clean = bse_clean[bse_clean['ISIN'].notna()]
bse_clean = bse_clean[bse_clean['ISIN'] != '']
bse_clean = bse_clean[bse_clean['Status'] == 'Active']

# Keep only valid ISINs (start with IN)
bse_clean = bse_clean[bse_clean['ISIN'].str.match(r'^IN[A-Z0-9]{10}$', na=False)]
print(f"   ❌ Removed {original - len(bse_clean)} invalid BSE entries")
print(f"   ✅ Clean BSE stocks: {len(bse_clean)}")

# Remove duplicates within BSE
before_dedup = len(bse_clean)
bse_clean = bse_clean.drop_duplicates(subset=['ISIN'], keep='first')
print(f"   ❌ Removed {before_dedup - len(bse_clean)} duplicate BSE ISINs")

# Step 5: Merge NSE + BSE
print("\n[5/6] Merging NSE + BSE...")

# Prepare NSE for merge
nse_for_merge = pd.DataFrame({
    'Symbol': nse['Symbol'],
    'Name': nse['Name'],
    'ISIN': nse['ISIN'],
    'Exchange': 'NSE',
    'Series': nse['Series'],
    'yfinance_symbol': nse['yfinance_symbol']
})

# Prepare BSE for merge
bse_for_merge = pd.DataFrame({
    'Symbol': bse_clean['Symbol'],
    'Name': bse_clean['Name'],
    'ISIN': bse_clean['ISIN'],
    'Exchange': 'BSE',
    'Series': 'EQ',
    'yfinance_symbol': bse_clean['Symbol'] + '.BO'
})

# Combine both
combined = pd.concat([nse_for_merge, bse_for_merge], ignore_index=True)
print(f"   📊 Combined total before deduplication: {len(combined)}")

# Remove duplicates (keep NSE over BSE if same ISIN)
before_final_dedup = len(combined)
combined = combined.drop_duplicates(subset=['ISIN'], keep='first')
print(f"   ❌ Removed {before_final_dedup - len(combined)} duplicate ISINs (NSE-BSE overlap)")
print(f"   ✅ Final unique stocks: {len(combined)}")

# Step 6: Save final files
print("\n[6/6] Saving final merged dataset...")

# Backup existing file
try:
    shutil.copy('indian_stocks_full.csv', 'indian_stocks_full_NSE_ONLY_BACKUP.csv')
    print(f"   💾 Backed up old file: indian_stocks_full_NSE_ONLY_BACKUP.csv")
except:
    pass

# Create screener-ready format
final = pd.DataFrame({
    'symbol': combined['Symbol'],
    'company': combined['Name'],
    'isin': combined['ISIN'],
    'exchange': combined['Exchange'],
    'sector': 'Unknown',
    'series': combined['Series']
})

# Save main screener file
final.to_csv("indian_stocks_full.csv", index=False)
print(f"   ✅ Saved: indian_stocks_full.csv ({len(final)} stocks)")

# Save detailed file
detailed = combined[['Symbol', 'Name', 'ISIN', 'Exchange', 'Series', 'yfinance_symbol']].copy()
detailed.to_csv("NSE_BSE_MERGED_DETAILED.csv", index=False)
print(f"   ✅ Saved: NSE_BSE_MERGED_DETAILED.csv ({len(detailed)} stocks)")

# Statistics
print("\n" + "=" * 80)
print("FINAL STATISTICS")
print("=" * 80)
print(f"\n📊 Total unique stocks: {len(final)}")
print(f"\nBreakdown by exchange:")
print(final['exchange'].value_counts())

# NSE-BSE overlap analysis
nse_isins = set(nse_for_merge['ISIN'])
bse_isins = set(bse_for_merge['ISIN'])
overlap = len(nse_isins & bse_isins)
print(f"\n🔗 NSE-BSE overlap: {overlap} stocks listed on both exchanges")
print(f"📈 NSE exclusive: {len(final[final['exchange'] == 'NSE'])}")
print(f"📉 BSE exclusive: {len(final[final['exchange'] == 'BSE'])}")

print("\n" + "=" * 80)
print("✅ MERGE COMPLETE!")
print("=" * 80)
print(f"\n🎉 You now have {len(final)} total tradable equity stocks!")
print("=" * 80)
