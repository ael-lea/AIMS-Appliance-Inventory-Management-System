"""
Sale Domain Model.
Demonstrates:
- Inheritance (Sale inherits from BaseModel)
- Encapsulation (Computed total, price and quantity rules)
- Polymorphism (Overriding to_dict, from_row, to_treeview_tuple, validate)
"""
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union
from .base import BaseModel
from ..core.exceptions import EmptyFieldException, InvalidDataTypeException, ValidationError


class Sale(BaseModel):
    """
    Represents a finalized sales transaction record.
    Encapsulates itemized product details, unit price, quantity, and total.
    """

    def __init__(
        self,
        sale_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_name: str = "",
        category: str = "",
        quantity: int = 1,
        unit_price: float = 0.0,
        total: Optional[float] = None,
        sale_date: Optional[Union[datetime, str]] = None
    ):
        super().__init__(entity_id=sale_id)
        self._product_id = product_id
        self._product_name = product_name.strip()
        self._category = category.strip()
        self._quantity = int(quantity) if quantity else 1
        self._unit_price = float(unit_price) if unit_price else 0.0
        self._total = float(total) if total is not None else (self._quantity * self._unit_price)
        self._sale_date = sale_date or datetime.now()

    # ---------------- ENCAPSULATION: GETTERS AND SETTERS ----------------

    @property
    def sale_id(self) -> Optional[int]:
        return self._id

    @sale_id.setter
    def sale_id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def product_id(self) -> Optional[int]:
        return self._product_id

    @product_id.setter
    def product_id(self, value: Optional[int]) -> None:
        self._product_id = value

    @property
    def product_name(self) -> str:
        return self._product_name

    @product_name.setter
    def product_name(self, value: str) -> None:
        val = str(value).strip()
        if not val:
            raise EmptyFieldException("Product name cannot be empty.", field_name="product_name")
        self._product_name = val

    @property
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        self._category = str(value).strip()

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, value: Union[int, str]) -> None:
        try:
            val = int(value)
            if val <= 0:
                raise ValueError
            self._quantity = val
            self._total = self._quantity * self._unit_price
        except (ValueError, TypeError):
            raise InvalidDataTypeException("Quantity must be a positive integer greater than zero.", field_name="quantity")

    @property
    def unit_price(self) -> float:
        return self._unit_price

    @unit_price.setter
    def unit_price(self, value: Union[float, int, str]) -> None:
        try:
            val = float(value)
            if val < 0:
                raise ValueError
            self._unit_price = val
            self._total = self._quantity * self._unit_price
        except (ValueError, TypeError):
            raise InvalidDataTypeException("Unit price cannot be negative.", field_name="unit_price")

    @property
    def total(self) -> float:
        return self._total

    @property
    def sale_date(self) -> Union[datetime, str]:
        return self._sale_date

    @sale_date.setter
    def sale_date(self, value: Union[datetime, str]) -> None:
        self._sale_date = value

    # ---------------- POLYMORPHIC METHODS ----------------

    def validate(self) -> None:
        if not self._product_name:
            raise EmptyFieldException("Product name cannot be empty.")
        if self._quantity <= 0:
            raise InvalidDataTypeException("Sale quantity must be at least 1.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sale_id": self._id,
            "product_id": self._product_id,
            "product_name": self._product_name,
            "category": self._category,
            "quantity": self._quantity,
            "unit_price": self._unit_price,
            "total": self._total,
            "sale_date": str(self._sale_date)
        }

    def to_treeview_tuple(self) -> Tuple[Any, ...]:
        return (
            self._id,
            str(self._sale_date)[:16],
            self._product_name,
            self._category,
            self._quantity,
            f"₱{self._unit_price:,.2f}",
            f"₱{self._total:,.2f}"
        )

    @classmethod
    def from_row(cls, row: Tuple[Any, ...]) -> "Sale":
        if not row:
            raise ValidationError("Cannot construct Sale from empty row.")

        return cls(
            sale_id=row[0],
            product_id=row[1],
            product_name=str(row[2] or ""),
            category=str(row[3] or ""),
            quantity=int(row[4] or 0),
            unit_price=float(row[5] or 0.0),
            total=float(row[6] or 0.0),
            sale_date=row[7] if len(row) > 7 else datetime.now()
        )
