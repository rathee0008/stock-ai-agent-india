import datetime as dt

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from lib import chart as ch
from lib import market_data as md
from lib import tradingview as tv
from lib import ai_agent

st.set_page_config(page_title="Indian Stocks AI Agent", page_icon="📈", layout="wide")

DISCLAIMER = (
    "⚠️ **Educational tool only — not financial advice.** Data is delayed/best-effort "
    "from free public sources (typically ~15 min behind for NSE/BSE). Nothing here is a "
    "recommendation to buy or sell any security. You are solely responsible for your own "
    "investment decisions."
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "ticker" not in st.session_state:
    st.session_state.ticker = "RELIANCE"

with st.sidebar:
    st.title("📈 Indian Stocks AI Agent")
    st.session_state.ticker = st.text_input(
        "Ticker / company name", st.session_state.ticker,
        help="e.g. RELIANCE, TCS, Infosys, HDFC Bank, NIFTY 50, SENSEX",
    ).strip()
    exchange = st.selectbox("Exchange (used for bare symbols)", ["NSE", "BSE"], index=0)
    st.caption("Tip: inside the chart itself you can click the search icon to pull up "
               "**any** NSE/BSE-listed stock — the exchange picker here is just the default "
               "for symbols you type without .NS/.BO.")
    st.divider()

    try:
        default_key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:  # noqa: BLE001 - no secrets.toml configured, that's fine
        default_key = ""
    anthropic_key = st.text_input(
        "Anthropic API key", type="password", value=default_key,
        help="Needed for the AI Analyst tab. Get one at console.anthropic.com.",
    )
    st.divider()
    st.caption(DISCLAIMER)

default_exchange_code = "NS" if exchange == "NSE" else "BO"
resolved_ticker = md.resolve_ticker(st.session_state.ticker, default_exchange_code)
tv_symbol = md.to_tradingview_symbol(resolved_ticker)

tab_chart, tab_ai, tab_data = st.tabs(
    ["📊 Chart", "🤖 AI Analyst", "🔎 Fundamentals & Technicals"]
)

with tab_chart:
    st.subheader(f"{st.session_state.ticker} — chart ({resolved_ticker})")
    st.caption(
        "TradingView's embeddable widget doesn't carry redistribution rights for NSE/BSE "
        "data, so this chart is built from yfinance and auto-refreshes. For a true live, "
        f"streaming chart, open it directly on [TradingView]({tv.chart_url(tv_symbol)})."
    )

    ccol1, ccol2, ccol3 = st.columns([2, 2, 1])
    use_custom_range = ccol1.checkbox(
        "Custom date range", value=False, key="chart_custom_range",
        help="Uncheck to use the preset Period selector instead.",
    )
    refresh_seconds = ccol2.selectbox("Auto-refresh every", [15, 30, 60, 120], index=1, key="chart_refresh")
    if ccol3.button("Refresh now"):
        st.cache_data.clear()

    if use_custom_range:
        dcol1, dcol2 = st.columns(2)
        start_date = dcol1.date_input(
            "Start date", value=dt.date.today() - dt.timedelta(days=180), key="chart_start_date",
        )
        end_date = dcol2.date_input("End date", value=dt.date.today(), key="chart_end_date")
        period = None
        interval = "1d"
    else:
        period = st.selectbox("Period", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=3, key="chart_period")
        interval_options = {
            "1d": "5m", "5d": "15m", "1mo": "1d", "6mo": "1d", "1y": "1d", "5y": "1wk",
        }
        interval = interval_options[period]

    tcol1, tcol2, tcol3 = st.columns([1.4, 1, 1.4])
    chart_type = tcol1.selectbox("Chart type", ["Candlestick", "Line", "Area", "Heikin-Ashi"], key="chart_type")
    log_scale = tcol2.checkbox("Log scale", value=False, key="chart_log_scale")
    compare_choice = tcol3.selectbox("Compare with", ["None", "NIFTY 50", "SENSEX", "BANK NIFTY"], key="chart_compare")

    icol1, icol2 = st.columns([4, 1])
    default_indicators = ["SMA 20/50", "Volume", "RSI (14)", "MACD"]
    if "chart_indicators" not in st.session_state:
        st.session_state.chart_indicators = default_indicators
    indicator_choices = icol1.multiselect(
        "Indicators",
        ["SMA 20/50", "EMA 12/26", "Bollinger Bands", "VWAP", "Parabolic SAR", "Ichimoku Cloud",
         "Volume", "RSI (14)", "Stochastic RSI", "MACD", "ATR (14)"],
        key="chart_indicators",
    )
    icol2.write("")
    icol2.write("")
    if icol2.button("Reset"):
        st.session_state.chart_indicators = default_indicators
        st.rerun()

    scol1, scol2 = st.columns(2)
    show_sr = scol1.checkbox("Show support / resistance levels", value=True, key="chart_show_sr")
    show_returns = scol2.checkbox("Show returns (%) panel", value=False, key="chart_show_returns")

    st_autorefresh(interval=refresh_seconds * 1000, key="chart_autorefresh")

    try:
        quote = md.get_quote(st.session_state.ticker)
        price = quote.get("last_price")
        prev_close = quote.get("previous_close")
        change = (price - prev_close) if (price is not None and prev_close) else None
        change_pct = (change / prev_close * 100) if (change is not None and prev_close) else None
        qcol1, qcol2 = st.columns(2)
        qcol1.metric("Last price (INR)", price)
        qcol2.metric(
            "Change vs prev close",
            f"{change:+.2f}" if change is not None else "—",
            f"{change_pct:+.2f}%" if change_pct is not None else None,
        )

        if use_custom_range:
            raw_df = md.get_history_range(st.session_state.ticker, start_date, end_date, interval=interval)
            period_label = f"{start_date} to {end_date}"
        else:
            raw_df = md.get_history(st.session_state.ticker, period=period, interval=interval)
            period_label = f"{period}, {interval}"
        df = md.compute_indicators(raw_df)

        levels = {"support": [], "resistance": []}
        if show_sr and len(df) >= 25:
            levels = md.support_resistance_levels(raw_df)

        compare_series = None
        compare_label = None
        if compare_choice != "None":
            try:
                if use_custom_range:
                    bench_raw = md.get_history_range(compare_choice, start_date, end_date, interval=interval)
                else:
                    bench_raw = md.get_history(compare_choice, period=period, interval=interval)
                compare_series = (bench_raw["Close"] / bench_raw["Close"].iloc[0] - 1) * 100
                compare_label = compare_choice
            except Exception:  # noqa: BLE001 - benchmark is optional, don't break the chart
                compare_series = None
                compare_label = None

        st.plotly_chart(
            ch.candlestick_figure(
                df,
                f"{resolved_ticker} ({period_label})",
                chart_type=chart_type,
                show_sma="SMA 20/50" in indicator_choices,
                show_ema="EMA 12/26" in indicator_choices,
                show_bb="Bollinger Bands" in indicator_choices,
                show_vwap="VWAP" in indicator_choices,
                show_psar="Parabolic SAR" in indicator_choices,
                show_ichimoku="Ichimoku Cloud" in indicator_choices,
                show_volume="Volume" in indicator_choices,
                show_rsi="RSI (14)" in indicator_choices,
                show_stochrsi="Stochastic RSI" in indicator_choices,
                show_macd="MACD" in indicator_choices,
                show_atr="ATR (14)" in indicator_choices,
                show_returns=show_returns,
                log_scale=log_scale,
                compare_series=compare_series,
                compare_label=compare_label,
                support_levels=levels["support"],
                resistance_levels=levels["resistance"],
            ),
            use_container_width=True,
            config={"displaylogo": False},
        )

        if show_sr and (levels["support"] or levels["resistance"]):
            lcol1, lcol2 = st.columns(2)
            lcol1.markdown("**Support:** " + (", ".join(f"₹{v:g}" for v in levels["support"]) or "—"))
            lcol2.markdown("**Resistance:** " + (", ".join(f"₹{v:g}" for v in levels["resistance"]) or "—"))

        dl_name = f"{resolved_ticker.replace('.', '_').replace('^', '')}_{period_label}".replace(" ", "_").replace(",", "")
        st.download_button(
            "Download chart data as CSV",
            data=df.to_csv().encode("utf-8"),
            file_name=f"{dl_name}.csv",
            mime="text/csv",
        )
        st.caption("Tip: hover the chart and use its toolbar's camera icon to download it as a PNG.")
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't load chart data: {e}")

with tab_ai:
    st.subheader("Ask the AI analyst")
    st.caption("Pulls live quotes, fundamentals, technicals, and news as tools before answering.")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input(f"Ask about {st.session_state.ticker}, e.g. 'What's the RSI and recent news?'")
    if prompt:
        if not anthropic_key:
            st.error("Enter your Anthropic API key in the sidebar first.")
        else:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Checking live data..."):
                    try:
                        reply, st.session_state.chat_history = ai_agent.chat(
                            anthropic_key, st.session_state.chat_history, prompt
                        )
                        st.markdown(reply)
                    except Exception as e:  # noqa: BLE001
                        st.error(f"AI request failed: {e}")

with tab_data:
    st.subheader(f"{st.session_state.ticker} — fundamentals & technicals")
    col1, col2 = st.columns(2)
    try:
        quote = md.get_quote(st.session_state.ticker)
        with col1:
            st.metric("Last price (INR)", quote["last_price"], delta=None)
            st.json(quote)
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't load quote: {e}")

    try:
        tech = md.technical_summary(st.session_state.ticker)
        with col2:
            st.metric("Trend (SMA20 vs SMA50)", tech["trend"])
            st.json(tech)
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't compute technicals: {e}")

    st.divider()
    try:
        st.write("**Fundamentals**")
        st.json(md.get_fundamentals(st.session_state.ticker))
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't load fundamentals: {e}")

    st.divider()
    st.write("**Recent news**")
    try:
        news = md.get_news(st.session_state.ticker)
        if not news:
            st.caption("No recent news found.")
        for item in news:
            st.markdown(f"- [{item['title']}]({item['link']}) — *{item['publisher']}*")
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't load news: {e}")
