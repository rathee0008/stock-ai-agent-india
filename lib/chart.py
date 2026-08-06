"""Pro candlestick chart (indicators + support/resistance) built from yfinance OHLC
data — a fallback for markets, like NSE/BSE, that TradingView's free embeddable widget
won't serve (see tradingview.py). Expects `df` to already carry indicator columns from
market_data.compute_indicators (SMA_20, SMA_50, EMA_12, EMA_26, MACD, MACD_signal,
RSI_14, BB_upper, BB_lower)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

UP = "#23c17d"
DOWN = "#f0546a"


def candlestick_figure(
    df: pd.DataFrame,
    title: str,
    *,
    show_sma: bool = True,
    show_ema: bool = False,
    show_bb: bool = False,
    show_volume: bool = True,
    show_rsi: bool = True,
    show_macd: bool = True,
    support_levels: list[float] | None = None,
    resistance_levels: list[float] | None = None,
) -> go.Figure:
    row = 1
    row_of = {"price": 1}
    row_heights = [0.5]
    if show_volume:
        row += 1
        row_of["volume"] = row
        row_heights.append(0.15)
    if show_rsi:
        row += 1
        row_of["rsi"] = row
        row_heights.append(0.17)
    if show_macd:
        row += 1
        row_of["macd"] = row
        row_heights.append(0.18)
    rows = row

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color=UP,
            decreasing_line_color=DOWN,
            name="Price",
        ),
        row=1,
        col=1,
    )

    if show_sma:
        if "SMA_20" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA_20"], name="SMA 20", line=dict(width=1.3, color="#4f8cff")), row=1, col=1)
        if "SMA_50" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], name="SMA 50", line=dict(width=1.3, color="#f0a500")), row=1, col=1)

    if show_ema:
        if "EMA_12" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA_12"], name="EMA 12", line=dict(width=1.2, color="#8b5cf6", dash="dot")), row=1, col=1)
        if "EMA_26" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA_26"], name="EMA 26", line=dict(width=1.2, color="#ec4899", dash="dot")), row=1, col=1)

    if show_bb and "BB_upper" in df and "BB_lower" in df:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], name="BB upper", line=dict(width=1, color="rgba(148,163,184,0.6)")), row=1, col=1)
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["BB_lower"], name="BB lower",
                line=dict(width=1, color="rgba(148,163,184,0.6)"),
                fill="tonexty", fillcolor="rgba(148,163,184,0.08)",
            ),
            row=1, col=1,
        )

    for lvl in (resistance_levels or []):
        fig.add_hline(
            y=lvl, line=dict(color=DOWN, width=1, dash="dash"),
            annotation_text=f"R {lvl:g}", annotation_position="right",
            annotation_font_color=DOWN, row=1, col=1,
        )
    for lvl in (support_levels or []):
        fig.add_hline(
            y=lvl, line=dict(color=UP, width=1, dash="dash"),
            annotation_text=f"S {lvl:g}", annotation_position="right",
            annotation_font_color=UP, row=1, col=1,
        )

    if show_volume:
        vol_colors = [UP if c >= o else DOWN for o, c in zip(df["Open"], df["Close"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=vol_colors, name="Volume"), row=row_of["volume"], col=1)
        fig.update_yaxes(title_text="Volume", row=row_of["volume"], col=1)

    if show_rsi and "RSI_14" in df:
        r = row_of["rsi"]
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI_14"], name="RSI 14", line=dict(color="#eab308")), row=r, col=1)
        fig.add_hline(y=70, line=dict(color="rgba(240,84,106,0.5)", dash="dot"), row=r, col=1)
        fig.add_hline(y=30, line=dict(color="rgba(35,193,125,0.5)", dash="dot"), row=r, col=1)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=r, col=1)

    if show_macd and "MACD" in df and "MACD_signal" in df:
        r = row_of["macd"]
        hist = df["MACD"] - df["MACD_signal"]
        hist_colors = [UP if v >= 0 else DOWN for v in hist]
        fig.add_trace(go.Bar(x=df.index, y=hist, marker_color=hist_colors, name="MACD hist"), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#4f8cff", width=1.3)), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal", line=dict(color="#f0a500", width=1.3)), row=r, col=1)
        fig.update_yaxes(title_text="MACD", row=r, col=1)

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=420 + 130 * (rows - 1),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(rangeslider_visible=False)

    return fig
