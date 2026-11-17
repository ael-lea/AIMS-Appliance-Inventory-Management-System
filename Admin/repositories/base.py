"""
Base Repository Module.
Demonstrates:
- Abstraction (Inherits from IRepository)
- Inheritance (Base for concrete entity repositories)
- Polymorphism (Overridable database execution)
- Method Overloading (Using @overload typing decorators and dynamic runtime dispatch)
- Exception Handling (Wrapping pymysql errors into DatabaseOperationException)
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union, overload
import pymysql
from ..core.interfaces import IRepository
from ..core.database import DatabaseManager
from ..core.exceptions import DatabaseOperationException, RecordNotFoundException


class BaseRepository(IRepository, ABC):
    """
    Abstract Base Repository providing unified database execution and Method Overloading.
    """

    def __init__(self, table_name: str, id_column: str = "id"):
        self._table_name = table_name
        self._id_column = id_column

    @property
    def table_name(self) -> str:
        return self._table_name

    @property
    def id_column(self) -> str:
        return self._id_column

    # ---------------- DATABASE EXECUTION HELPERS ----------------

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch: str = "none") -> Any:
        """
        Encapsulated database query execution.
        Safely handles cursor and connection closing, commit/rollback, and error wrapping.
        """
        cursor, connection = None, None
        try:
            cursor, connection = DatabaseManager.get_cursor_and_connection()
            cursor.execute(query, params or ())

            if fetch == "all":
                result = cursor.fetchall()
            elif fetch == "one":
                result = cursor.fetchone()
            elif fetch == "lastrowid":
                result = cursor.lastrowid
            elif fetch == "rowcount":
                result = cursor.rowcount
            else:
                result = None

            connection.commit()
            return result
        except pymysql.MySQLError as err:
            if connection:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise DatabaseOperationException(f"Database error executing query on '{self._table_name}': {err}")
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if connection:
                try:
                    connection.close()
                except Exception:
                    pass

    # ---------------- METHOD OVERLOADING DEMONSTRATION ----------------

    @overload
    def find(self, criteria: int) -> Optional[Any]:
        """Overload 1: Find record by integer primary key ID."""
        ...

    @overload
    def find(self, criteria: str) -> List[Any]:
        """Overload 2: Find records by string search term (name/text)."""
        ...

    @overload
    def find(self, criteria: Dict[str, Any]) -> List[Any]:
        """Overload 3: Find records by dictionary of column-value filter pairs."""
        ...

    def find(self, criteria: Union[int, str, Dict[str, Any]]) -> Union[Optional[Any], List[Any]]:
        """
        Method Overloading implementation in Python:
        Dispatches behavior dynamically based on argument type.
        - If integer: searches by primary key ID and returns single record or None.
        - If string: performs LIKE search across default text columns.
        - If dictionary: performs structured AND filtering across specified columns.
        """
        if isinstance(criteria, int):
            return self.get_by_id(criteria)
        elif isinstance(criteria, str):
            return self.search("name", criteria)
        elif isinstance(criteria, dict):
            where_clauses = [f"{col} = %s" for col in criteria.keys()]
            query = f"SELECT * FROM `{self._table_name}` WHERE " + " AND ".join(where_clauses)
            rows = self.execute_query(query, tuple(criteria.values()), fetch="all")
            return [self._map_row(r) for r in rows] if rows else []
        else:
            raise TypeError(f"Unsupported criteria type for find(): {type(criteria)}")

    @abstractmethod
    def _map_row(self, row: Tuple[Any, ...]) -> Any:
        """Map raw tuple row to entity model."""
        pass
