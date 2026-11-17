"""
Sales Repository Module.
Demonstrates:
- Inheritance (Inherits from BaseRepository)
- Polymorphism (Overriding add, update, delete, get_by_id, get_all, search)
- Transactional Inventory Updates & Analytics Data Generation
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from .base import BaseRepository
from ..models.sale import Sale
from ..core.exceptions import (
    ValidationError,
    RecordNotFoundException
)


class SalesRepository(BaseRepository):
    """
    Repository handling sales transactions, stock deduction, and analytics queries.
    """

    DATE_FILTERS = {
        "Today": "DATE(sale_date) = CURDATE()",
        "Last 7 Days": "sale_date >= NOW() - INTERVAL 7 DAY",
        "Last 30 Days": "sale_date >= NOW() - INTERVAL 30 DAY",
        "This Year": "YEAR(sale_date) = YEAR(CURDATE())",
        "All Time": "1 = 1",
    }

    def __init__(self):
        super().__init__(table_name="sales", id_column="sale_id")

    def _map_row(self, row: Tuple[Any, ...]) -> Sale:
        return Sale.from_row(row)

    def add(self, sale: Sale) -> int:
        """
        Records a sale and atomically deducts the sold quantity from product inventory.
        """
        sale.validate()

        # If product_id is specified, verify stock and deduct
        if sale.product_id:
            stock_row = self.execute_query(
                "SELECT quantity FROM products WHERE product_id = %s",
                (sale.product_id,),
                fetch="one"
            )
            if not stock_row:
                raise ValidationError("Referenced product does not exist.")
            current_stock = stock_row[0]
            if current_stock < sale.quantity:
                raise ValidationError(f"Insufficient stock! Available: {current_stock}, Requested: {sale.quantity}")

            # Deduct stock
            self.execute_query(
                "UPDATE products SET quantity = quantity - %s WHERE product_id = %s",
                (sale.quantity, sale.product_id)
            )

        query = """
            INSERT INTO sales (product_id, product_name, category, quantity, unit_price, total, sale_date)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        params = (
            sale.product_id,
            sale.product_name,
            sale.category or None,
            sale.quantity,
            sale.unit_price,
            sale.total
        )
        new_id = self.execute_query(query, params, fetch="lastrowid")
        sale.sale_id = new_id
        return new_id

    def update(self, sale: Sale) -> bool:
        if not sale.sale_id:
            raise ValidationError("Sale ID is required to update.")
        query = """
            UPDATE sales
            SET product_name = %s, category = %s, quantity = %s, unit_price = %s, total = %s
            WHERE sale_id = %s
        """
        params = (sale.product_name, sale.category, sale.quantity, sale.unit_price, sale.total, sale.sale_id)
        self.execute_query(query, params)
        return True

    def delete(self, sale_id: int) -> bool:
        if not sale_id:
            raise RecordNotFoundException("Please select a sale to delete.")
        self.execute_query("DELETE FROM sales WHERE sale_id = %s", (sale_id,))
        return True

    def get_by_id(self, sale_id: int) -> Optional[Sale]:
        row = self.execute_query(
            "SELECT sale_id, product_id, product_name, category, quantity, unit_price, total, sale_date FROM sales WHERE sale_id = %s",
            (sale_id,),
            fetch="one"
        )
        return self._map_row(row) if row else None

    def get_all(self) -> List[Sale]:
        rows = self.execute_query(
            "SELECT sale_id, product_id, product_name, category, quantity, unit_price, total, sale_date FROM sales ORDER BY sale_date DESC",
            fetch="all"
        )
        return [self._map_row(r) for r in rows] if rows else []

    def search(self, column: str, query: str) -> List[Sale]:
        rows = self.execute_query(
            "SELECT sale_id, product_id, product_name, category, quantity, unit_price, total, sale_date FROM sales WHERE product_name LIKE %s ORDER BY sale_date DESC",
            (f"%{query}%",),
            fetch="all"
        )
        return [self._map_row(r) for r in rows] if rows else []

    def get_filtered_sales(self, period_filter: str) -> List[Sale]:
        condition = self.DATE_FILTERS.get(period_filter, "1=1")
        query = f"SELECT sale_id, product_id, product_name, category, quantity, unit_price, total, sale_date FROM sales WHERE {condition} ORDER BY sale_date DESC"
        rows = self.execute_query(query, fetch="all")
        return [self._map_row(r) for r in rows] if rows else []

    def get_summary_metrics(self, period_filter: str) -> Dict[str, Any]:
        """Returns {revenue, orders, items_sold, avg_order_value}."""
        condition = self.DATE_FILTERS.get(period_filter, "1=1")
        query = f"""
            SELECT
                COALESCE(SUM(total), 0),
                COUNT(*),
                COALESCE(SUM(quantity), 0),
                COALESCE(AVG(total), 0)
            FROM sales
            WHERE {condition}
        """
        row = self.execute_query(query, fetch="one")
        if row:
            return {
                "revenue": float(row[0]),
                "orders": int(row[1]),
                "items_sold": int(row[2]),
                "avg_order": float(row[3])
            }
        return {"revenue": 0.0, "orders": 0, "items_sold": 0, "avg_order": 0.0}

    def get_trend_chart_data(self, period_filter: str) -> List[Tuple]:
        condition = self.DATE_FILTERS.get(period_filter, "1=1")
        query = f"""
            SELECT DATE(sale_date), SUM(total)
            FROM sales
            WHERE {condition}
            GROUP BY DATE(sale_date)
            ORDER BY DATE(sale_date)
        """
        return self.execute_query(query, fetch="all") or []

    def get_top_products_data(self, period_filter: str, limit: int = 5) -> List[Tuple]:
        condition = self.DATE_FILTERS.get(period_filter, "1=1")
        query = f"""
            SELECT product_name, SUM(quantity)
            FROM sales
            WHERE {condition}
            GROUP BY product_name
            ORDER BY SUM(quantity) DESC
            LIMIT {limit}
        """
        return self.execute_query(query, fetch="all") or []

    def get_category_chart_data(self, period_filter: str) -> List[Tuple]:
        condition = self.DATE_FILTERS.get(period_filter, "1=1")
        query = f"""
            SELECT COALESCE(NULLIF(category, ''), 'Uncategorized'), SUM(total)
            FROM sales
            WHERE {condition}
            GROUP BY 1
            ORDER BY SUM(total) DESC
        """
        return self.execute_query(query, fetch="all") or []

    def get_report_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Everything the printable sales report needs for an inclusive date range."""
        cond = "DATE(sale_date) BETWEEN %s AND %s"
        params = (start_date, end_date)

        row = self.execute_query(
            f"SELECT COALESCE(SUM(total), 0), COUNT(*), COALESCE(SUM(quantity), 0) "
            f"FROM sales WHERE {cond}", params, fetch="one")
        revenue, orders, items = (float(row[0]), int(row[1]), int(row[2])) if row else (0.0, 0, 0)

        daily = self.execute_query(
            f"SELECT DATE(sale_date), COUNT(*), SUM(quantity), SUM(total) "
            f"FROM sales WHERE {cond} GROUP BY DATE(sale_date) ORDER BY 1",
            params, fetch="all") or []

        top = self.execute_query(
            f"SELECT product_name, SUM(quantity) AS qty, SUM(total) "
            f"FROM sales WHERE {cond} GROUP BY product_name ORDER BY qty DESC LIMIT 5",
            params, fetch="all") or []

        details = self.execute_query(
            f"SELECT sale_id, sale_date, product_name, category, quantity, unit_price, total "
            f"FROM sales WHERE {cond} ORDER BY sale_date", params, fetch="all") or []

        return {
            "revenue": revenue,
            "orders": orders,
            "items_sold": items,
            "avg_order": revenue / orders if orders else 0.0,
            "daily": daily,
            "top": top,
            "details": details,
        }

    def count_all(self) -> int:
        row = self.execute_query("SELECT COUNT(*) FROM sales", fetch="one")
        return row[0] if row else 0