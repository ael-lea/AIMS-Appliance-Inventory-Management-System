"""
Shipment Orders Module.
Exposes OOP ShipmentView and backward-compatible helper functions.
"""
from typing import Any, Tuple
from .views.shipment_view import ShipmentView
from .repositories.shipment_repo import ShipmentRepository
from .models.shipment import Shipment
from .core.database import DatabaseManager


def shipment_form(window) -> ShipmentView:
    """Backward-compatible entry point returning the ShipmentView instance."""
    return ShipmentView(window)


def connect_database() -> Tuple[Any, Any]:
    """Backward-compatible database connection accessor."""
    try:
        return DatabaseManager.get_cursor_and_connection()
    except Exception:
        return None, None


__all__ = [
    "ShipmentView",
    "ShipmentRepository",
    "Shipment",
    "shipment_form",
    "connect_database"
]
