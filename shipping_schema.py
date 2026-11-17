"""
Shipping and Recipient Database Schema Management Module.
Demonstrates:
- Object-Oriented Programming (Classes and Objects)
- Abstraction & Interfaces (ISchemaManager abstract base class)
- Inheritance & Polymorphism (ShippingSchemaManager, RecipientSchemaManager)
- Reusable Methods & Clean Separation of Concerns
"""
from abc import ABC, abstractmethod
from typing import Set, Dict, Any

# Column definitions for shipping_orders
SHIPPING_COLUMNS: Dict[str, str] = {
    "order_ref":         "VARCHAR(30) NULL",
    "recipient_id":      "INT NULL",
    "recipient_name":    "VARCHAR(100) NOT NULL DEFAULT ''",
    "order_date":        "DATE NULL",
    "status":            "ENUM('Pending', 'Being Processed', 'Delivered') NOT NULL DEFAULT 'Pending'",
    "tracking_number":   "VARCHAR(100) NULL",
    "delivery_date":     "DATE NULL",
    "address":           "TEXT NULL",
    "created_at":        "DATETIME NULL DEFAULT CURRENT_TIMESTAMP",
    "status_changed_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
    "auto_advance":      "TINYINT(1) NOT NULL DEFAULT 1",
}

CREATE_SHIPPING_SQL = """
    CREATE TABLE IF NOT EXISTS shipping_orders (
        order_id VARCHAR(30) PRIMARY KEY,
        order_ref VARCHAR(30) NULL,
        recipient_id INT NULL,
        recipient_name VARCHAR(100) NOT NULL,
        order_date DATE NOT NULL,
        status ENUM('Pending', 'Being Processed', 'Delivered') NOT NULL DEFAULT 'Pending',
        tracking_number VARCHAR(100) NULL,
        delivery_date DATE NULL,
        address TEXT NULL,
        created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
        status_changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        auto_advance TINYINT(1) NOT NULL DEFAULT 1,
        UNIQUE KEY uq_shipping_order_ref (order_ref)
    )
"""

CREATE_RECIPIENT_SQL = """
    CREATE TABLE IF NOT EXISTS recipient_data (
        invoice INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        contact VARCHAR(20),
        address TEXT,
        description TEXT
    )
"""


class ISchemaManager(ABC):
    """
    Abstract Interface for schema verification and migration.
    Demonstrates Abstraction and Interface contracts.
    """

    @abstractmethod
    def ensure_schema(self, cursor: Any) -> None:
        """Ensures the table exists and all required columns are present."""
        pass


class BaseSchemaManager(ISchemaManager, ABC):
    """
    Base class providing reusable database metadata inspection utilities.
    Demonstrates Inheritance.
    """

    @staticmethod
    def get_existing_columns(cursor: Any, table_name: str) -> Set[str]:
        """Queries information_schema to retrieve lower-case column names for a table."""
        cursor.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
            (table_name,)
        )
        return {row[0].lower() for row in cursor.fetchall()}


class ShippingSchemaManager(BaseSchemaManager):
    """
    Encapsulates shipping_orders table migration and column management.
    Demonstrates Polymorphism by implementing ensure_schema().
    """

    def ensure_schema(self, cursor: Any) -> None:
        cursor.execute(CREATE_SHIPPING_SQL)
        existing = self.get_existing_columns(cursor, "shipping_orders")

        # Migrate legacy shipping_address column to address
        if "shipping_address" in existing:
            if "address" not in existing:
                cursor.execute("ALTER TABLE shipping_orders CHANGE COLUMN shipping_address address TEXT NULL")
            else:
                cursor.execute("UPDATE shipping_orders SET address = shipping_address WHERE address IS NULL AND shipping_address IS NOT NULL")
            existing = self.get_existing_columns(cursor, "shipping_orders")

        # Add missing columns
        for column, definition in SHIPPING_COLUMNS.items():
            if column not in existing:
                cursor.execute(f"ALTER TABLE shipping_orders ADD COLUMN {column} {definition}")
                if column == "auto_advance":
                    cursor.execute("UPDATE shipping_orders SET auto_advance = 0")

        # Ensure created_at default value
        cursor.execute(
            "SELECT COLUMN_DEFAULT FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'shipping_orders' AND COLUMN_NAME = 'created_at'"
        )
        row = cursor.fetchone()
        if row is not None and row[0] is None:
            cursor.execute("ALTER TABLE shipping_orders MODIFY COLUMN created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP")

        # Ensure unique index on order_ref
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'shipping_orders' AND INDEX_NAME = 'uq_shipping_order_ref'"
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE shipping_orders ADD UNIQUE KEY uq_shipping_order_ref (order_ref)")


class RecipientSchemaManager(BaseSchemaManager):
    """
    Encapsulates recipient_data table migration.
    Demonstrates Polymorphism by implementing ensure_schema().
    """

    def ensure_schema(self, cursor: Any) -> None:
        cursor.execute(CREATE_RECIPIENT_SQL)
        existing = self.get_existing_columns(cursor, "recipient_data")
        if "address" not in existing:
            cursor.execute("ALTER TABLE recipient_data ADD COLUMN address TEXT AFTER contact")
        if "description" not in existing:
            cursor.execute("ALTER TABLE recipient_data ADD COLUMN description TEXT")


# Singleton instances
_shipping_manager = ShippingSchemaManager()
_recipient_manager = RecipientSchemaManager()


# Compatibility functional wrappers
def ensure_shipping_schema(cursor: Any) -> None:
    _shipping_manager.ensure_schema(cursor)


def ensure_recipient_schema(cursor: Any) -> None:
    _recipient_manager.ensure_schema(cursor)
