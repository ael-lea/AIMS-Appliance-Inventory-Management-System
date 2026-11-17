"""
Core Interfaces and Abstract Base Classes (ABCs) for AIMS.
Fulfills Project Requirement: Abstraction, Interfaces or Abstract Classes (if applicable).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union


class IModel(ABC):
    """
    Abstract Interface for domain entity models.
    Enforces serialization and deserialization contracts across all models.
    """

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model instance into a dictionary representation."""
        pass

    @classmethod
    @abstractmethod
    def from_row(cls, row: Tuple[Any, ...]) -> "IModel":
        """Instantiate a model instance from a database row tuple."""
        pass

    @abstractmethod
    def validate(self) -> None:
        """Validate the model attributes; raises ValidationError if invalid."""
        pass


class IRepository(ABC):
    """
    Abstract Interface for data persistence repositories.
    Provides standard CRUD operations decoupled from concrete database drivers.
    """

    @abstractmethod
    def add(self, entity: Any) -> Any:
        """Insert a new entity record into storage."""
        pass

    @abstractmethod
    def update(self, entity: Any) -> bool:
        """Update an existing entity record in storage."""
        pass

    @abstractmethod
    def delete(self, entity_id: Any) -> bool:
        """Delete an entity record by its identifier."""
        pass

    @abstractmethod
    def get_by_id(self, entity_id: Any) -> Optional[Any]:
        """Retrieve a single entity record by its identifier."""
        pass

    @abstractmethod
    def get_all(self) -> List[Any]:
        """Retrieve all entity records."""
        pass

    @abstractmethod
    def search(self, column: str, query: str) -> List[Any]:
        """Search records matching the query in a specific column."""
        pass


class IDataStorage(ABC):
    """
    Abstract Interface for saving and loading data to/from external files (CSV, JSON, SQL).
    Fulfills Project Requirement: Save Data, Load Data, File Error Handling.
    """

    @abstractmethod
    def save(self, data: List[Dict[str, Any]], file_path: str) -> int:
        """Save formatted data to a file path. Returns number of records saved."""
        pass

    @abstractmethod
    def load(self, file_path: str) -> List[Dict[str, Any]]:
        """Load and parse records from a file path."""
        pass


class IView(ABC):
    """
    Abstract Interface for UI views/forms.
    Enforces standard lifecycle methods across Tkinter/CustomTkinter views.
    """

    @abstractmethod
    def build_ui(self) -> None:
        """Build and place all UI widgets in the view."""
        pass

    @abstractmethod
    def refresh_data(self) -> None:
        """Fetch updated data from repositories and refresh view displays."""
        pass

    @abstractmethod
    def clear_fields(self) -> None:
        """Reset all input fields and selections to default states."""
        pass
