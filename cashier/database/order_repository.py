"""Reads and writes the orders and order_items tables."""
from datetime import datetime

from cashier.database.base_repository import BaseRepository
from cashier.models import Order, OrderLine, OrderSummary


class OrderRepository(BaseRepository):

    def ensure_schema(self):
        self._run_ddl("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR(30) PRIMARY KEY,
                order_date DATETIME NOT NULL,
                subtotal DECIMAL(10,2) NOT NULL,
                vat DECIMAL(10,2) NOT NULL DEFAULT 0,
                total DECIMAL(10,2) NOT NULL,
                payment_method VARCHAR(20) NULL,
                amount_paid DECIMAL(10,2) NULL,
                change_amount DECIMAL(10,2) NULL,
                status ENUM('Pending', 'Completed') NOT NULL DEFAULT 'Pending'
            )
        """)
        self._run_ddl("""
            CREATE TABLE IF NOT EXISTS order_items (
                item_id INT AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(30) NOT NULL,
                product_id INT NULL,
                product_name VARCHAR(100) NOT NULL,
                category VARCHAR(100) NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                line_total DECIMAL(10,2) NOT NULL,
                INDEX (order_id)
            )
        """)
        # What the cashier chose in Order Entry, so a held order restores it when resumed.
        self._ensure_column("orders", "recipient_id", "INT NULL")
        self._ensure_column("orders", "ship_order", "TINYINT(1) NOT NULL DEFAULT 1")

    # --- transactional operations (receive the caller's cursor) --------------
    def next_order_id(self, cursor):
        prefix = f"OR-{datetime.now().year}-"
        cursor.execute(
            "SELECT order_id FROM orders WHERE order_id LIKE %s ORDER BY order_id DESC LIMIT 1",
            (f"{prefix}%",),
        )
        row = cursor.fetchone()
        number = int(row[0].split("-")[-1]) + 1 if row else 1
        return f"{prefix}{number:04d}"

    def save(self, cursor, order):
        """Insert (or replace) an order and all of its lines."""
        cursor.execute("DELETE FROM order_items WHERE order_id = %s", (order.order_id,))
        cursor.execute("DELETE FROM orders WHERE order_id = %s", (order.order_id,))
        cursor.execute("""
            INSERT INTO orders
            (order_id, order_date, subtotal, vat, total, payment_method,
             amount_paid, change_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (order.order_id, order.order_date, order.subtotal, order.vat, order.total,
              order.payment_method, order.amount_paid, order.change_amount, order.status))
        for line in order.lines:
            cursor.execute("""
                INSERT INTO order_items
                (order_id, product_id, product_name, category, quantity, unit_price, line_total)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (order.order_id, line.product_id, line.product_name, line.category,
                  line.quantity, line.unit_price, line.line_total))

    def set_shipping(self, cursor, order_id, recipient_id, ship_order):
        """Remember the recipient / 'Ship this order' choice on a held order.

        Call it right after save(): save() re-inserts the row, which resets both columns.
        """
        cursor.execute("UPDATE orders SET recipient_id=%s, ship_order=%s WHERE order_id=%s",
                       (recipient_id if ship_order else None, 1 if ship_order else 0, order_id))

    # --- stand-alone queries -----------------------------------------------------
    def get_shipping(self, order_id):
        """(recipient_id, ship_order) saved with a held order; (None, True) if nothing is saved."""
        with self._database.cursor() as cursor:
            cursor.execute("SELECT recipient_id, ship_order FROM orders WHERE order_id=%s",
                           (order_id,))
            row = cursor.fetchone()
        if row is None:
            return None, True
        return row[0], bool(row[1])

    def get(self, order_id):
        """Return the full Order, or None when it does not exist."""
        with self._database.cursor() as cursor:
            cursor.execute("""
                SELECT order_id, order_date, subtotal, vat, total,
                       payment_method, amount_paid, change_amount, status
                FROM orders WHERE order_id = %s
            """, (order_id,))
            header = cursor.fetchone()
            if not header:
                return None
            cursor.execute("""
                SELECT product_id, product_name, category, quantity, unit_price, line_total
                FROM order_items WHERE order_id = %s ORDER BY item_id
            """, (order_id,))
            lines = tuple(OrderLine(*row) for row in cursor.fetchall())
        return Order(*header, lines=lines)

    def search(self, term="", status="All", limit=500):
        """Order-history rows filtered by order ID/product text and status."""
        sql = """
            SELECT o.order_id, o.order_date,
                   (SELECT COALESCE(SUM(i.quantity), 0) FROM order_items i WHERE i.order_id=o.order_id),
                   o.total, COALESCE(o.payment_method, ''), o.status
            FROM orders o WHERE 1=1
        """
        params = []
        if term:
            sql += (" AND (o.order_id LIKE %s OR EXISTS (SELECT 1 FROM order_items i "
                    "WHERE i.order_id=o.order_id AND i.product_name LIKE %s))")
            params.extend([f"%{term}%", f"%{term}%"])
        if status != "All":
            sql += " AND o.status=%s"
            params.append(status)
        sql += " ORDER BY o.order_date DESC LIMIT %s"
        params.append(int(limit))
        with self._database.cursor() as cursor:
            cursor.execute(sql, params)
            return [OrderSummary(oid, date, int(count), total, method, status)
                    for oid, date, count, total, method, status in cursor.fetchall()]

    def count_pending(self):
        with self._database.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
            return cursor.fetchone()[0]