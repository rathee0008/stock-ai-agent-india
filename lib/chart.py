"""Pro candlestick chart (indicators + support/resistance) built from yfinance OHLC
data — a fallback for markets, like NSE/BSE, that TradingView's free embeddable widget
won't serve (see tradingview.py). Expects `df` to already carry indicator columns from
market_data.compute_indicators (SMA_20, SMA_50, EMA_12, EMA_26, MACD, MACD_signal,
RSI_14, BB_upper, BB_lower)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# TradingView-style dark palette
BG = "#131722"
GRID = "#1e222d"
AXIS_LINE = "#2a2e39"
TEXT = "#d1d4dc"
MUTED = "#787b86"
UP = "#26a69a"
DOWN = "#ef5350"
FONT_FAMILY = "'Trebuchet MS', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif"


def _section_label(fig: go.Figure, text: str, row: int, rows: int, row_heights: list[float]) -> None:
    """Pin a small muted caption to the top-left corner of a subplot row."""
    total = sum(row_heights)
    gaps = 0.03 * (rows - 1)
    usable = 1 - gaps
    y_top = 1.0
    for i, h in enumerate(row_heights):
        if i == row - 1:
            break
        y_top -= usable * (h / total) + 0.03
    fig.add_annotation(
        text=text, xref="paper", yref="paper",
        x=0.005, y=y_top - 0.012, xanchor="left", yanchor="top",
        showarrow=False, font=dict(size=11, color=MUTED, family=FONT_FAMILY),
    )


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
        row_heights.append(0.14)
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

    # --- Price candles ----------------------------------------------------
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            increasing=dict(line=dict(color=UP, width=1), fillcolor=UP),
            decreasing=dict(line=dict(color=DOWN, width=1), fillcolor=DOWN),
            name="Price",
            showlegend=False,
        ),
        row=1, col=1,
    )

    if show_sma:
        if "SMA_20" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA_20"], name="SMA 20", line=dict(width=1.4, color="#42a5f5")), row=1, col=1)
        if "SMA_50" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], name="SMA 50", line=dict(width=1.4, color="#ffb74d")), row=1, col=1)

    if show_ema:
        if "EMA_12" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA_12"], name="EMA 12", line=dict(width=1.2, color="#ab47bc", dash="dot")), row=1, col=1)
        if "EMA_26" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA_26"], name="EMA 26", line=dict(width=1.2, color="#ec407a", dash="dot")), row=1, col=1)

    if show_bb and "BB_upper" in df and "BB_lower" in df:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], name="BB upper", line=dict(width=1, color="rgba(148,163,184,0.55)")), row=1, col=1)
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["BB_lower"], name="BB lower",
                line=dict(width=1, color="rgba(148,163,184,0.55)"),
                fill="tonexty", fillcolor="rgba(148,163,184,0.08)",
            ),
            row=1, col=1,
        )

    for lvl in (resistance_levels or []):
        fig.add_hline(
            y=lvl, line=dict(color=DOWN, width=1, dash="dash"), row=1, col=1,
            annotation_text=f" R {lvl:g} ", annotation_position="right",
            annotation_font=dict(color="#ffffff", size=10, family=FONT_FAMILY),
            annotation_bgcolor=DOWN, annotation_borderpad=2,
        )
    for lvl in (support_levels or []):
        fig.add_hline(
            y=lvl, line=dict(color=UP, width=1, dash="dash"), row=1, col=1,
            annotation_text=f" S {lvl:g} ", annotation_position="right",
            annotation_font=dict(color="#ffffff", size=10, family=FONT_FAMILY),
            annotation_bgcolor=UP, annotation_borderpad=2,
        )

    # Faint watermark of the ticker behind the price panel
    fig.add_annotation(
        text=title.split(" ")[0], xref="x domain", yref="y domain", row=1, col=1,
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=64, color="rgba(255,255,255,0.035)", family=FONT_FAMILY),
    )

    # --- Volume -------------------------------------------------------------
    if show_volume:
        vol_colors = ["rgba(38,166,154,0.55)" if c >= o else "rgba(239,83,80,0.55)" for o, c in zip(df["Open"], df["Close"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=vol_colors, marker_line_width=0, name="Volume", showlegend=False), row=row_of["volume"], col=1)
        fig.update_yaxes(title_text="Volume", title_font=dict(size=10, color=MUTED), row=row_of["volume"], col=1)

    # --- RSI ------------------------------------------------------------
    if show_rsi and "RSI_14" in df:
        r = row_of["rsi"]
        fig.add_hrect(y0=70, y1=100, line_width=0, fillcolor=DOWN, opacity=0.06, row=r, col=1)
        fig.add_hrect(y0=0, y1=30, line_width=0, fillcolor=UP, opacity=0.06, row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI_14"], name="RSI 14", line=dict(color="#eab308", width=1.4), showlegend=False), row=r, col=1)
        fig.add_hline(y=70, line=dict(color="rgba(239,83,80,0.45)", width=1, dash="dot"), row=r, col=1)
        fig.add_hline(y=30, line=dict(color="rgba(38,166,154,0.45)", width=1, dash="dot"), row=r, col=1)
        fig.update_yaxes(title_text="RSI", title_font=dict(size=10, color=MUTED), range=[0, 100], tickvals=[30, 50, 70], row=r, col=1)

    # --- MACD ------------------------------------------------------------
    if show_macd and "MACD" in df and "MACD_signal" in df:
        r = row_of["macd"]
        hist = df["MACD"] - df["MACD_signal"]
        hist_colors = ["rgba(38,166,154,0.7)" if v >= 0 else "rgba(239,83,80,0.7)" for v in hist]
        fig.add_trace(go.Bar(x=df.index, y=hist, marker_color=hist_colors, marker_line_width=0, name="MACD hist", showlegend=False), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#42a5f5", width=1.4)), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal", line=dict(color="#ffb74d", width=1.4)), row=r, col=1)
        fig.update_yaxes(title_text="MACD", title_font=dict(size=10, color=MUTED), row=r, col=1)

    # --- Section captions --------------------------------------------------
    section_titles = {"volume": "Volume", "rsi": "RSI (14)", "macd": "MACD (12, 26, 9)"}
    for key, text in section_titles.items():
        if key in row_of:
            _section_label(fig, text, row_of[key], rows, row_heights)

    # --- Global layout -------------------------------------------------
    fig.update_layout(
        title=dict(text=title, font=dict(size=17, color=TEXT, family=FONT_FAMILY), x=0.01, xanchor="left"),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family=FONT_FAMILY, color=TEXT, size=12),
        height=440 + 130 * (rows - 1),
        margin=dict(l=10, r=60, t=50, b=10),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=11),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1e222d", bordercolor="#2a2e39", font=dict(size=11, color=TEXT, family=FONT_FAMILY)),
    )
    fig.update_xaxes(
        rangeslider_visible=False, showgrid=True, gridcolor=GRID, gridwidth=1,
        showline=True, linecolor=AXIS_LINE, zeroline=False,
        showspikes=True, spikecolor="#758696", spikethickness=1, spikedash="solid", spikemode="across",
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=GRID, gridwidth=1,
        showline=True, linecolor=AXIS_LINE, zeroline=False,
        side="right",
    )

    return fig
