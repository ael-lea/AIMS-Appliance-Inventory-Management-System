"""Small formatting helpers shared by the whole package."""


def peso(value):
    """Format a number as Philippine pesos, e.g. 1234.5 -> '₱1,234.50'."""
    return f"₱{float(value or 0):,.2f}"


def format_date(value, pattern="%Y-%m-%d"):
    """Format a date/datetime; return '' for empty values and text as-is."""
    if not value:
        return ""
    return value.strftime(pattern) if hasattr(value, "strftime") else str(value)
