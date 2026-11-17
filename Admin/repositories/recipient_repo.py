"""
Recipient Repository Module.
Demonstrates:
- Inheritance (Inherits from BaseRepository)
- Polymorphism (Overriding add, update, delete, get_by_id, get_all, search)
- Encapsulated Business Rules (Shipment Protection on Delete)
- Custom Exception Handling (DuplicateRecordException, ValidationError, RecordNotFoundException)
"""
from typing import Any, List, Optional, Tuple
from .base import BaseRepository
from ..models.recipient import Recipient
from ..core.exceptions import (
    DuplicateRecordException,
    ValidationError,
    RecordNotFoundException
)


class RecipientRepository(BaseRepository):
    """
    Repository handling database CRUD operations for the recipient_data table.
    """

    FINISHED_STATUSES = ("Delivered", "Cancelled")

    def __init__(self):
        super().__init__(table_name="recipient_data", id_column="invoice")

    def _map_row(self, row: Tuple[Any, ...]) -> Recipient:
        return Recipient.from_row(row)

    def add(self, recipient: Recipient) -> int:
        """
        Inserts a new recipient.
        Checks for duplicate name and contact combination.
        """
        recipient.validate()

        duplicate = self.execute_query(
            "SELECT invoice FROM recipient_data WHERE name = %s AND contact = %s",
            (recipient.name, recipient.contact),
            fetch="one"
        )
        if duplicate:
            raise DuplicateRecordException(f"This recipient already exists (Recipient ID {duplicate[0]}).")

        query = """
            INSERT INTO recipient_data (name, contact, address, description)
            VALUES (%s, %s, %s, %s)
        """
        params = (recipient.name, recipient.contact, recipient.address, recipient.description)
        new_id = self.execute_query(query, params, fetch="lastrowid")
        recipient.invoice = new_id
        return new_id

    def update(self, recipient: Recipient) -> bool:
        """Updates an existing recipient record."""
        if not recipient.invoice:
            raise ValidationError("Recipient ID is required for update.")

        recipient.validate()

        duplicate = self.execute_query(
            "SELECT invoice FROM recipient_data WHERE name = %s AND contact = %s AND invoice <> %s",
            (recipient.name, recipient.contact, recipient.invoice),
            fetch="one"
        )
        if duplicate:
            raise DuplicateRecordException(f"Another recipient already has this name and contact (ID {duplicate[0]}).")

        query = """
            UPDATE recipient_data
            SET name = %s, contact = %s, address = %s, description = %s
            WHERE invoice = %s
        """
        params = (recipient.name, recipient.contact, recipient.address, recipient.description, recipient.invoice)
        self.execute_query(query, params)
        return True

    def has_active_shipments(self, recipient_id: int) -> bool:
        """Checks if recipient still has active shipments in progress."""
        # Check if shipping_orders table exists
        exists = self.execute_query("SHOW TABLES LIKE 'shipping_orders'", fetch="one")
        if not exists:
            return False

        col_exists = self.execute_query("SHOW COLUMNS FROM shipping_orders LIKE 'recipient_id'", fetch="one")
        if not col_exists:
            return False

        placeholders = ", ".join(["%s"] * len(self.FINISHED_STATUSES))
        query = f"SELECT COUNT(*) FROM shipping_orders WHERE recipient_id = %s AND status NOT IN ({placeholders})"
        row = self.execute_query(query, (recipient_id, *self.FINISHED_STATUSES), fetch="one")
        return bool(row and row[0] > 0)

    def delete(self, recipient_id: int) -> bool:
        """
        Deletes a recipient record.
        Enforces: Cannot delete recipient with active (Pending/Processing) shipments.
        """
        if not recipient_id:
            raise RecordNotFoundException("Please select a recipient to delete.")

        if self.has_active_shipments(recipient_id):
            raise ValidationError("Cannot delete recipient: they still have shipments in progress or pending.")

        self.execute_query("DELETE FROM recipient_data WHERE invoice = %s", (recipient_id,))
        return True

    def get_by_id(self, recipient_id: int) -> Optional[Recipient]:
        row = self.execute_query(
            "SELECT invoice, name, contact, address, description FROM recipient_data WHERE invoice = %s",
            (recipient_id,),
            fetch="one"
        )
        return self._map_row(row) if row else None

    def get_all(self) -> List[Recipient]:
        rows = self.execute_query(
            "SELECT invoice, name, contact, address, description FROM recipient_data ORDER BY invoice",
            fetch="all"
        )
        return [self._map_row(r) for r in rows] if rows else []

    def search(self, column: str, query: str) -> List[Recipient]:
        valid_cols = {
            "Invoice": "invoice",
            "invoice": "invoice",
            "Name": "name",
            "name": "name",
            "Contact": "contact",
            "contact": "contact"
        }
        col = valid_cols.get(column, "name")
        rows = self.execute_query(
            f"SELECT invoice, name, contact, address, description FROM recipient_data WHERE {col} LIKE %s ORDER BY invoice",
            (f"%{query}%",),
            fetch="all"
        )
        return [self._map_row(r) for r in rows] if rows else []

    def count_all(self) -> int:
        row = self.execute_query("SELECT COUNT(*) FROM recipient_data", fetch="one")
        return row[0] if row else 0
