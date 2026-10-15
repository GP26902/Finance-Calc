"""Shared UI helpers."""
import re

import streamlit as st

CURRENCY_SYMBOLS = {
    "United States (USA)": "$",
    "India": "₹",
    "Canada": "C$",
    "United Kingdom": "£",
    "Other / Custom": "$",
}


def fmt(cur: str, value: float, decimals: int = 2) -> str:
    """Format a number as currency, e.g. fmt('$', -1234.5) -> '-$1,234.50'."""
    sign = "-" if value < 0 else ""
    return f"{sign}{cur}{abs(value):,.{decimals}f}"


_UNESCAPED_DOLLAR = re.compile(r"(?<!\\)\$")


def esc(text: str) -> str:
    """Escape dollar signs for Streamlit markdown, which otherwise pairs two of them into LaTeX math.
    Idempotent: already-escaped dollar signs are left alone."""
    return _UNESCAPED_DOLLAR.sub(r"\\$", text)


def success(body: str, **kw):
    return st.success(esc(body), **kw)


def info(body: str, **kw):
    return st.info(esc(body), **kw)


def warning(body: str, **kw):
    return st.warning(esc(body), **kw)


def error(body: str, **kw):
    return st.error(esc(body), **kw)


def caption(body: str, **kw):
    return st.caption(esc(body), **kw)
