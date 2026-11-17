"""
Product Repository Module.
Demonstrates:
- Inheritance (Inherits from BaseRepository)
- Polymorphism (Overriding add, update, delete, get_by_id, get_all, search)
- Encapsulated Query Logic
- Custom Exception Handling (DuplicateRecordException, ValidationError, RecordNotFoundException)
"""
from typing import Any, List, Optional, Tuple
from .base import BaseRepository
from ..models.product import Product
from ..core.exceptions import (
    DuplicateRecordException,
    ValidationError,
    RecordNotFoundException
)


class ProductRepository(BaseRepository):
    """
    Repository handling database CRUD operations for the products table.
    """

    def __init__(self):
        super().__init__(table_name="products", id_column="product_id")

    def _map_row(self, row: Tuple[Any, ...]) -> Product:
        return Product.from_row(row)

    def add(self, product: Product) -> int:
        """
        Inserts a new product record.
        Verifies case-insensitive uniqueness of the product name.
        """
        product.validate()

        duplicate = self.execute_query(
            "SELECT product_id FROM products WHERE LOWER(name) = LOWER(%s)",
            (product.name,),
            fetch="one"
        )
        if duplicate:
            raise DuplicateRecordException("A product with this name already exists.")

        query = """
            INSERT INTO products (name, category, price, quantity, image_path)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            product.name,
            product.category or None,
            product.price,
            product.quantity,
            product.image_path or None
        )
        new_id = self.execute_query(query, params, fetch="lastrowid")
        product.product_id = new_id
        return new_id

    def update(self, product: Product) -> bool:
        """
        Updates an existing product record.
        Ensures product name is not taken by another item.
        """
        if not product.product_id:
            raise ValidationError("Product ID is required for update.")

        product.validate()

        duplicate = self.execute_query(
            "SELECT product_id FROM products WHERE LOWER(name) = LOWER(%s) AND product_id != %s",
            (product.name, product.product_id),
            fetch="one"
        )
        if duplicate:
            raise DuplicateRecordException("Another product with this name already exists.")

        query = """
            UPDATE products
            SET name = %s, category = %s, price = %s, quantity = %s, image_path = %s
            WHERE product_id = %s
        """
        params = (
            product.name,
            product.category or None,
            product.price,
            product.quantity,
            product.image_path or None,
            product.product_id
        )
        self.execute_query(query, params)
        return True

    def delete(self, product_id: int) -> bool:
        """Deletes a product by product_id."""
        if not product_id:
            raise RecordNotFoundException("Please select a product to delete.")

        self.execute_query("DELETE FROM products WHERE product_id = %s", (product_id,))
        return True

    def get_by_id(self, product_id: int) -> Optional[Product]:
        row = self.execute_query(
            "SELECT product_id, name, category, price, quantity, image_path FROM products WHERE product_id = %s",
            (product_id,),
            fetch="one"
        )
        return self._map_row(row) if row else None

    def get_all(self) -> List[Product]:
        rows = self.execute_query(
            "SELECT product_id, name, category, price, quantity, image_path FROM products ORDER BY product_id",
            fetch="all"
        )
        return [self._map_row(r) for r in rows] if rows else []

    def search(self, column: str, query: str) -> List[Product]:
        search_columns = {
            "Product ID": "product_id",
            "product_id": "product_id",
            "Name": "name",
            "name": "name",
            "Category": "category",
            "category": "category"
        }
        col = search_columns.get(column, "name")

        if col == "product_id":
            if not str(query).strip().isdigit():
                return []
            rows = self.execute_query(
                "SELECT product_id, name, category, price, quantity, image_path FROM products WHERE product_id = %s",
                (int(query),),
                fetch="all"
            )
        else:
            rows = self.execute_query(
                f"SELECT product_id, name, category, price, quantity, image_path FROM products WHERE {col} LIKE %s ORDER BY product_id",
                (f"%{query}%",),
                fetch="all"
            )
        return [self._map_row(r) for r in rows] if rows else []

    def count_all(self) -> int:
        row = self.execute_query("SELECT COUNT(*) FROM products", fetch="one")
        return row[0] if row else 0

    def get_in_stock(self) -> List[Product]:
        rows = self.execute_query(
            "SELECT product_id, name, category, price, quantity, image_path FROM products WHERE quantity > 0 ORDER BY name",
            fetch="all"
        )
        return [self._map_row(r) for r in rows] if rows else []

    def update_stock(self, product_id: int, quantity_delta: int) -> bool:
        """Adjusts product quantity by a delta (positive to add, negative to deduct)."""
        self.execute_query(
            "UPDATE products SET quantity = quantity + %s WHERE product_id = %s",
            (quantity_delta, product_id)
        )
        return True
