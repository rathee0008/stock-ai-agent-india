"""Free, no-key market data helpers backed by yfinance, for Indian (NSE/BSE) equities."""
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf

# Company name / bare symbol -> yfinance ticker, so users can type "TCS" or
# "Reliance" instead of needing to know the .NS/.BO suffix convention.
POPULAR_STOCKS = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFOSYS": "INFY.NS",
    "INFY": "INFY.NS",
    "HDFC BANK": "HDFCBANK.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICI BANK": "ICICIBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBI": "SBIN.NS",
    "STATE BANK OF INDIA": "SBIN.NS",
    "SBIN": "SBIN.NS",
    "HINDUSTAN UNILEVER": "HINDUNILVR.NS",
    "HUL": "HINDUNILVR.NS",
    "ITC": "ITC.NS",
    "BHARTI AIRTEL": "BHARTIARTL.NS",
    "AIRTEL": "BHARTIARTL.NS",
    "BAJAJ FINANCE": "BAJFINANCE.NS",
    "KOTAK BANK": "KOTAKBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "LARSEN": "LT.NS",
    "L&T": "LT.NS",
    "LT": "LT.NS",
    "MARUTI": "MARUTI.NS",
    "MARUTI SUZUKI": "MARUTI.NS",
    "ASIAN PAINTS": "ASIANPAINT.NS",
    "WIPRO": "WIPRO.NS",
    "TATA MOTORS": "TATAMOTORS.NS",
    "TATA STEEL": "TATASTEEL.NS",
    "ADANI ENTERPRISES": "ADANIENT.NS",
    "ADANI": "ADANIENT.NS",
    "SUN PHARMA": "SUNPHARMA.NS",
    "AXIS BANK": "AXISBANK.NS",
    "NTPC": "NTPC.NS",
    "ONGC": "ONGC.NS",
    "TITAN": "TITAN.NS",
    "ULTRATECH": "ULTRACEMCO.NS",
}

INDEX_ALIASES = {
    "NIFTY": "^NSEI",
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "BANKNIFTY": "^NSEBANK",
}


def resolve_ticker(query: str, default_exchange: str = "NS") -> str:
    """Best-effort resolution of a user-typed name/symbol to a yfinance ticker.
    `default_exchange` ('NS' or 'BO') is used for bare symbols not in the maps above."""
    q = query.strip().upper()
    if q in POPULAR_STOCKS:
        return POPULAR_STOCKS[q]
    if q in INDEX_ALIASES:
        return INDEX_ALIASES[q]
    if q.startswith("^") or q.endswith(".NS") or q.endswith(".BO"):
        return q
    return f"{q}.{default_exchange}"


def to_tradingview_symbol(ticker: str) -> str:
    """Map a yfinance-style ticker to a TradingView widget symbol (EXCHANGE:CODE)."""
    t = ticker.upper()
    if t == "^NSEI":
        return "NSE:NIFTY"
    if t == "^BSESN":
        return "BSE:SENSEX"
    if t == "^NSEBANK":
        return "NSE:BANKNIFTY"
    if t.endswith(".NS"):
        return f"NSE:{t[:-3]}"
    if t.endswith(".BO"):
        return f"BSE:{t[:-3]}"
    return f"NSE:{t}"


def get_quote(ticker: str) -> dict:
    resolved = resolve_ticker(ticker)
    t = yf.Ticker(resolved)
    fi = t.fast_info
    return {
        "ticker": resolved,
        "last_price": fi.get("lastPrice"),
        "previous_close": fi.get("previousClose"),
        "open": fi.get("open"),
        "day_high": fi.get("dayHigh"),
        "day_low": fi.get("dayLow"),
        "year_high": fi.get("yearHigh"),
        "year_low": fi.get("yearLow"),
        "volume": fi.get("lastVolume"),
        "market_cap": fi.get("marketCap"),
        "currency": fi.get("currency", "INR"),
        "exchange": fi.get("exchange"),
    }


def get_history(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    resolved = resolve_ticker(ticker)
    df = yf.Ticker(resolved).history(period=period, interval=interval)
    if df.empty:
        raise ValueError(f"No price history found for '{ticker}' ({resolved})")
    return df


def get_fundamentals(ticker: str) -> dict:
    resolved = resolve_ticker(ticker)
    info = yf.Ticker(resolved).info
    keys = [
        "longName", "sector", "industry", "marketCap", "trailingPE",
        "forwardPE", "priceToBook", "dividendYield", "beta",
        "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "totalRevenue",
        "revenueGrowth", "grossMargins", "operatingMargins", "profitMargins",
        "returnOnEquity", "debtToEquity", "freeCashflow", "recommendationKey",
        "targetMeanPrice", "numberOfAnalystOpinions",
    ]
    return {k: info.get(k) for k in keys}


def get_news(ticker: str, limit: int = 5) -> list[dict]:
    resolved = resolve_ticker(ticker)
    items = yf.Ticker(resolved).news or []
    out = []
    for it in items[:limit]:
        content = it.get("content", it)
        out.append({
            "title": content.get("title") or it.get("title"),
            "publisher": (content.get("provider") or {}).get("displayName") if isinstance(content.get("provider"), dict) else it.get("publisher"),
            "link": (content.get("canonicalUrl") or {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else it.get("link"),
        })
    return out


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["Close"]

    out["SMA_20"] = close.rolling(20).mean()
    out["SMA_50"] = close.rolling(50).mean()
    out["EMA_12"] = close.ewm(span=12, adjust=False).mean()
    out["EMA_26"] = close.ewm(span=26, adjust=False).mean()

    out["MACD"] = out["EMA_12"] - out["EMA_26"]
    out["MACD_signal"] = out["MACD"].ewm(span=9, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    out["RSI_14"] = 100 - (100 / (1 + rs))

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    out["BB_upper"] = mid + 2 * std
    out["BB_lower"] = mid - 2 * std

    return out


def technical_summary(ticker: str, period: str = "6mo") -> dict:
    resolved = resolve_ticker(ticker)
    df = compute_indicators(get_history(resolved, period=period))
    last = df.iloc[-1]
    return {
        "ticker": resolved,
        "close": round(float(last["Close"]), 2),
        "sma_20": round(float(last["SMA_20"]), 2) if pd.notna(last["SMA_20"]) else None,
        "sma_50": round(float(last["SMA_50"]), 2) if pd.notna(last["SMA_50"]) else None,
        "rsi_14": round(float(last["RSI_14"]), 2) if pd.notna(last["RSI_14"]) else None,
        "macd": round(float(last["MACD"]), 3) if pd.notna(last["MACD"]) else None,
        "macd_signal": round(float(last["MACD_signal"]), 3) if pd.notna(last["MACD_signal"]) else None,
        "bb_upper": round(float(last["BB_upper"]), 2) if pd.notna(last["BB_upper"]) else None,
        "bb_lower": round(float(last["BB_lower"]), 2) if pd.notna(last["BB_lower"]) else None,
        "trend": "bullish" if last["SMA_20"] > last["SMA_50"] else "bearish",
    }


def support_resistance_levels(
    df: pd.DataFrame, window: int = 10, tolerance_pct: float = 1.5, max_levels: int = 3
) -> dict:
    """Detect swing-high/low pivots (local extrema over `window` bars on each side),
    cluster nearby pivots within `tolerance_pct` of each other, and rank clusters by
    how many times price touched them. Returns the strongest levels above/below the
    last close."""
    highs, lows = df["High"], df["Low"]
    n = len(df)
    pivot_highs: list[float] = []
    pivot_lows: list[float] = []
    for i in range(window, n - window):
        seg_high = highs.iloc[i - window : i + window + 1]
        if highs.iloc[i] == seg_high.max():
            pivot_highs.append(float(highs.iloc[i]))
        seg_low = lows.iloc[i - window : i + window + 1]
        if lows.iloc[i] == seg_low.min():
            pivot_lows.append(float(lows.iloc[i]))

    def cluster(levels: list[float]) -> list[tuple[float, int]]:
        if not levels:
            return []
        levels = sorted(levels)
        clusters = [[levels[0]]]
        for lvl in levels[1:]:
            if abs(lvl - clusters[-1][-1]) / clusters[-1][-1] * 100 <= tolerance_pct:
                clusters[-1].append(lvl)
            else:
                clusters.append([lvl])
        return [(sum(c) / len(c), len(c)) for c in clusters]

    last_close = float(df["Close"].iloc[-1])
    res_clusters = sorted(
        (c for c in cluster(pivot_highs) if c[0] > last_close), key=lambda c: -c[1]
    )[:max_levels]
    sup_clusters = sorted(
        (c for c in cluster(pivot_lows) if c[0] < last_close), key=lambda c: -c[1]
    )[:max_levels]

    return {
        "resistance": sorted(round(lvl, 2) for lvl, _ in res_clusters),
        "support": sorted((round(lvl, 2) for lvl, _ in sup_clusters), reverse=True),
    }


def support_resistance(ticker: str, period: str = "6mo", interval: str = "1d") -> dict:
    resolved = resolve_ticker(ticker)
    df = get_history(resolved, period=period, interval=interval)
    levels = support_resistance_levels(df)
    levels["ticker"] = resolved
    levels["last_close"] = round(float(df["Close"].iloc[-1]), 2)
    return levels
