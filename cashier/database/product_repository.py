"""Reads and updates the products table (owned by the Admin module)."""
from cashier.database.base_repository import BaseRepository
from cashier.models import Product


class ProductRepository(BaseRepository):

    def ensure_schema(self):
        """The products table is created by the Admin module; nothing to do."""

    def count_available(self):
        with self._database.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM products WHERE quantity > 0")
            return cursor.fetchone()[0]

    def categories(self):
        with self._database.cursor() as cursor:
            cursor.execute("SELECT DISTINCT category FROM products "
                           "WHERE category IS NOT NULL AND category <> '' ORDER BY category")
            return [row[0] for row in cursor.fetchall()]

    def search_available(self, term="", category="All"):
        """Products in stock, optionally filtered by ID/name text and category."""
        sql = "SELECT product_id, name, category, price, quantity FROM products WHERE quantity > 0"
        params = []
        if term:
            sql += " AND (product_id = %s OR name LIKE %s)"
            params += [int(term) if term.isdigit() else -1, f"%{term}%"]
        if category != "All":
            sql += " AND category = %s"
            params.append(category)
        with self._database.cursor() as cursor:
            cursor.execute(sql + " ORDER BY name", params)
            return [Product(*row) for row in cursor.fetchall()]

    def stock_of(self, product_id):
        with self._database.cursor() as cursor:
            cursor.execute("SELECT quantity FROM products WHERE product_id=%s", (product_id,))
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def deduct_stock(self, cursor, product_id, quantity):
        """Take stock inside a running transaction. False if there is not enough."""
        cursor.execute(
            "UPDATE products SET quantity=quantity-%s WHERE product_id=%s AND quantity >= %s",
            (quantity, product_id, quantity),
        )
        return cursor.rowcount == 1
