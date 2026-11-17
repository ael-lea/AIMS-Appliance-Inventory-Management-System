"""
Session Management Module.
Reads and writes the single shared session in the project root (session.current_user),
the same one login.py fills in and the Cashier app reads.
"""
from typing import Dict, Any, Optional

import session as _shared      # project-root session.py


class SessionManager:
    """Thin wrapper over the shared session, keeping the Admin-side method names."""

    @classmethod
    def set_user(cls, user_id: int, name: str, role: str, email: str = "") -> None:
        _shared.current_user.update({"id": user_id, "name": name, "role": role, "email": email})

    @classmethod
    def get_user(cls) -> Dict[str, Any]:
        return _shared.current_user

    @classmethod
    def clear(cls) -> None:
        _shared.current_user.clear()

    @classmethod
    def is_logged_in(cls) -> bool:
        return bool(_shared.current_user.get("id"))

    @classmethod
    def is_admin(cls) -> bool:
        role = _shared.current_user.get("role", "")
        return str(role).strip().lower() in ("admin", "administrator")

    @classmethod
    def get_username(cls) -> str:
        return _shared.current_user.get("name") or "Admin"

    @classmethod
    def get_user_id(cls) -> Optional[int]:
        return _shared.current_user.get("id")


current_user = _shared.current_user