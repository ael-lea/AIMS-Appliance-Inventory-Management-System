"""
Shipping Rules & Auto-Advance Module.
Exposes background status automation.
"""
from .repositories.shipment_repo import ShipmentRepository


def auto_advance_shipments() -> int:
    """Automates advancement of shipments by age."""
    return ShipmentRepository().auto_advance_shipments()


__all__ = ["auto_advance_shipments"]
