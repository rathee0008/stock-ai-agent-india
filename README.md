# Indian Stocks AI Agent

Streamlit app with:
- **Chart** — free TradingView Advanced Chart widget, searchable across every NSE/BSE-listed
  stock and index (click the search icon inside the chart). Genuinely live/streaming, not
  a static candlestick snapshot.
- **AI Analyst** — Claude-powered chat that calls live tools (quote, fundamentals,
  technicals, news) before answering.
- **Fundamentals & Technicals** — yfinance data + computed SMA/EMA/RSI/MACD/Bollinger Bands.

Not financial advice; educational use only. Sibling of the US-market
[stock-ai-agent](../stock-ai-agent) app, same pattern, adapted for NSE/BSE tickers
(`.NS` / `.BO`) and INR pricing. No paper-trading tab here — Alpaca (used in the US
version) doesn't support Indian equities.

## Run locally

```bash
cd stock-ai-agent-india
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Paste your Anthropic API key in the sidebar (or put it in `.streamlit/secrets.toml`, copied
from `.streamlit/secrets.toml.example`). The AI Analyst tab won't work without it; Chart and
Fundamentals/Technicals work with no keys at all.

## Ticker input

Type a company name ("TCS", "Reliance", "HDFC Bank") or a ticker with/without suffix
("INFY", "INFY.NS", "RELIANCE.BO"). Indices work too: "NIFTY 50", "SENSEX", "BANK NIFTY".
Anything not recognized is assumed to be a raw NSE symbol (or BSE, if you switch the
sidebar's exchange picker) — `XYZ` → `XYZ.NS` by default.

## Deploy to Streamlit Community Cloud

1. Push this folder to a GitHub repo (public or private).
2. Go to https://share.streamlit.io → "New app" → pick the repo/branch → main file `app.py`.
3. In the app's **Settings → Secrets**, paste:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. Deploy. (This step requires your own GitHub/Streamlit accounts — sign in there yourself.)
