"""
Base Model Module.
Demonstrates:
- Abstraction (Inherits from IModel)
- Constructors (__init__)
- Encapsulation (Protected attributes, properties)
- Polymorphism (Abstract to_dict, from_row, to_treeview_tuple)
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Optional
from datetime import datetime
from ..core.interfaces import IModel


class BaseModel(IModel, ABC):
    """
    Abstract Base Class for all domain entities.
    Demonstrates Inheritance from IModel and provides standard encapsulation.
    """

    def __init__(self, entity_id: Optional[Any] = None):
        """
        Constructor initializing base entity state.
        Demonstrates proper use of constructors and encapsulation.
        """
        self._id = entity_id
        self._created_at = datetime.now()

    @property
    def id(self) -> Optional[Any]:
        """Getter for entity identifier."""
        return self._id

    @id.setter
    def id(self, value: Any) -> None:
        """Setter for entity identifier."""
        self._id = value

    @property
    def created_at(self) -> datetime:
        """Getter for entity creation timestamp."""
        return self._created_at

    @abstractmethod
    def to_treeview_tuple(self) -> Tuple[Any, ...]:
        """
        Polymorphic method: returns a tuple of values specifically formatted
        for display in a Tkinter ttk.Treeview table.
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self._id}>"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self._id is not None and self._id == other._id
        return False
