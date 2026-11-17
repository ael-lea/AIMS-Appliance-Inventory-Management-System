"""
Product Inventory Module.
Exposes OOP ProductView and backward-compatible helper functions.
"""
from typing import Any, Tuple
from .views.products_view import ProductView
from .repositories.product_repo import ProductRepository
from .models.product import Product
from .core.database import DatabaseManager


def product_form(window) -> ProductView:
    """Backward-compatible entry point returning the ProductView instance."""
    return ProductView(window)


def connect_database() -> Tuple[Any, Any]:
    """Backward-compatible database connection accessor."""
    try:
        return DatabaseManager.get_cursor_and_connection()
    except Exception:
        return None, None


__all__ = [
    "ProductView",
    "ProductRepository",
    "Product",
    "product_form",
    "connect_database"
]
