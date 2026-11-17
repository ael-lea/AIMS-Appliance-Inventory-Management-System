"""
Shipment Domain Model.
Demonstrates:
- Inheritance (Shipment inherits from BaseModel)
- Encapsulation (Status, Order ID, and Tracking attributes)
- Polymorphism (Overriding to_dict, from_row, to_treeview_tuple, validate)
"""
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple, Union
from .base import BaseModel
from ..core.exceptions import EmptyFieldException, ValidationError


class Shipment(BaseModel):
    """
    Represents a shipping order for product dispatch.
    Encapsulates recipient link, fulfillment status, and tracking information.
    """

    VALID_STATUSES = ("Pending", "Being Processed", "Delivered", "Cancelled")

    def __init__(
        self,
        order_id: str = "",
        recipient_id: Optional[int] = None,
        recipient_name: str = "",
        address: str = "",
        order_date: Optional[Union[date, str]] = None,
        status: str = "Pending",
        tracking_number: str = "",
        delivery_date: Optional[Union[date, str]] = None,
        created_at: Optional[datetime] = None
    ):
        super().__init__(entity_id=order_id)
        self._order_id = order_id
        self._recipient_id = recipient_id
        self._recipient_name = recipient_name.strip()
        self._address = address.strip()
        self._order_date = order_date or date.today()
        self._status = status if status in self.VALID_STATUSES else "Pending"
        self._tracking_number = tracking_number.strip()
        self._delivery_date = delivery_date
        self._created_at = created_at or datetime.now()

    # ---------------- ENCAPSULATION: GETTERS AND SETTERS ----------------

    @property
    def order_id(self) -> str:
        return self._order_id

    @order_id.setter
    def order_id(self, value: str) -> None:
        self._order_id = value
        self._id = value

    @property
    def recipient_id(self) -> Optional[int]:
        return self._recipient_id

    @recipient_id.setter
    def recipient_id(self, value: Optional[int]) -> None:
        self._recipient_id = value

    @property
    def recipient_name(self) -> str:
        return self._recipient_name

    @recipient_name.setter
    def recipient_name(self, value: str) -> None:
        self._recipient_name = value.strip()

    @property
    def address(self) -> str:
        return self._address

    @address.setter
    def address(self, value: str) -> None:
        self._address = value.strip()

    @property
    def order_date(self) -> Union[date, str]:
        return self._order_date

    @order_date.setter
    def order_date(self, value: Union[date, str]) -> None:
        self._order_date = value

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        if value not in self.VALID_STATUSES:
            raise ValidationError(f"Invalid shipment status: {value}")
        self._status = value

    @property
    def tracking_number(self) -> str:
        return self._tracking_number

    @tracking_number.setter
    def tracking_number(self, value: str) -> None:
        self._tracking_number = value.strip()

    @property
    def delivery_date(self) -> Optional[Union[date, str]]:
        return self._delivery_date

    @delivery_date.setter
    def delivery_date(self, value: Optional[Union[date, str]]) -> None:
        self._delivery_date = value

    # ---------------- POLYMORPHIC METHODS ----------------

    def validate(self) -> None:
        """Validates shipment order constraints."""
        if not self._recipient_id:
            raise EmptyFieldException("Please select a valid recipient.")
        if not self._address:
            raise EmptyFieldException("Recipient has no address saved. Add one first.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self._order_id,
            "recipient_id": self._recipient_id,
            "recipient_name": self._recipient_name,
            "address": self._address,
            "order_date": str(self._order_date),
            "status": self._status,
            "tracking_number": self._tracking_number,
            "delivery_date": str(self._delivery_date) if self._delivery_date else "",
            "created_at": self._created_at.isoformat() if self._created_at else ""
        }

    def to_treeview_tuple(self) -> Tuple[Any, ...]:
        return (
            self._order_id,
            self._recipient_id,
            self._recipient_name,
            str(self._order_date),
            self._status,
            self._tracking_number,
            str(self._delivery_date) if self._delivery_date else ""
        )

    @classmethod
    def from_row(cls, row: Tuple[Any, ...]) -> "Shipment":
        if not row:
            raise ValidationError("Cannot construct Shipment from empty row.")

        return cls(
            order_id=str(row[0]),
            recipient_id=row[1] if row[1] is not None else None,
            recipient_name=str(row[2] or ""),
            order_date=row[3],
            status=str(row[4] or "Pending"),
            tracking_number=str(row[5] or ""),
            delivery_date=row[6] if len(row) > 6 else None
        )
