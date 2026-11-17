"""
Recipient Domain Model.
Demonstrates:
- Inheritance (Recipient inherits from BaseModel)
- Encapsulation (Contact and Name validation rules)
- Polymorphism (Overriding to_dict, from_row, to_treeview_tuple, validate)
- Custom Exceptions (EmptyFieldException, InvalidDataTypeException)
"""
import re
from typing import Any, Dict, Optional, Tuple
from .base import BaseModel
from ..core.exceptions import EmptyFieldException, InvalidDataTypeException, ValidationError


class Recipient(BaseModel):
    """
    Represents a shipping recipient/customer.
    Encapsulates contact details and address information.
    """

    PHONE_REGEX = re.compile(r"^9\d{9}$")
    NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z .,'&-]*$")

    def __init__(
        self,
        invoice: Optional[int] = None,
        name: str = "",
        contact: str = "",
        address: str = "",
        description: str = ""
    ):
        super().__init__(entity_id=invoice)
        self._name = name.strip()
        self._contact = contact.strip()
        self._address = address.strip()
        self._description = description.strip()

    # ---------------- ENCAPSULATION: GETTERS AND SETTERS ----------------

    @property
    def invoice(self) -> Optional[int]:
        return self._id

    @invoice.setter
    def invoice(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        val = str(value).strip()
        if not val:
            raise EmptyFieldException("Recipient name is required.", field_name="name")
        if not self.NAME_REGEX.fullmatch(val):
            raise InvalidDataTypeException("Recipient Name must contain letters only (no numbers).", field_name="name")
        self._name = val

    @property
    def contact(self) -> str:
        return self._contact

    @contact.setter
    def contact(self, value: str) -> None:
        val = str(value).strip()
        if not val:
            raise EmptyFieldException("Contact number is required.", field_name="contact")
        if not self.PHONE_REGEX.fullmatch(val):
            raise InvalidDataTypeException(
                "Contact must be exactly 10 digits and start with 9 (e.g. 9123456789)",
                field_name="contact"
            )
        self._contact = val

    @property
    def address(self) -> str:
        return self._address

    @address.setter
    def address(self, value: str) -> None:
        val = str(value).strip()
        if not val:
            raise EmptyFieldException("Address is required.", field_name="address")
        self._address = val

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = str(value).strip()

    # ---------------- POLYMORPHIC METHODS ----------------

    def validate(self) -> None:
        """Validates that all required fields meet business rules."""
        if not self._name or not self._contact or not self._address:
            raise EmptyFieldException("Name, contact and address are required.")
        self.name = self._name
        self.contact = self._contact
        self.address = self._address

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invoice": self._id,
            "name": self._name,
            "contact": self._contact,
            "address": self._address,
            "description": self._description
        }

    def to_treeview_tuple(self) -> Tuple[Any, ...]:
        return (
            str(self._id) if self._id is not None else "",
            self._name,
            self._contact,
            self._address,
            self._description
        )

    @classmethod
    def from_row(cls, row: Tuple[Any, ...]) -> "Recipient":
        if not row:
            raise ValidationError("Cannot construct Recipient from empty row.")

        return cls(
            invoice=row[0],
            name=row[1] or "",
            contact=row[2] or "",
            address=row[3] or "",
            description=row[4] if len(row) > 4 and row[4] else ""
        )
