"""
Shipment Repository Module.
Demonstrates:
- Inheritance (Inherits from BaseRepository)
- Polymorphism (Overriding add, update, delete, get_by_id, get_all, search)
- Automated Business Workflow (Order ID & Tracking Generation, Auto-advance rules)
"""
from datetime import date, datetime
import random
import string
from typing import Any, Dict, List, Optional, Tuple
from .base import BaseRepository
from ..models.shipment import Shipment
from ..core.exceptions import (
    ValidationError,
    RecordNotFoundException
)


class ShipmentRepository(BaseRepository):
    """
    Repository handling shipping orders, fulfillment workflows, and analytics.
    """

    PROCESSING_AFTER_MINUTES = 5
    DELIVERED_AFTER_MINUTES = 24 * 60
    STATUS_ORDER = {"Pending": 0, "Being Processed": 1, "Delivered": 2}   # forward direction

    def __init__(self):
        super().__init__(table_name="shipping_orders", id_column="order_id")

    def _map_row(self, row: Tuple[Any, ...]) -> Shipment:
        return Shipment.from_row(row)

    def generate_order_id(self) -> str:
        """Generates sequential order identifier in format ORD-YYYY-XXX."""
        year = date.today().year
        prefix = f"ORD-{year}-"
        row = self.execute_query(
            "SELECT order_id FROM shipping_orders WHERE order_id LIKE %s ORDER BY order_id DESC LIMIT 1",
            (f"{prefix}%",),
            fetch="one"
        )
        if row and row[0]:
            try:
                next_number = int(str(row[0]).split("-")[-1]) + 1
            except ValueError:
                next_number = 1
        else:
            next_number = 1
        return f"{prefix}{next_number:03d}"

    @staticmethod
    def generate_tracking_number() -> str:
        """Generates a random unique tracking code (e.g. TRK-XXXX-YYYY)."""
        part1 = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        part2 = "".join(random.choices(string.digits, k=4))
        return f"TRK-{part1}-{part2}"

    def add(self, shipment: Shipment) -> str:
        """Inserts a new shipment order."""
        shipment.validate()

        if not shipment.order_id:
            shipment.order_id = self.generate_order_id()
        if not shipment.tracking_number:
            shipment.tracking_number = self.generate_tracking_number()

        query = """
            INSERT INTO shipping_orders
            (order_id, recipient_id, recipient_name, address, order_date, status, tracking_number, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        params = (
            shipment.order_id,
            shipment.recipient_id,
            shipment.recipient_name,
            shipment.address,
            shipment.order_date,
            shipment.status,
            shipment.tracking_number
        )
        self.execute_query(query, params)
        return shipment.order_id

    def update(self, shipment: Shipment) -> bool:
        """Updates status and tracking info of a shipment order."""
        if not shipment.order_id:
            raise ValidationError("Order ID is required to update shipment.")

        delivery_date_val = shipment.delivery_date
        if shipment.status == "Delivered" and not delivery_date_val:
            delivery_date_val = date.today()

        # A manual status change restarts the auto-advance clock; moving a shipment BACKWARD
        # also switches auto-advance off for it, so it is not pushed forward again on refresh.
        previous = self.execute_query(
            "SELECT status FROM shipping_orders WHERE order_id = %s",
            (shipment.order_id,), fetch="one")
        old_status = previous[0] if previous else None
        status_changed = old_status is not None and old_status != shipment.status
        moved_back = (status_changed
                      and old_status in self.STATUS_ORDER and shipment.status in self.STATUS_ORDER
                      and self.STATUS_ORDER[shipment.status] < self.STATUS_ORDER[old_status])
        extra = ""                                   # fixed SQL fragments, not user input
        if status_changed:
            extra += ", status_changed_at = NOW()"
        if moved_back:
            extra += ", auto_advance = 0"

        query = f"""
            UPDATE shipping_orders
            SET recipient_id = %s, recipient_name = %s,
                status = %s, tracking_number = %s, delivery_date = %s{extra}
            WHERE order_id = %s
        """
        params = (
            shipment.recipient_id,
            shipment.recipient_name,
            shipment.status,
            shipment.tracking_number,
            delivery_date_val,
            shipment.order_id
        )
        self.execute_query(query, params)
        return True

    def delete(self, order_id: str) -> bool:
        if not order_id:
            raise RecordNotFoundException("Please select a shipment to delete.")
        self.execute_query("DELETE FROM shipping_orders WHERE order_id = %s", (order_id,))
        return True

    def get_by_id(self, order_id: str) -> Optional[Shipment]:
        row = self.execute_query(
            "SELECT order_id, recipient_id, recipient_name, order_date, status, tracking_number, delivery_date FROM shipping_orders WHERE order_id = %s",
            (order_id,),
            fetch="one"
        )
        return self._map_row(row) if row else None

    def get_all(self) -> List[Shipment]:
        rows = self.execute_query(
            "SELECT order_id, recipient_id, recipient_name, order_date, status, tracking_number, delivery_date FROM shipping_orders ORDER BY order_date DESC, order_id DESC",
            fetch="all"
        )
        return [self._map_row(r) for r in rows] if rows else []

    def search(self, column: str, query: str) -> List[Shipment]:
        valid_cols = {
            "Order ID": "order_id",
            "order_id": "order_id",
            "Recipient": "recipient_name",
            "recipient_name": "recipient_name",
            "Status": "status",
            "status": "status",
            "Tracking": "tracking_number",
            "tracking_number": "tracking_number"
        }
        col = valid_cols.get(column, "recipient_name")
        rows = self.execute_query(
            f"SELECT order_id, recipient_id, recipient_name, order_date, status, tracking_number, delivery_date FROM shipping_orders WHERE {col} LIKE %s ORDER BY order_date DESC",
            (f"%{query}%",),
            fetch="all"
        )
        return [self._map_row(r) for r in rows] if rows else []

    def get_stats(self) -> Dict[str, int]:
        """Calculates current shipment metrics."""
        query = """
            SELECT
                COALESCE(SUM(status = 'Pending'), 0),
                COALESCE(SUM(status = 'Being Processed'), 0),
                COALESCE(SUM(status = 'Delivered'), 0),
                COALESCE(SUM(status = 'Pending' AND COALESCE(created_at, order_date) <= NOW() - INTERVAL 24 HOUR), 0)
            FROM shipping_orders
        """
        row = self.execute_query(query, fetch="one")
        if row:
            return {
                "pending": int(row[0]),
                "processing": int(row[1]),
                "delivered": int(row[2]),
                "old_pending": int(row[3])
            }
        return {"pending": 0, "processing": 0, "delivered": 0, "old_pending": 0}

    def auto_advance_shipments(self) -> int:
        """Automates background status transitions based on elapsed time."""
        try:
            changed = 0
            # Delivered transition
            deliv_query = """
                UPDATE shipping_orders
                SET status='Delivered', delivery_date=COALESCE(delivery_date, CURDATE())
                WHERE status IN ('Pending', 'Being Processed')
                    AND auto_advance = 1
                    AND status_changed_at <= NOW() - INTERVAL %s MINUTE
            """
            changed += self.execute_query(deliv_query, (self.DELIVERED_AFTER_MINUTES,), fetch="rowcount") or 0

            # Processing transition
            proc_query = """
                UPDATE shipping_orders
                SET status='Being Processed'
                WHERE status='Pending'
                  AND auto_advance = 1
                  AND status_changed_at <= NOW() - INTERVAL %s MINUTE
            """
            changed += self.execute_query(proc_query, (self.PROCESSING_AFTER_MINUTES,), fetch="rowcount") or 0
            return changed
        except Exception:
            return 0