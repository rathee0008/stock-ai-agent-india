"""Embeds for TradingView's free public widgets (no API key / no paid account needed).

Note: TradingView's embeddable widgets do not carry redistribution rights for NSE/BSE
(India) data — symbols like "NSE:RELIANCE" render fine on tradingview.com itself but the
embedded widget shows "This symbol is only available on TradingView." We still expose
`chart_url` so the app can link out to the real, fully-live TradingView page instead."""

import streamlit.components.v1 as components


def chart_url(symbol: str) -> str:
    """Deep link to the symbol's live chart on tradingview.com itself (works for NSE/BSE)."""
    return f"https://www.tradingview.com/symbols/{symbol.replace(':', '-')}/"


def advanced_chart(symbol: str = "NSE:RELIANCE", height: int = 610, theme: str = "dark") -> None:
    """Full interactive live chart. Users can search/switch to ANY listed stock from the
    widget's own built-in symbol search box (magnifying glass, top-left of the widget)."""
    html = f"""
    <div class="tradingview-widget-container">
      <div id="tv_chart"></div>
      <script src="https://s3.tradingview.com/tv.js"></script>
      <script>
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{symbol}",
        "interval": "D",
        "timezone": "Asia/Kolkata",
        "theme": "{theme}",
        "style": "1",
        "locale": "en",
        "allow_symbol_change": true,
        "hide_side_toolbar": false,
        "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"],
        "support_host": "https://www.tradingview.com",
        "container_id": "tv_chart"
      }});
      </script>
    </div>
    """
    components.html(html, height=height)


def mini_chart(symbol: str = "NSE:RELIANCE", height: int = 220, theme: str = "dark") -> None:
    """Small sparkline-style overview, e.g. for a watchlist row."""
    html = f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
      {{
        "symbol": "{symbol}",
        "width": "100%",
        "height": {height},
        "locale": "en",
        "dateRange": "3M",
        "colorTheme": "{theme}",
        "isTransparent": true,
        "autosize": true
      }}
      </script>
    </div>
    """
    components.html(html, height=height + 10)
