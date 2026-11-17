"""
Sales & Analytics Module.
Exposes OOP SalesView and backward-compatible helper functions.
"""
from typing import Any, Tuple
from .views.sales_view import SalesView
from .repositories.sales_repo import SalesRepository
from .models.sale import Sale
from .core.database import DatabaseManager


def sales_form(window) -> SalesView:
    """Backward-compatible entry point returning the SalesView instance."""
    return SalesView(window)


def connect_database() -> Tuple[Any, Any]:
    """Backward-compatible database connection accessor."""
    try:
        return DatabaseManager.get_cursor_and_connection()
    except Exception:
        return None, None


__all__ = [
    "SalesView",
    "SalesRepository",
    "Sale",
    "sales_form",
    "connect_database"
]
