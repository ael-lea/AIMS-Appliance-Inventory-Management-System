"""Reads and writes the recipient directory (recipient_data, shared with the Admin module).

The delivery address lives in the `address` column, exactly like on the Admin "Recipient
Details" page. `description` is a free note that only the Admin page edits.
"""
import re
from collections import namedtuple

from cashier.database.base_repository import BaseRepository
from shipping_schema import ensure_recipient_schema

Recipient = namedtuple("Recipient", "recipient_id name contact address")

CONTACT_LENGTH = 10                                  # same rule as the Admin page:
CONTACT_PATTERN = re.compile(r"9\d{9}")              # 10 digits, starting with 9
CONTACT_MESSAGE = "Contact must be exactly 10 digits and start with 9 (e.g. 9123456789)."
_NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z .,'&-]*")


class RecipientError(Exception):
    """An input rule was broken. The message is safe to show the user."""


class RecipientRepository(BaseRepository):

    def ensure_schema(self):
        """Same definition the Admin page uses, so either side can create the table first."""
        with self._database.cursor(commit=True) as cursor:
            ensure_recipient_schema(cursor)

    @staticmethod
    def _to_recipient(row):
        return Recipient(row[0], row[1] or "", row[2] or "", row[3] or "")

    def all(self):
        """Everyone in the directory, sorted by name."""
        with self._database.cursor() as cursor:
            cursor.execute("SELECT invoice, name, contact, address "
                           "FROM recipient_data ORDER BY name, invoice")
            return [self._to_recipient(row) for row in cursor.fetchall()]

    def get(self, recipient_id):
        """One recipient, or None when it no longer exists."""
        with self._database.cursor() as cursor:
            cursor.execute("SELECT invoice, name, contact, address "
                           "FROM recipient_data WHERE invoice=%s", (recipient_id,))
            row = cursor.fetchone()
        return self._to_recipient(row) if row else None

    def add(self, name, contact, address):
        """Validate (same rules as the Admin page), save, and return the new Recipient."""
        name, contact, address = (name or "").strip(), (contact or "").strip(), (address or "").strip()
        if not name or not contact or not address:
            raise RecipientError("All fields are required.")
        if not _NAME_PATTERN.fullmatch(name):
            raise RecipientError("Recipient name must contain letters only (no numbers).")
        if len(name) > 100:
            raise RecipientError("Recipient name must be at most 100 characters.")
        if not CONTACT_PATTERN.fullmatch(contact):
            raise RecipientError(CONTACT_MESSAGE)

        with self._database.cursor(commit=True) as cursor:
            # Same rule as the Admin page: one recipient per name + contact.
            cursor.execute("SELECT invoice FROM recipient_data WHERE name=%s AND contact=%s",
                           (name, contact))
            existing = cursor.fetchone()
            if existing:
                raise RecipientError(
                    f"This recipient already exists (Recipient ID {existing[0]}). "
                    "Pick them from the list instead.")
            cursor.execute("INSERT INTO recipient_data (name, contact, address, description) "
                           "VALUES (%s, %s, %s, '')", (name, contact, address))
            new_id = cursor.lastrowid
        return Recipient(new_id, name, contact, address)
