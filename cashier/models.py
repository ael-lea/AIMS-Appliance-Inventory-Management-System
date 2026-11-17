"""Domain models: Product, CartItem, Cart, Order and related value objects.

Encapsulation: the mutable classes (CartItem, Cart) keep their data in
private attributes and expose it through properties and methods.
Immutable records (OrderLine, Order, ...) are frozen dataclasses.
"""
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from functools import singledispatchmethod
from typing import Optional, Tuple

from cashier.config import Settings

PriceBreakdown = namedtuple("PriceBreakdown", "subtotal vat total")


class Product:
    """A product that can be sold (read-only view of a products row)."""

    def __init__(self, product_id, name, category, price, stock):
        self._product_id = product_id
        self._name = name
        self._category = category
        self._price = float(price)
        self._stock = int(stock)

    @property
    def product_id(self):
        return self._product_id

    @property
    def name(self):
        return self._name

    @property
    def category(self):
        return self._category

    @property
    def price(self):
        return self._price

    @property
    def stock(self):
        return self._stock


class CartItem:
    """One product line inside the cart."""

    def __init__(self, product_id, name, category, unit_price, quantity):
        self._product_id = product_id
        self._name = name
        self._category = category or None
        self._unit_price = float(unit_price)
        self._quantity = 0
        self.quantity = quantity           # goes through the validating setter

    # --- alternative constructors -------------------------------------
    @classmethod
    def from_product(cls, product, quantity=1):
        return cls(product.product_id, product.name, product.category,
                   product.price, quantity)

    @classmethod
    def from_order_line(cls, line):
        return cls(line.product_id, line.product_name, line.category,
                   line.unit_price, line.quantity)

    # --- read-only data -------------------------------------------------
    @property
    def product_id(self):
        return self._product_id

    @property
    def name(self):
        return self._name

    @property
    def category(self):
        return self._category

    @property
    def unit_price(self):
        return self._unit_price

    @property
    def line_total(self):
        return round(self._unit_price * self._quantity, 2)

    # --- validated quantity ------------------------------------------------
    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        value = int(value)
        if value < 0:
            raise ValueError("Quantity cannot be negative.")
        self._quantity = value

    def increase(self, amount):
        """Add `amount` units (use a negative number to remove units)."""
        self.quantity = self._quantity + amount


class Cart:
    """The order being built by the cashier."""

    def __init__(self, items=None):
        self._items = list(items) if items else []

    # --- container behaviour ------------------------------------------------
    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, index):
        return self._items[index]

    @property
    def is_empty(self):
        return not self._items

    def quantity_of(self, product_id):
        """Total units of one product already in the cart."""
        return sum(i.quantity for i in self._items if i.product_id == product_id)

    # --- method overloading (single dispatch on the argument type) ---------
    @singledispatchmethod
    def add(self, source, quantity=1):
        """add(Product, quantity) or add(CartItem): merges equal products."""
        raise TypeError(f"Cannot add {type(source).__name__} to the cart.")

    @add.register(Product)
    def _add_product(self, product, quantity=1):
        self._merge(CartItem.from_product(product, quantity))

    @add.register(CartItem)
    def _add_item(self, item, quantity=None):
        self._merge(item)

    @singledispatchmethod
    def remove(self, target):
        """remove(int index) or remove(CartItem)."""
        raise TypeError(f"Cannot remove {type(target).__name__} from the cart.")

    @remove.register(int)
    def _remove_at(self, index):
        self._items.pop(index)

    @remove.register(CartItem)
    def _remove_item(self, item):
        self._items.remove(item)

    def _merge(self, new_item):
        for item in self._items:
            if item.product_id == new_item.product_id:
                item.increase(new_item.quantity)
                return
        self._items.append(new_item)

    # --- changes ---------------------------------------------------------------
    def change_quantity(self, index, delta):
        """Change a line's quantity; the line disappears when it reaches 0."""
        item = self._items[index]
        item.quantity = max(0, item.quantity + delta)
        if item.quantity == 0:
            self._items.pop(index)

    def replace_with(self, items):
        self._items = list(items)

    def clear(self):
        self._items.clear()

    # --- totals ------------------------------------------------------------------
    @property
    def total(self):
        return round(sum(i.line_total for i in self._items), 2)

    @property
    def item_count(self):
        return sum(i.quantity for i in self._items)

    def breakdown(self, vat_rate=Settings.VAT_RATE):
        """Split the VAT-inclusive total into subtotal and VAT."""
        total = self.total
        subtotal = round(total / (1 + vat_rate), 2) if vat_rate else total
        return PriceBreakdown(subtotal, round(total - subtotal, 2), total)


@dataclass(frozen=True)
class OrderLine:
    """One saved line of an order."""
    product_id: Optional[int]
    product_name: str
    category: Optional[str]
    quantity: int
    unit_price: float
    line_total: float


@dataclass(frozen=True)
class Order:
    """A saved order (pending or completed) with its lines."""
    order_id: str
    order_date: datetime
    subtotal: float
    vat: float
    total: float
    payment_method: Optional[str]
    amount_paid: Optional[float]
    change_amount: Optional[float]
    status: str
    lines: Tuple[OrderLine, ...] = ()

    PENDING = "Pending"
    COMPLETED = "Completed"

    @classmethod
    def from_cart(cls, order_id, cart, status, payment_method=None,
                  amount_paid=None, change_amount=None):
        """Build an Order from the current cart."""
        figures = cart.breakdown()
        lines = tuple(
            OrderLine(i.product_id, i.name, i.category, i.quantity,
                      i.unit_price, i.line_total)
            for i in cart
        )
        return cls(order_id, datetime.now(), figures.subtotal, figures.vat,
                   figures.total, payment_method, amount_paid, change_amount,
                   status, lines)

    @property
    def is_pending(self):
        return self.status == self.PENDING


@dataclass(frozen=True)
class OrderSummary:
    """One row of the order-history / sales tables."""
    order_id: str
    order_date: datetime
    item_count: int
    total: float
    payment_method: str
    status: str


@dataclass(frozen=True)
class SalesSummary:
    """Headline numbers of the Sales Overview page."""
    total_sales: float
    transactions: int
    items_sold: int

    @property
    def average_order(self):
        return self.total_sales / self.transactions if self.transactions else 0.0


@dataclass(frozen=True)
class ShipmentRecord:
    """One row of shipping_orders."""
    order_id: str
    customer_name: str
    order_date: object
    status: str
    tracking_number: str
    delivery_date: object
