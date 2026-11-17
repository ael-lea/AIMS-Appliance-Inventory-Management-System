"""
Recipient Management Module.
Exposes OOP RecipientView and backward-compatible helper functions.
"""
from typing import Any, List, Optional, Tuple
from .views.recipient_view import RecipientView
from .repositories.recipient_repo import RecipientRepository
from .models.recipient import Recipient


def supplier_form(window) -> RecipientView:
    """Backward-compatible entry point returning the RecipientView instance."""
    return RecipientView(window)


def recipient_form(window) -> RecipientView:
    return RecipientView(window)


def get_recipients() -> List[Tuple[Any, ...]]:
    """Returns list of (invoice, name, contact, address) for dropdown population."""
    repo = RecipientRepository()
    try:
        recipients = repo.get_all()
        return [(r.invoice, r.name, r.contact, r.address) for r in recipients]
    except Exception:
        return []


def get_recipient(recipient_id: int) -> Optional[Tuple[Any, ...]]:
    """Returns (invoice, name, contact, address) for a single recipient."""
    repo = RecipientRepository()
    try:
        r = repo.get_by_id(recipient_id)
        return (r.invoice, r.name, r.contact, r.address) if r else None
    except Exception:
        return None


def create_recipient(name: str, contact: str, address: str, description: str = "") -> Optional[int]:
    """Validates and creates a recipient, returning new ID or None."""
    repo = RecipientRepository()
    try:
        rec = Recipient(name=name, contact=contact, address=address, description=description)
        return repo.add(rec)
    except Exception:
        return None


def add_recipient_dialog(parent, on_saved=None) -> None:
    """Pop-up modal dialog for creating a recipient."""
    RecipientView.open_quick_add_dialog(parent, on_saved=on_saved)


__all__ = [
    "RecipientView",
    "RecipientRepository",
    "Recipient",
    "supplier_form",
    "recipient_form",
    "get_recipients",
    "get_recipient",
    "create_recipient",
    "add_recipient_dialog"
]
