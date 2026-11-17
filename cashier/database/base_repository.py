"""Abstract parent of all repositories."""
from abc import ABC, abstractmethod

from cashier.database.connection import DatabaseManager


class BaseRepository(ABC):
    """Every repository owns a DatabaseManager and can prepare its tables."""

    def __init__(self, database=None):
        self._database = database or DatabaseManager()

    @abstractmethod
    def ensure_schema(self):
        """Create the table(s) this repository needs, if missing."""

    def _run_ddl(self, sql):
        with self._database.cursor(commit=True) as cursor:
            cursor.execute(sql)

    def _ensure_column(self, table, name, definition):
        """Add a column to an existing table if it is missing. True if it was added.

        `table`, `name` and `definition` are fixed strings from our own code (never user input).
        """
        with self._database.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s",
                (table, name))
            exists = cursor.fetchone()[0]
        if exists:
            return False
        self._run_ddl(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        return True