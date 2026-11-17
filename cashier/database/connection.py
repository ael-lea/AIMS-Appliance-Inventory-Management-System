"""Database access: one place that opens connections and handles errors."""
from contextlib import contextmanager

import pymysql

from auth import get_connection   # same credentials as the login module


class DatabaseError(Exception):
    """Raised for any database problem; the UI shows it in a message box."""


class DatabaseManager:
    """Opens connections and gives out cursors that commit/rollback safely."""

    def connect(self):
        try:
            return get_connection()
        except pymysql.MySQLError as error:
            raise DatabaseError(f"Unable to connect to the database.\n\n{error}") from error

    @contextmanager
    def cursor(self, commit=False):
        """Yield a cursor. Commits on success when commit=True, otherwise rolls back."""
        connection = self.connect()
        cursor = connection.cursor()
        try:
            yield cursor
            if commit:
                connection.commit()
        except pymysql.MySQLError as error:
            connection.rollback()
            raise DatabaseError(str(error)) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
