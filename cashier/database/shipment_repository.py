"""Reads and writes the shipping_orders table (shared with the Admin module)."""
from datetime import datetime

from cashier.database.base_repository import BaseRepository
from cashier.models import ShipmentRecord
from cashier.tracking import generate_tracking_number
from shipping_schema import ensure_shipping_schema

class ShipmentError(Exception):
    """A shipment rule was broken. The message is safe to show to the user."""


def _is_admin(role):
    return (role or "").strip().lower() == "admin"


class ShipmentRepository(BaseRepository):

    STATUSES = ("Pending", "Being Processed", "Delivered")
    SEARCH_COLUMNS = {                 # fixed whitelist -> safe to put in SQL
        "Order ID": "order_id",
        # "Sale Ref": "order_ref",
        "Recipient Name": "recipient_name",
        "Status": "status",
        "Tracking Number": "tracking_number",
    }

    # Automatic status change (seconds spent in a status before it moves on).
    # These are DEMO values so you can show it during a defense. For real use try
    # 24 * 3600 and 3 * 24 * 3600.
    AUTO_PROCESS_AFTER = 2 * 60        # Pending -> Being Processed
    AUTO_DELIVER_AFTER = 5 * 60        # Being Processed -> Delivered

    # ------------------------------------------------------------------ schema
    def ensure_schema(self):
        """Same definition the Admin page uses (shipping_schema.py), so either side can run first."""
        with self._database.cursor(commit=True) as cursor:
            ensure_shipping_schema(cursor)

    # ------------------------------------------------------------------ create
    def create_for_order(self, cursor, order_id, recipient_id, recipient_name, address,
                         order_date, tracking=None):
        """Create the shipment of a confirmed order (inside its transaction)."""
        cursor.execute("""
            INSERT INTO shipping_orders
                (order_id, order_ref, recipient_name, recipient_id, address,
                 order_date, status, tracking_number, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'Pending', %s, NOW())
        """, (order_id, order_id, recipient_name[:100], recipient_id,
              (address or "").strip() or None, order_date,
              (tracking or "").strip() or generate_tracking_number()))

    def create_from_sale(self, order_ref, customer, tracking=None):
        """'Create Shipment' button in Order History: ship a completed sale. Returns the new shipment ID."""
        customer = (customer or "").strip()
        if not customer:
            raise ShipmentError("Customer name is required.")
        with self._database.cursor(commit=True) as cursor:
            cursor.execute("SELECT status FROM orders WHERE order_id=%s", (order_ref,))
            sale = cursor.fetchone()
            if sale is None:
                raise ShipmentError("That order does not exist.")
            if sale[0] != "Completed":
                raise ShipmentError("Only completed orders can be shipped.")
            cursor.execute("SELECT order_id FROM shipping_orders WHERE order_ref=%s", (order_ref,))
            if cursor.fetchone() is not None:
                raise ShipmentError("This order already has a shipment.")
            order_id = self._next_id(cursor)
            cursor.execute("""
                INSERT INTO shipping_orders
                    (order_id, order_ref, recipient_name, order_date, status,
                     tracking_number, created_at)
                VALUES (%s, %s, %s, %s, 'Pending', %s, NOW())
            """, (order_id, order_ref, customer, datetime.now().date(), (tracking or "").strip() or generate_tracking_number()))
        return order_id

    def add(self, recipient_id, recipient_name, address, tracking=None):
        """Add a manual shipment (not linked to a sale) for a saved recipient. Returns its new ID."""
        if recipient_id is None or not (recipient_name or "").strip():
            raise ShipmentError("Select a recipient.")
        with self._database.cursor(commit=True) as cursor:
            order_id = self._next_id(cursor)
            cursor.execute("""
                INSERT INTO shipping_orders
                    (order_id, recipient_name, recipient_id, address,
                     order_date, status, tracking_number, created_at)
                VALUES (%s, %s, %s, %s, %s, 'Pending', %s, NOW())
            """, (order_id, recipient_name.strip()[:100], recipient_id,
                  (address or "").strip() or None, datetime.now().date(),
                  (tracking or "").strip() or generate_tracking_number()))
        return order_id

    @staticmethod
    def _next_id(cursor):
        prefix = f"ORD-{datetime.now().year}-"
        cursor.execute(
            "SELECT order_id FROM shipping_orders WHERE order_id LIKE %s "
            "ORDER BY order_id DESC LIMIT 1", (f"{prefix}%",))
        last_row = cursor.fetchone()
        number = int(last_row[0].split("-")[-1]) + 1 if last_row else 1
        return f"{prefix}{number:03d}"

    # ------------------------------------------------------------------ read
    def search(self, term="", option="Order ID"):
        sql = """SELECT order_id, recipient_name, order_date, status,
                        COALESCE(tracking_number, ''), delivery_date
                 FROM shipping_orders"""
        params = []
        if term:
            column = self.SEARCH_COLUMNS.get(option, "order_id")
            sql += f" WHERE {column} LIKE %s"
            params.append(f"%{term}%")
        sql += " ORDER BY order_date DESC, order_id DESC"
        with self._database.cursor() as cursor:
            cursor.execute(sql, params)
            return [ShipmentRecord(*row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------ update
    def update(self, order_id, new_status, customer=None, tracking=None, role="Cashier"):
        """Save status, customer and tracking number together, following the role rules.

        Cashier: can only move forward, and a Delivered shipment is locked.
        Admin:   can do anything, including reopening a Delivered shipment.
        Pass customer/tracking as None to keep what is stored.
        """
        if new_status not in self.STATUSES:
            raise ShipmentError(f"Unknown status: {new_status}")
        admin = _is_admin(role)

        with self._database.cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT status, recipient_name, tracking_number FROM shipping_orders "
                "WHERE order_id=%s FOR UPDATE", (order_id,))
            row = cursor.fetchone()
            if row is None:
                raise ShipmentError("Shipment not found.")
            old_status, old_customer, old_tracking = row

            old_i, new_i = self.STATUSES.index(old_status), self.STATUSES.index(new_status)
            if not admin:
                if old_status == "Delivered":
                    raise ShipmentError("This shipment is already Delivered and locked. "
                                        "Only an Admin can reopen it.")
                if new_i < old_i:
                    raise ShipmentError("Cashiers can only move a shipment forward. "
                                        "Ask an Admin to move it back.")

            new_customer = old_customer if customer is None else customer.strip()
            if not new_customer:
                raise ShipmentError("Customer name is required.")
            new_tracking = old_tracking if tracking is None else (tracking.strip() or None)

            # Fixed SQL fragments (not user input). Decided here in Python because MySQL applies
            # SET assignments left to right, so `status` would already be the new value.
            stamp = "NOW()" if new_status != old_status else "status_changed_at"
            auto = 0 if new_i < old_i else None          # a reopened shipment stops being automatic
            delivery = "COALESCE(delivery_date, CURDATE())" if new_status == "Delivered" else "NULL"
            sql = (f"UPDATE shipping_orders SET recipient_name=%s, tracking_number=%s, status=%s, "
                   f"delivery_date={delivery}, status_changed_at={stamp}")
            params = [new_customer, new_tracking, new_status]
            if auto is not None:
                sql += ", auto_advance=%s"
                params.append(auto)
            sql += " WHERE order_id=%s"
            params.append(order_id)
            cursor.execute(sql, params)

    def update_status(self, order_id, new_status, role="Cashier"):
        """Status only (kept so older calls still work)."""
        self.update(order_id, new_status, role=role)

    # ------------------------------------------------------------------ delete
    def delete(self, order_id, role):
        """Admin only. Ask for confirmation in the screen before calling this."""
        if not _is_admin(role):
            raise ShipmentError("Only an Admin can delete shipments.")
        with self._database.cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM shipping_orders WHERE order_id=%s", (order_id,))
            return cursor.rowcount > 0

    # ------------------------------------------------------------------ automatic status
    def advance_statuses(self):
        """Move shipments on by themselves. Returns how many changed (0 = nothing to redraw).

        Pending -> Being Processed after AUTO_PROCESS_AFTER seconds,
        Being Processed -> Delivered after AUTO_DELIVER_AFTER seconds.
        Delivered is done first so a shipment never jumps two steps in one run.
        """
        changed = 0
        with self._database.cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE shipping_orders
                SET status='Delivered', delivery_date=COALESCE(delivery_date, CURDATE()),
                    status_changed_at=NOW()
                WHERE status='Being Processed' AND auto_advance=1
                  AND status_changed_at <= NOW() - INTERVAL %s SECOND
            """, (int(self.AUTO_DELIVER_AFTER),))
            changed += cursor.rowcount
            cursor.execute("""
                UPDATE shipping_orders
                SET status='Being Processed', status_changed_at=NOW()
                WHERE status='Pending' AND auto_advance=1
                  AND status_changed_at <= NOW() - INTERVAL %s SECOND
            """, (int(self.AUTO_PROCESS_AFTER),))
            changed += cursor.rowcount
        return changed