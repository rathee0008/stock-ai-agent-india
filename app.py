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
    period = ccol1.selectbox("Period", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=3)
    interval_options = {
        "1d": "5m", "5d": "15m", "1mo": "1d", "6mo": "1d", "1y": "1d", "5y": "1wk",
    }
    interval = interval_options[period]
    refresh_seconds = ccol2.selectbox("Auto-refresh every", [15, 30, 60, 120], index=1)
    if ccol3.button("Refresh now"):
        st.cache_data.clear()

    indicator_choices = st.multiselect(
        "Indicators",
        ["SMA 20/50", "EMA 12/26", "Bollinger Bands", "Volume", "RSI (14)", "MACD"],
        default=["SMA 20/50", "Volume", "RSI (14)", "MACD"],
    )
    show_sr = st.checkbox("Show support / resistance levels", value=True)

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

        raw_df = md.get_history(st.session_state.ticker, period=period, interval=interval)
        df = md.compute_indicators(raw_df)

        levels = {"support": [], "resistance": []}
        if show_sr and len(df) >= 25:
            levels = md.support_resistance_levels(raw_df)

        st.plotly_chart(
            ch.candlestick_figure(
                df,
                f"{resolved_ticker} ({period}, {interval})",
                show_sma="SMA 20/50" in indicator_choices,
                show_ema="EMA 12/26" in indicator_choices,
                show_bb="Bollinger Bands" in indicator_choices,
                show_volume="Volume" in indicator_choices,
                show_rsi="RSI (14)" in indicator_choices,
                show_macd="MACD" in indicator_choices,
                support_levels=levels["support"],
                resistance_levels=levels["resistance"],
            ),
            use_container_width=True,
        )

        if show_sr and (levels["support"] or levels["resistance"]):
            lcol1, lcol2 = st.columns(2)
            lcol1.markdown("**Support:** " + (", ".join(f"₹{v:g}" for v in levels["support"]) or "—"))
            lcol2.markdown("**Resistance:** " + (", ".join(f"₹{v:g}" for v in levels["resistance"]) or "—"))
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
