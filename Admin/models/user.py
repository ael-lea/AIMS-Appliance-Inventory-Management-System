"""
User Hierarchy Domain Models.
Demonstrates:
- Inheritance (BaseModel -> User -> AdminUser and CashierUser)
- Polymorphism (Overriding has_permission() and get_dashboard_title())
- Encapsulation (User credentials and role access control)
"""
from typing import Any, Dict, List, Optional, Tuple
from .base import BaseModel
from ..core.exceptions import ValidationError


class User(BaseModel):
    """
    Base User class representing an authenticated actor in the system.
    Demonstrates Inheritance from BaseModel.
    """

    def __init__(
        self,
        user_id: Optional[int] = None,
        username: str = "",
        email: str = "",
        role: str = "Employee"
    ):
        super().__init__(entity_id=user_id)
        self._username = username.strip()
        self._email = email.strip()
        self._role = role.strip()

    @property
    def user_id(self) -> Optional[int]:
        return self._id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        self._username = value.strip()

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> str:
        return self._role

    def has_permission(self, permission: str) -> bool:
        """Polymorphic permission check; base user has standard read access."""
        return permission in ("view_dashboard", "view_products")

    def get_dashboard_title(self) -> str:
        """Polymorphic dashboard title generator."""
        return f"{self._role} Dashboard - {self._username}"

    def validate(self) -> None:
        if not self._username:
            raise ValidationError("Username is required.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self._id,
            "username": self._username,
            "email": self._email,
            "role": self._role
        }

    def to_treeview_tuple(self) -> Tuple[Any, ...]:
        return (self._id, self._username, self._email, self._role)

    @classmethod
    def from_row(cls, row: Tuple[Any, ...]) -> "User":
        return cls(user_id=row[0], username=row[1], email=row[2], role=row[3] if len(row) > 3 else "Employee")


class AdminUser(User):
    """
    Administrator User subclass with full system management privileges.
    Demonstrates Inheritance and Polymorphism.
    """

    def __init__(self, user_id: Optional[int] = None, username: str = "", email: str = ""):
        super().__init__(user_id=user_id, username=username, email=email, role="Admin")

    def has_permission(self, permission: str) -> bool:
        """Admins have unrestricted permissions."""
        return True

    def get_dashboard_title(self) -> str:
        return f"Admin Dashboard - {self._username}"


class CashierUser(User):
    """
    Cashier User subclass with sales and recipient privileges.
    Demonstrates Inheritance and Polymorphism.
    """

    def __init__(self, user_id: Optional[int] = None, username: str = "", email: str = ""):
        super().__init__(user_id=user_id, username=username, email=email, role="Cashier")

    def has_permission(self, permission: str) -> bool:
        """Cashiers can manage sales, recipients, and view products, but cannot manage employees."""
        allowed = ("view_dashboard", "view_products", "record_sales", "view_recipients", "create_recipient")
        return permission in allowed

    def get_dashboard_title(self) -> str:
        return f"Cashier Dashboard - {self._username}"
