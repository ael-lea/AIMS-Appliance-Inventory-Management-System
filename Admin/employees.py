"""
Employee Management Module.
Exposes OOP EmployeeView and backward-compatible helper functions.
"""
from typing import Any, Tuple
from .views.employees_view import EmployeeView
from .repositories.employee_repo import EmployeeRepository
from .models.employee import Employee
from .core.database import DatabaseManager


def employee_form(window) -> EmployeeView:
    """Backward-compatible entry point returning the EmployeeView instance."""
    return EmployeeView(window)


def connect_database() -> Tuple[Any, Any]:
    """Backward-compatible database connection accessor."""
    try:
        return DatabaseManager.get_cursor_and_connection()
    except Exception:
        return None, None


__all__ = [
    "EmployeeView",
    "EmployeeRepository",
    "Employee",
    "employee_form",
    "connect_database"
]
