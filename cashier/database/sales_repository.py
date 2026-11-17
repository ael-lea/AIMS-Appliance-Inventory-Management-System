"""Sales records and the reports built from completed orders."""
from cashier.database.base_repository import BaseRepository
from cashier.models import OrderSummary, SalesSummary


class SalesPeriod:
    """A named reporting period that knows its own SQL conditions.

    Each period has a current condition, an optional condition for the period
    it is compared against, and the wording used in the UI ("vs yesterday").
    """

    # label -> (current condition, previous condition or None, comparison wording)
    _DEFINITIONS = {
        "Today": (
            "DATE({col})=CURDATE()",
            "DATE({col})=CURDATE() - INTERVAL 1 DAY",
            "yesterday"),
        "Yesterday": (
            "DATE({col})=CURDATE() - INTERVAL 1 DAY",
            "DATE({col})=CURDATE() - INTERVAL 2 DAY",
            "the day before"),
        "This Week": (
            "YEARWEEK({col},1)=YEARWEEK(CURDATE(),1)",
            "YEARWEEK({col},1)=YEARWEEK(CURDATE() - INTERVAL 7 DAY,1)",
            "last week"),
        "This Month": (
            "(YEAR({col})=YEAR(CURDATE()) AND MONTH({col})=MONTH(CURDATE()))",
            "(YEAR({col})=YEAR(CURDATE() - INTERVAL 1 MONTH) "
            "AND MONTH({col})=MONTH(CURDATE() - INTERVAL 1 MONTH))",
            "last month"),
        "Last 7 Days": (
            "{col} >= NOW() - INTERVAL 7 DAY",
            "({col} >= NOW() - INTERVAL 14 DAY AND {col} < NOW() - INTERVAL 7 DAY)",
            "the previous 7 days"),
        "Last 30 Days": (
            "{col} >= NOW() - INTERVAL 30 DAY",
            "({col} >= NOW() - INTERVAL 60 DAY AND {col} < NOW() - INTERVAL 30 DAY)",
            "the previous 30 days"),
        "All Time": ("1=1", None, ""),
    }
    LABELS = tuple(_DEFINITIONS)

    def __init__(self, label="Today"):
        if label not in self._DEFINITIONS:
            raise ValueError(f"Unknown sales period: {label}")
        self._label = label

    def condition(self, column="order_date"):
        """SQL condition for the given column (fixed list, so injection-safe)."""
        return self._DEFINITIONS[self._label][0].format(col=column)

    def previous_condition(self, column="order_date"):
        """SQL condition for the comparison period, or None if there isn't one."""
        template = self._DEFINITIONS[self._label][1]
        return template.format(col=column) if template else None

    @property
    def compare_label(self):
        return self._DEFINITIONS[self._label][2]


class SalesRepository(BaseRepository):

    def ensure_schema(self):
        """Matches the sales table used by the existing Admin Sales page."""
        self._run_ddl("""
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT NULL,
                product_name VARCHAR(100) NOT NULL,
                category VARCHAR(100) NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                total DECIMAL(10,2) NOT NULL,
                sale_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def record_sales(self, cursor, cart, sale_date):
        """Insert one sales row per cart line (inside the caller's transaction)."""
        for item in cart:
            cursor.execute("""
                INSERT INTO sales
                (product_id, product_name, category, quantity, unit_price, total, sale_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (item.product_id, item.name, item.category, item.quantity,
                  item.unit_price, item.line_total, sale_date))

    # --- dashboard cards -------------------------------------------------------------
    def today_sales(self):
        with self._database.cursor() as cursor:
            cursor.execute("SELECT COALESCE(SUM(total), 0) FROM orders "
                           "WHERE status='Completed' AND DATE(order_date)=CURDATE()")
            return cursor.fetchone()[0]

    def today_completed_count(self):
        with self._database.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM orders "
                           "WHERE status='Completed' AND DATE(order_date)=CURDATE()")
            return cursor.fetchone()[0]

    # --- sales overview ------------------------------------------------------------------
    def _summarise(self, condition_for):
        """Totals for completed orders; condition_for(column) gives the date filter."""
        with self._database.cursor() as cursor:
            cursor.execute(f"""
                SELECT COALESCE(SUM(o.total),0), COUNT(*),
                       COALESCE((SELECT SUM(oi.quantity) FROM order_items oi
                                 JOIN orders ox ON ox.order_id=oi.order_id
                                 WHERE ox.status='Completed' AND {condition_for('ox.order_date')}),0)
                FROM orders o WHERE o.status='Completed' AND {condition_for('o.order_date')}
            """)
            total, count, items = cursor.fetchone()
        return SalesSummary(float(total or 0), int(count or 0), int(items or 0))

    def summary(self, period):
        return self._summarise(period.condition)

    def previous_summary(self, period):
        """Summary of the comparison period, or None (e.g. for All Time)."""
        if period.previous_condition() is None:
            return None
        return self._summarise(period.previous_condition)

    def completed_orders(self, period, limit=300):
        with self._database.cursor() as cursor:
            cursor.execute(f"""
                SELECT o.order_id, o.order_date,
                       (SELECT COALESCE(SUM(i.quantity),0) FROM order_items i WHERE i.order_id=o.order_id),
                       o.total, COALESCE(o.payment_method,'')
                FROM orders o WHERE o.status='Completed' AND {period.condition('o.order_date')}
                ORDER BY o.order_date DESC LIMIT %s
            """, (int(limit),))
            return [OrderSummary(oid, date, int(qty), total, method, "Completed")
                    for oid, date, qty, total, method in cursor.fetchall()]

    def payment_breakdown(self, period):
        """List of (method, number_of_orders, amount), biggest amount first."""
        with self._database.cursor() as cursor:
            cursor.execute(f"""
                SELECT COALESCE(payment_method,'Unknown'), COUNT(*), COALESCE(SUM(total),0)
                FROM orders WHERE status='Completed' AND {period.condition()}
                GROUP BY payment_method ORDER BY SUM(total) DESC
            """)
            return list(cursor.fetchall())

    def top_products(self, period, limit=5):
        """List of (product_name, quantity_sold, revenue), most units first.

        Reads the sales table, which gets one row per cart line.
        """
        with self._database.cursor() as cursor:
            cursor.execute(f"""
                SELECT product_name, COALESCE(SUM(quantity),0), COALESCE(SUM(total),0)
                FROM sales WHERE {period.condition('sale_date')}
                GROUP BY product_name
                ORDER BY SUM(quantity) DESC, SUM(total) DESC LIMIT %s
            """, (int(limit),))
            return [(name, int(qty), total) for name, qty, total in cursor.fetchall()]

    
    def shipment_statuses(self, period):
        """Return shipment statuses keyed by the corresponding sales order ID."""
        with self._database.cursor() as cursor:
            cursor.execute(f"""
                SELECT s.order_ref, s.status
                FROM shipping_orders s
                JOIN orders o ON o.order_id = s.order_ref
                WHERE o.status='Completed'
                AND {period.condition('o.order_date')}
            """)

            return {
                str(order_id): status
                for order_id, status in cursor.fetchall()
            }


    def sales_by_hour(self, period):
        """Dict of hour of day (0-23) -> completed sales amount."""
        with self._database.cursor() as cursor:
            cursor.execute(f"""
                SELECT HOUR(order_date), COALESCE(SUM(total),0)
                FROM orders WHERE status='Completed' AND {period.condition()}
                GROUP BY HOUR(order_date)
            """)
            return {int(hour): float(amount) for hour, amount in cursor.fetchall()}