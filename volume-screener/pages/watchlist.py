import streamlit as st

from utils.data_fetcher import fetch_stock_data_with_fallback
from utils.score_engine import score_stock
from utils.charting import create_tv_chart
from utils.symbol_universe import load_series_map

# Always render a title so the page is never blank
st.title("⭐ Watchlist")

series_map = load_series_map()

# Initialize session state
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# Add stocks
with st.form("add_form", clear_on_submit=True):
    new_stock = st.text_input("Add stock symbol (e.g., INFY.NS)")
    add = st.form_submit_button("Add to Watchlist")
    if add and new_stock:
        sym = new_stock.upper().strip()
        if sym and sym not in st.session_state["watchlist"]:
            st.session_state["watchlist"].append(sym)

# Remove stocks
if st.session_state["watchlist"]:
    remove = st.multiselect("Remove stocks", st.session_state["watchlist"])
    if st.button("Remove Selected") and remove:
        for stock in remove:
            if stock in st.session_state["watchlist"]:
                st.session_state["watchlist"].remove(stock)

# Show list
st.subheader("Your Watchlist")
if not st.session_state["watchlist"]:
    st.info("Watchlist is empty. Add symbols above to begin.")
else:
    for sym in st.session_state["watchlist"]:
        base = sym.upper().replace(".NS", "").replace(".BO", "")
        series = series_map.get(base, "EQ")

        try:
            result = fetch_stock_data_with_fallback(base, series=series)
        except Exception as e:
            st.error(f"{sym}: data fetch failed — {e}")
            continue

        df = result.get("df")
        mode = result.get("mode")

        if df is None or df.empty or mode == "none":
            st.warning(f"No data for {sym}")
            continue

        try:
            score, signals = score_stock(df)
        except Exception as e:
            st.error(f"{sym}: scoring failed — {e}")
            continue

        st.markdown(f"**{base} — Score: {score}**")
        if signals:
            st.write(", ".join(signals[:4]))

        try:
            st.plotly_chart(create_tv_chart(df, base), use_container_width=True)
        except Exception as e:
            st.error(f"{sym}: chart render failed — {e}")

        if mode == "sme_eod" and result.get("live_url"):
            st.info(
                "SME stock: historical data from NSE (EOD). "
                "Click below to see live intraday moves."
            )
            st.markdown(
                f"[Open live chart / quote for {base}]({result['live_url']})"
            )
