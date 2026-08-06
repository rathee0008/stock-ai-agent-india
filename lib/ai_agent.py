"""Claude-powered analyst that can call live market-data tools before answering.

Requires an Anthropic API key (ANTHROPIC_API_KEY env var or st.secrets["ANTHROPIC_API_KEY"]).
This agent answers questions and summarizes data — it is informational only and does
not place trades and is not a licensed financial advisor.
"""
from __future__ import annotations

import json

import anthropic

from lib import market_data as md

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = (
    "You are an Indian equity research assistant embedded in a Streamlit app, covering "
    "NSE and BSE listed stocks and indices (e.g. NIFTY 50, SENSEX, BANK NIFTY). "
    "You have tools to pull live quotes, price history, fundamentals, technical "
    "indicators, and recent news for any Indian stock (by company name or NSE/BSE ticker). "
    "Use them before answering questions that need current data — never guess a price or "
    "number. State figures in INR. Always be clear this is general market information, not "
    "personalized investment advice, and that you are not a licensed financial advisor. "
    "Keep answers concise and cite the specific numbers you pulled."
)

TOOLS = [
    {
        "name": "get_quote",
        "description": "Get the latest quote (price, day range, volume, market cap) for an Indian stock or index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Company name or ticker, e.g. 'TCS', 'Reliance', 'INFY.NS', 'NIFTY 50'.",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_fundamentals",
        "description": "Get fundamental metrics (P/E, margins, growth, analyst targets) for an Indian stock.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_technical_summary",
        "description": "Get computed technical indicators (SMA, RSI, MACD, Bollinger Bands, trend) for an Indian stock.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "period": {"type": "string", "description": "e.g. 1mo, 6mo, 1y", "default": "6mo"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_news",
        "description": "Get recent news headlines for an Indian stock.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_support_resistance",
        "description": "Get computed support and resistance price levels (from swing-high/low pivot clustering) for an Indian stock.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "period": {"type": "string", "description": "e.g. 1mo, 6mo, 1y", "default": "6mo"},
            },
            "required": ["ticker"],
        },
    },
]


def _run_tool(name: str, tool_input: dict):
    if name == "get_quote":
        return md.get_quote(tool_input["ticker"])
    if name == "get_fundamentals":
        return md.get_fundamentals(tool_input["ticker"])
    if name == "get_technical_summary":
        return md.technical_summary(tool_input["ticker"], tool_input.get("period", "6mo"))
    if name == "get_news":
        return md.get_news(tool_input["ticker"])
    if name == "get_support_resistance":
        return md.support_resistance(tool_input["ticker"], tool_input.get("period", "6mo"))
    return {"error": f"unknown tool {name}"}


def chat(api_key: str, history: list[dict], user_message: str) -> tuple[str, list[dict]]:
    """history/return format: list of {"role": "user"|"assistant", "content": str} for display.
    Returns (assistant_reply_text, updated_history)."""
    client = anthropic.Anthropic(api_key=api_key)

    messages = [{"role": h["role"], "content": h["content"]} for h in history]
    messages.append({"role": "user", "content": user_message})

    final_text_parts: list[str] = []

    for _ in range(6):  # cap tool-use round-trips
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if resp.stop_reason != "tool_use":
            final_text_parts = [b.text for b in resp.content if b.type == "text"]
            messages.append({"role": "assistant", "content": resp.content})
            break

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                result = _run_tool(block.name, block.input)
            except Exception as e:  # noqa: BLE001
                result = {"error": str(e)}
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
            })
        messages.append({"role": "user", "content": tool_results})
    else:
        final_text_parts = ["(Reached tool-call limit before finishing — try a narrower question.)"]

    reply = "\n".join(final_text_parts).strip() or "(no response)"
    updated_history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply},
    ]
    return reply, updated_history
