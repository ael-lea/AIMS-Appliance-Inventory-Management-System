"""
Product Domain Model.
Demonstrates:
- Inheritance (Product inherits from BaseModel)
- Encapsulation (Properties, setters, input validation)
- Polymorphism (Overriding to_dict, from_row, to_treeview_tuple, validate)
- Custom Exceptions (EmptyFieldException, InvalidDataTypeException, ValidationError)
"""
import os
import re
from typing import Any, Dict, Optional, Tuple, Union
from .base import BaseModel
from ..core.exceptions import EmptyFieldException, InvalidDataTypeException, ValidationError


class Product(BaseModel):
    """
    Represents an inventory product item.
    Encapsulates pricing, stock quantity, category, and image reference.
    """

    def __init__(
        self,
        product_id: Optional[int] = None,
        name: str = "",
        category: str = "",
        price: float = 0.0,
        quantity: int = 0,
        image_path: str = ""
    ):
        super().__init__(entity_id=product_id)
        self._name = name.strip()
        self._category = category.strip()
        self._price = float(price) if price else 0.0
        self._quantity = int(quantity) if quantity else 0
        self._image_path = image_path.strip() if image_path else ""

    # ---------------- ENCAPSULATION: GETTERS AND SETTERS ----------------

    @property
    def product_id(self) -> Optional[int]:
        return self._id

    @product_id.setter
    def product_id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        val = str(value).strip()
        if not val:
            raise EmptyFieldException("Product name cannot be empty.", field_name="name")
        self._name = val

    @property
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        self._category = str(value).strip()

    @property
    def price(self) -> float:
        return self._price

    @price.setter
    def price(self, value: Union[float, int, str]) -> None:
        try:
            val = float(value)
            if val < 0:
                raise ValueError
            self._price = val
        except (ValueError, TypeError):
            raise InvalidDataTypeException("Price must be a valid non-negative number.", field_name="price")

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, value: Union[int, str]) -> None:
        try:
            val = int(value)
            if val < 0:
                raise ValueError
            self._quantity = val
        except (ValueError, TypeError):
            raise InvalidDataTypeException("Quantity must be a non-negative whole integer.", field_name="quantity")

    @property
    def image_path(self) -> str:
        return self._image_path

    @image_path.setter
    def image_path(self, value: str) -> None:
        self._image_path = str(value).strip()

    # ---------------- POLYMORPHIC METHODS ----------------

    def validate(self) -> None:
        """Validates product fields according to business rules."""
        if not self._name:
            raise EmptyFieldException("Please enter the product name.", field_name="name")
        if self._price < 0 or self._quantity < 0:
            raise InvalidDataTypeException("Price and quantity cannot be negative.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self._id,
            "name": self._name,
            "category": self._category,
            "price": self._price,
            "quantity": self._quantity,
            "image_path": self._image_path
        }

    def to_treeview_tuple(self) -> Tuple[Any, ...]:
        return (
            str(self._id) if self._id is not None else "",
            self._name,
            self._category or "",
            f"{self._price:.2f}",
            self._quantity
        )

    @classmethod
    def from_row(cls, row: Tuple[Any, ...]) -> "Product":
        if not row:
            raise ValidationError("Cannot construct Product from empty row.")

        product_id = row[0]
        name = row[1]
        category = row[2] if len(row) > 2 else ""
        price = float(row[3]) if len(row) > 3 and row[3] is not None else 0.0
        quantity = int(row[4]) if len(row) > 4 and row[4] is not None else 0
        image_path = row[5] if len(row) > 5 and row[5] is not None else ""

        return cls(
            product_id=product_id,
            name=name,
            category=category,
            price=price,
            quantity=quantity,
            image_path=image_path
        )
