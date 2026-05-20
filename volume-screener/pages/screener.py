import time
import streamlit as st

from utils.symbol_universe import load_all_symbols, load_series_map
from utils.data_fetcher import fetch_stock_data_with_fallback
from utils.score_engine import score_stock
from utils.charting import create_tv_chart

# Always show a header so the page is never blank
st.title("🔥 Mega Stock Screener")

# Symbol selection
all_symbols, _ = load_all_symbols()
symbols = list(all_symbols.keys())
selected = st.multiselect("Pick stocks", symbols, default=symbols[:15])

# Load series map so we know which symbols are SME (SM/BE)
series_map = load_series_map()

# Minimum score filter in sidebar for consistency
min_score = st.sidebar.slider("Minimum Score", min_value=5, max_value=20, value=10)

# Helper function to generate fallback links
def get_fallback_links(symbol):
    """Generate multiple fallback research links for a stock"""
    return {
        "screener": f"https://www.screener.in/company/{symbol}/",
        "tradingview": f"https://www.tradingview.com/symbols/NSE-{symbol}/",
        "google": f"https://www.google.com/search?q={symbol}+NSE+stock+price",
    }

# Run action
if st.button("Run Screener", type="primary"):
    results = []
    with st.spinner(f"Scanning {len(selected)} stocks..."):
        for sym in selected:
            # Strip any suffix and look up series from CSV
            base = sym.replace(".NS", "").replace(".BO", "")
            series = series_map.get(base, "EQ")

            try:
                result = fetch_stock_data_with_fallback(base, period="3mo", series=series)
            except Exception as e:
                st.error(f"{sym}: fetch failed — {e}")
                time.sleep(0.1)
                continue

            mode = result.get("mode")
            df = result.get("df")

            if df is None or df.empty or mode == "none":
                # Build fallback links
                nse_url = result.get("live_url")
                fallback = get_fallback_links(base)
                
                # Special message for SME stocks where data sources don't have history yet
                if series in ("SM", "BE") and nse_url:
                    st.warning(
                        f"⚠️ {base}: SME stock - no historical EOD data available yet from free sources."
                    )
                    st.markdown(
                        f"👉 [NSE Live]({nse_url}) · "
                        f"[Screener.in]({fallback['screener']}) · "
                        f"[TradingView]({fallback['tradingview']}) · "
                        f"[Google Search]({fallback['google']})"
                    )
                else:
                    st.error(f"{base}: fetch failed — no usable data")
                    # Show multiple fallbacks for manual research
                    st.markdown(
                        f"📊 Research links: "
                        f"[Screener.in]({fallback['screener']}) · "
                        f"[TradingView]({fallback['tradingview']}) · "
                        f"[Google]({fallback['google']})"
                    )
                time.sleep(0.1)
                continue

            # Handle snapshot-only mode (1 row from today)
            if mode == "sme_snapshot" and len(df) < 5:
                nse_url = result.get("live_url")
                fallback = get_fallback_links(base)
                
                st.info(
                    f"ℹ️ {base}: Only today's live snapshot available (historical data blocked). "
                    "Use links below for analysis."
                )
                if nse_url:
                    st.markdown(
                        f"👉 [NSE Live]({nse_url}) · "
                        f"[Screener.in]({fallback['screener']}) · "
                        f"[TradingView]({fallback['tradingview']})"
                    )

            try:
                score, signals = score_stock(df)
            except Exception as e:
                st.error(f"{sym}: scoring failed — {e}")
                time.sleep(0.1)
                continue

            if score >= min_score:
                results.append(
                    {
                        "symbol": base,
                        "score": score,
                        "signals": signals,
                        "df": df,
                        "mode": mode,
                        "live_url": result.get("live_url"),
                        "series": series,
                    }
                )

            # Gentle throttle to respect provider limits
            time.sleep(0.1)

    if results:
        for res in sorted(results, key=lambda x: x["score"], reverse=True):
            st.subheader(f"{res['symbol']} — Score: {res['score']}")
            if res.get("signals"):
                st.write(", ".join(res["signals"]))

            # Price/volume chart
            try:
                st.plotly_chart(
                    create_tv_chart(res["df"], res["symbol"]),
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"{res['symbol']}: chart failed — {e}")

            # If any alternative data source was used, show live links
            if res.get("mode") in ("sme_eod", "sme_snapshot", "nse_api") and res.get("live_url"):
                # Map mode to friendly source name
                source_map = {
                    "sme_eod": "NSEpy EOD data",
                    "nse_api": "NSE website APIs",
                    "sme_snapshot": "today's NSE snapshot only",
                }
                source = source_map.get(res.get("mode"), "alternative source")
                
                nse_url = res.get("live_url")
                fallback = get_fallback_links(res["symbol"])

                if res.get("mode") == "sme_snapshot":
                    st.info(
                        f"📊 SME stock: {source} - no historical data available. "
                        "Check live sources below."
                    )
                else:
                    st.info(
                        f"📈 SME stock: data from {source}. "
                        "Check live sources for latest moves."
                    )

                st.markdown(
                    f"👉 [NSE Live]({nse_url}) · "
                    f"[Screener.in]({fallback['screener']}) · "
                    f"[TradingView]({fallback['tradingview']})"
                )
    else:
        st.info(
            "No stocks matched the screening criteria. "
            "Try lowering the minimum score or adding more symbols."
        )
