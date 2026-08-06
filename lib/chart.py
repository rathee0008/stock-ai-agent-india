"""Pro candlestick chart (indicators + support/resistance) built from yfinance OHLC
data — a fallback for markets, like NSE/BSE, that TradingView's free embeddable widget
won't serve (see tradingview.py). Expects `df` to already carry indicator columns from
market_data.compute_indicators (SMA_20, SMA_50, EMA_12, EMA_26, MACD, MACD_signal,
RSI_14, BB_upper, BB_lower, ATR_14, VWAP, STOCHRSI_K, STOCHRSI_D, PSAR, ICHI_*)."""
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


def _to_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Convert regular OHLC candles to Heikin-Ashi candles (smoothed trend view)."""
    ha = df.copy()
    ha_close = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = ha_close.copy()
    ha_open.iloc[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2
    ha["Open"] = ha_open
    ha["Close"] = ha_close
    ha["High"] = pd.concat([df["High"], ha_open, ha_close], axis=1).max(axis=1)
    ha["Low"] = pd.concat([df["Low"], ha_open, ha_close], axis=1).min(axis=1)
    return ha


def candlestick_figure(
    df: pd.DataFrame,
    title: str,
    *,
    chart_type: str = "Candlestick",
    show_sma: bool = True,
    show_ema: bool = False,
    show_bb: bool = False,
    show_vwap: bool = False,
    show_psar: bool = False,
    show_ichimoku: bool = False,
    show_volume: bool = True,
    show_rsi: bool = True,
    show_stochrsi: bool = False,
    show_macd: bool = True,
    show_atr: bool = False,
    show_returns: bool = False,
    log_scale: bool = False,
    compare_series: pd.Series | None = None,
    compare_label: str | None = None,
    support_levels: list[float] | None = None,
    resistance_levels: list[float] | None = None,
) -> go.Figure:
    row = 1
    row_of = {"price": 1}
    row_heights = [0.42]
    if show_returns or compare_series is not None:
        row += 1
        row_of["returns"] = row
        row_heights.append(0.13)
    if show_volume:
        row += 1
        row_of["volume"] = row
        row_heights.append(0.12)
    if show_rsi:
        row += 1
        row_of["rsi"] = row
        row_heights.append(0.14)
    if show_stochrsi:
        row += 1
        row_of["stochrsi"] = row
        row_heights.append(0.14)
    if show_macd:
        row += 1
        row_of["macd"] = row
        row_heights.append(0.15)
    if show_atr:
        row += 1
        row_of["atr"] = row
        row_heights.append(0.12)
    rows = row

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
    )

    # --- Price panel -------------------------------------------------------
    chart_type = (chart_type or "Candlestick").strip()
    if chart_type == "Heikin-Ashi":
        ha = _to_heikin_ashi(df)
        fig.add_trace(
            go.Candlestick(
                x=ha.index,
                open=ha["Open"], high=ha["High"], low=ha["Low"], close=ha["Close"],
                increasing=dict(line=dict(color=UP, width=1), fillcolor=UP),
                decreasing=dict(line=dict(color=DOWN, width=1), fillcolor=DOWN),
                name="Heikin-Ashi",
                showlegend=False,
            ),
            row=1, col=1,
        )
    elif chart_type == "Line":
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["Close"], mode="lines", name="Close",
                line=dict(color="#42a5f5", width=1.6), showlegend=False,
            ),
            row=1, col=1,
        )
    elif chart_type == "Area":
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["Close"], mode="lines", name="Close",
                line=dict(color="#42a5f5", width=1.6),
                fill="tozeroy", fillcolor="rgba(66,165,245,0.12)", showlegend=False,
            ),
            row=1, col=1,
        )
    else:
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

    if show_vwap and "VWAP" in df:
        fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(width=1.3, color="#26c6da", dash="dash")), row=1, col=1)

    if show_psar and "PSAR" in df:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["PSAR"], name="Parabolic SAR", mode="markers",
                marker=dict(size=3, color="#ffd54f"),
            ),
            row=1, col=1,
        )

    if show_ichimoku and "ICHI_SPAN_A" in df and "ICHI_SPAN_B" in df:
        fig.add_trace(go.Scatter(x=df.index, y=df["ICHI_SPAN_A"], name="Senkou A", line=dict(width=1, color="rgba(38,166,154,0.5)")), row=1, col=1)
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["ICHI_SPAN_B"], name="Senkou B",
                line=dict(width=1, color="rgba(239,83,80,0.5)"),
                fill="tonexty", fillcolor="rgba(120,130,140,0.12)",
            ),
            row=1, col=1,
        )
        if "ICHI_TENKAN" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["ICHI_TENKAN"], name="Tenkan-sen", line=dict(width=1.2, color="#29b6f6")), row=1, col=1)
        if "ICHI_KIJUN" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["ICHI_KIJUN"], name="Kijun-sen", line=dict(width=1.2, color="#ff7043")), row=1, col=1)

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

    # --- Returns / benchmark comparison ----------------------------------
    if "returns" in row_of:
        r = row_of["returns"]
        base_close = df["Close"].iloc[0]
        own_returns = (df["Close"] / base_close - 1) * 100
        fig.add_trace(go.Scatter(x=df.index, y=own_returns, name="Return %", line=dict(color="#42a5f5", width=1.4)), row=r, col=1)
        if compare_series is not None and len(compare_series):
            fig.add_trace(
                go.Scatter(
                    x=compare_series.index, y=compare_series.values,
                    name=compare_label or "Benchmark",
                    line=dict(color="#ffb74d", width=1.4, dash="dot"),
                ),
                row=r, col=1,
            )
        fig.add_hline(y=0, line=dict(color=AXIS_LINE, width=1), row=r, col=1)
        fig.update_yaxes(title_text="Return %", title_font=dict(size=10, color=MUTED), row=r, col=1)

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

    # --- Stochastic RSI ------------------------------------------------------
    if show_stochrsi and "STOCHRSI_K" in df:
        r = row_of["stochrsi"]
        fig.add_hrect(y0=80, y1=100, line_width=0, fillcolor=DOWN, opacity=0.06, row=r, col=1)
        fig.add_hrect(y0=0, y1=20, line_width=0, fillcolor=UP, opacity=0.06, row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["STOCHRSI_K"], name="StochRSI %K", line=dict(color="#26c6da", width=1.4)), row=r, col=1)
        if "STOCHRSI_D" in df:
            fig.add_trace(go.Scatter(x=df.index, y=df["STOCHRSI_D"], name="StochRSI %D", line=dict(color="#ffb74d", width=1.2, dash="dot")), row=r, col=1)
        fig.add_hline(y=80, line=dict(color="rgba(239,83,80,0.45)", width=1, dash="dot"), row=r, col=1)
        fig.add_hline(y=20, line=dict(color="rgba(38,166,154,0.45)", width=1, dash="dot"), row=r, col=1)
        fig.update_yaxes(title_text="StochRSI", title_font=dict(size=10, color=MUTED), range=[0, 100], row=r, col=1)

    # --- MACD ------------------------------------------------------------
    if show_macd and "MACD" in df and "MACD_signal" in df:
        r = row_of["macd"]
        hist = df["MACD"] - df["MACD_signal"]
        hist_colors = ["rgba(38,166,154,0.7)" if v >= 0 else "rgba(239,83,80,0.7)" for v in hist]
        fig.add_trace(go.Bar(x=df.index, y=hist, marker_color=hist_colors, marker_line_width=0, name="MACD hist", showlegend=False), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#42a5f5", width=1.4)), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal", line=dict(color="#ffb74d", width=1.4)), row=r, col=1)
        fig.update_yaxes(title_text="MACD", title_font=dict(size=10, color=MUTED), row=r, col=1)

    # --- ATR -------------------------------------------------------------
    if show_atr and "ATR_14" in df:
        r = row_of["atr"]
        fig.add_trace(go.Scatter(x=df.index, y=df["ATR_14"], name="ATR 14", line=dict(color="#ab47bc", width=1.4), showlegend=False), row=r, col=1)
        fig.update_yaxes(title_text="ATR", title_font=dict(size=10, color=MUTED), row=r, col=1)

    # --- Section captions --------------------------------------------------
    section_titles = {
        "returns": f"Return % vs {compare_label}" if compare_label else "Return % (vs period start)",
        "volume": "Volume",
        "rsi": "RSI (14)",
        "stochrsi": "Stochastic RSI (14, 3, 3)",
        "macd": "MACD (12, 26, 9)",
        "atr": "ATR (14)",
    }
    for key, text in section_titles.items():
        if key in row_of:
            _section_label(fig, text, row_of[key], rows, row_heights)

    # --- Global layout -------------------------------------------------
    fig.update_layout(
        title=dict(text=title, font=dict(size=17, color=TEXT, family=FONT_FAMILY), x=0.01, xanchor="left"),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family=FONT_FAMILY, color=TEXT, size=12),
        height=420 + 115 * (rows - 1),
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
    if log_scale:
        fig.update_yaxes(type="log", row=1, col=1)

    return fig
