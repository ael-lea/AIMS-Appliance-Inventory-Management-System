"""
Admin Settings & Maintenance Module.
Exposes OOP AdminSettingsView and backward-compatible helper functions.
"""
from .views.admin_settings_view import AdminSettingsView


def open_admin_settings(parent) -> None:
    """Backward-compatible entry point opening Admin Settings menu."""
    AdminSettingsView(parent).open_settings_menu()


__all__ = [
    "AdminSettingsView",
    "open_admin_settings"
]
