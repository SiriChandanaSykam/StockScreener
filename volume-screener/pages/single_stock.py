import streamlit as st

from utils.data_fetcher import fetch_stock_data_with_fallback
from utils.score_engine import score_stock
from utils.charting import create_tv_chart
from utils.symbol_universe import load_series_map

# Always render a title so the page is never blank
st.title("🔬 Single Stock Analysis")

series_map = load_series_map()

# Input
sym = st.text_input("Enter Stock Symbol (e.g., RELIANCE.NS)", value="RELIANCE.NS")

if sym:
    base = sym.upper().replace(".NS", "").replace(".BO", "")
    series = series_map.get(base, "EQ")

    try:
        result = fetch_stock_data_with_fallback(base, series=series)
        df = result.get("df")
    except Exception as e:
        df = None
        st.error(f"Data fetch failed for {sym}: {e}")

    if df is None or df.empty or result.get("mode") == "none":
        st.error(f"No data found for {sym}. Please check the symbol and try again.")
    else:
        try:
            score, signals = score_stock(df)
        except Exception as e:
            score, signals = None, None
            st.error(f"Scoring failed for {sym}: {e}")

        if score is not None:
            st.subheader(f"{base} — Score: {score}")
            if signals:
                st.write("Signals:", ", ".join(signals))

        try:
            st.plotly_chart(create_tv_chart(df, base), use_container_width=True)
        except Exception as e:
            st.error(f"Chart render failed for {sym}: {e}")

        if result.get("mode") == "sme_eod" and result.get("live_url"):
            st.info(
                "SME stock: historical data from NSE (EOD). "
                "Click below to see live intraday moves."
            )
            st.markdown(
                f"[Open live chart / quote for {base}]({result['live_url']})"
            )

        with st.expander("Recent data (last 5 rows)", expanded=False):
            st.write(df.tail(5))
else:
    st.info("Enter a stock symbol to begin analysis.")
