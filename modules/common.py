"""Shared UI helpers."""

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
