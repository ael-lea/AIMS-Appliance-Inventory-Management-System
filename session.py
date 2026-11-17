"""
Session Management Module.
Demonstrates:
- Object-Oriented Programming (UserSession class, Encapsulation)
- Constructors (__init__)
- Encapsulation (Private attributes with @property getters & setters)
- Seamless backward compatibility with legacy dict access
"""
from typing import Any, Dict, Optional


class UserSession:
    """
    Encapsulates the authenticated user session state.
    Provides encapsulated properties while supporting dictionary-style access.
    """

    def __init__(self, user_id: Optional[int] = None, name: Optional[str] = None, role: Optional[str] = None, email: Optional[str] = None):
        self._id = user_id
        self._name = name
        self._role = role
        self._email = email

    # ---------------- ENCAPSULATION: GETTERS AND SETTERS ----------------

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def name(self) -> Optional[str]:
        return self._name

    @name.setter
    def name(self, value: Optional[str]) -> None:
        self._name = str(value).strip() if value else None

    @property
    def role(self) -> Optional[str]:
        return self._role

    @role.setter
    def role(self, value: Optional[str]) -> None:
        self._role = str(value).strip() if value else None

    @property
    def email(self) -> Optional[str]:
        return self._email

    @email.setter
    def email(self, value: Optional[str]) -> None:
        self._email = str(value).strip() if value else None

    # ---------------- SESSION LIFECYCLE ----------------

    def set_user(self, user_id: int, name: str, role: str, email: str = "") -> None:
        """Sets the active authenticated user."""
        self._id = user_id
        self._name = name
        self._role = role
        self._email = email

    def clear(self) -> None:
        """Clears all session variables upon logout."""
        self._id = None
        self._name = None
        self._role = None
        self._email = None

    def is_authenticated(self) -> bool:
        """Returns True if a user is currently logged in."""
        return self._id is not None

    def is_admin(self) -> bool:
        """Returns True if the active user holds Admin role."""
        return str(self._role).strip().lower() in ("admin", "administrator")

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self._id, "name": self._name, "role": self._role, "email": self._email}

    # ---------------- DICT COMPATIBILITY OPERATORS ----------------

    def __getitem__(self, key: str) -> Any:
        return getattr(self, f"_{key}", None)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, f"_{key}", value)

    def get(self, key: str, default: Any = None) -> Any:
        val = getattr(self, f"_{key}", None)
        return val if val is not None else default

    def items(self):
        return self.to_dict().items()

    def update(self, other: Dict[str, Any]) -> None:
        for k, v in other.items():
            self[k] = v

    def __repr__(self) -> str:
        return f"<UserSession id={self._id} name={self._name} role={self._role}>"


# Global active session instance
current_user = UserSession()
