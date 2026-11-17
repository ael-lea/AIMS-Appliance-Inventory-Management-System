"""Payment methods.

PaymentMethod is an abstract class (an interface). CashPayment and
CardPayment implement it differently, so the order screen can treat both the
same way -- that is polymorphism.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from cashier.utils import peso


@dataclass(frozen=True)
class PaymentResult:
    """Outcome of checking a payment against an order total."""
    paid: Optional[float]
    change: float = 0.0
    error: Optional[str] = None
    short_by: float = 0.0

    @property
    def is_valid(self):
        return self.error is None


class PaymentMethod(ABC):
    """Contract every payment method must follow."""

    name = ""

    @property
    @abstractmethod
    def requires_tender(self):
        """True when the cashier must type an 'Amount Received'."""

    @abstractmethod
    def default_tender(self, total):
        """Text to pre-fill in the Amount Received box."""

    @abstractmethod
    def evaluate(self, total, tender_text):
        """Validate the payment and return a PaymentResult."""


class CashPayment(PaymentMethod):
    name = "Cash"

    @property
    def requires_tender(self):
        return True

    def default_tender(self, total):
        return ""

    def evaluate(self, total, tender_text):
        try:
            paid = float((tender_text or "").strip())
            if paid < 0:
                raise ValueError
        except ValueError:
            return PaymentResult(None, error="Enter a valid amount received.")
        if paid < total:
            short = total - paid
            return PaymentResult(paid, error=f"Payment is short by {peso(short)}.",
                                short_by=short)
        return PaymentResult(paid, change=round(paid - total, 2))


class CardPayment(PaymentMethod):
    name = "Card"

    @property
    def requires_tender(self):
        return False

    def default_tender(self, total):
        return f"{total:.2f}"

    def evaluate(self, total, tender_text):
        return PaymentResult(total)           # card always pays the exact total


class PaymentFactory:
    """Creates a payment method from its display name."""

    _REGISTRY = {"Cash": CashPayment, "Card": CardPayment}
    NAMES = tuple(_REGISTRY)

    @classmethod
    def create(cls, name):
        return cls._REGISTRY[name]()
