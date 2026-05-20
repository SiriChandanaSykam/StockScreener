import streamlit as st

from utils.symbol_universe import load_all_symbols, load_series_map
from utils.score_engine import score_stock
from utils.data_fetcher import fetch_stock_data_with_fallback
from utils.charting import create_tv_chart

# Always render a header so the page is never blank
st.title("🏭 Sector Analysis")

# Load symbols and sector mapping
all_symbols, sector_map = load_all_symbols()
sectors = list(sector_map.keys())

# Load series map so we know which symbols are SME (SM/BE)
series_map = load_series_map()

# Controls
selected_sectors = st.multiselect("Select sectors to analyze", sectors, default=sectors[:3])
min_score = st.sidebar.slider("Minimum score filter", 5, 20, 10)

# Action
if st.button("Run Sector Analysis", type="primary"):
    for sector in selected_sectors:
        st.subheader(sector)
        stocks = sector_map.get(sector, {})

        filtered_results = []
        for sym, name in stocks.items():
            base = sym.replace(".NS", "").replace(".BO", "")
            series = series_map.get(base, "EQ")

            try:
                result = fetch_stock_data_with_fallback(base, series=series)
            except Exception as e:
                st.error(f"{sym}: data fetch failed — {e}")
                continue

            df = result.get("df")
            mode = result.get("mode")

            if df is None or df.empty or mode == "none":
                continue

            try:
                score, signals = score_stock(df)
            except Exception as e:
                st.error(f"{sym}: scoring failed — {e}")
                continue

            if score >= min_score:
                filtered_results.append(
                    (base, name, score, signals, df, mode, result.get("live_url"))
                )

        if filtered_results:
            filtered_results.sort(key=lambda x: x[2], reverse=True)

            for base, name, score, signals, df, mode, live_url in filtered_results[:10]:
                st.markdown(f"**{base} — {name}** | Score: {score}")
                if signals:
                    st.write(", ".join(signals[:4]))
                try:
                    st.plotly_chart(create_tv_chart(df, base), use_container_width=True)
                except Exception as e:
                    st.error(f"{base}: chart render failed — {e}")

                if mode == "sme_eod" and live_url:
                    st.info(
                        "SME stock: historical data from NSE (EOD). "
                        "Click below to see live intraday moves."
                    )
                    st.markdown(
                        f"[Open live chart / quote for {base}]({live_url})"
                    )
        else:
            st.info(
                f"No stocks passed scoring for sector '{sector}' with min score {min_score}. "
                "Try lowering the threshold or expanding sectors."
            )
