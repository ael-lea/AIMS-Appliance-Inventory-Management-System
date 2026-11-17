"""Checkout business logic: hold an order or confirm (pay for) it."""
from collections import namedtuple

from cashier.models import Order

# Who an order is shipped to. Build it from the selected row of the recipient directory.
ShipTo = namedtuple("ShipTo", "recipient_id name address")


class InsufficientStockError(Exception):
    """Raised when a product no longer has enough stock at confirmation."""


class CheckoutService:
    """Coordinates the repositories so each checkout is ONE database transaction."""

    def __init__(self, database, orders, sales, shipments, products):
        self._database = database
        self._orders = orders
        self._sales = sales
        self._shipments = shipments
        self._products = products

    def hold(self, cart, resumed_order_id=None, recipient_id=None, ship_order=True):
        """Save the cart as a Pending order (stock is NOT deducted). Returns the order ID.

        The recipient and the 'Ship this order' choice are saved with it so they can be
        restored when the order is resumed.
        """
        with self._database.cursor(commit=True) as cursor:
            order_id = resumed_order_id or self._orders.next_order_id(cursor)
            self._orders.save(cursor, Order.from_cart(order_id, cart, Order.PENDING))
            self._orders.set_shipping(cursor, order_id, recipient_id, ship_order)
        return order_id

    def confirm(self, cart, payment, result, ship_to=None, resumed_order_id=None):
        """Complete the sale: deduct stock, save order, record sales, create shipment.

        ship_to is a ShipTo, or None when 'Ship this order' is unticked (no shipment is made).
        """
        if ship_to is not None and ship_to.recipient_id is None:
            raise ValueError("Select a recipient before confirming a shipped order.")
        with self._database.cursor(commit=True) as cursor:
            # Re-check stock inside the transaction to prevent overselling.
            for item in cart:
                if not self._products.deduct_stock(cursor, item.product_id, item.quantity):
                    raise InsufficientStockError(
                        f"Not enough stock for {item.name}. Please refresh the order.")
            order_id = resumed_order_id or self._orders.next_order_id(cursor)
            order = Order.from_cart(order_id, cart, Order.COMPLETED,
                                    payment.name, result.paid, result.change)
            self._orders.save(cursor, order)
            self._sales.record_sales(cursor, cart, order.order_date)
            if ship_to is not None:
                self._shipments.create_for_order(
                    cursor, order_id, ship_to.recipient_id, ship_to.name,
                    ship_to.address, order.order_date.date())
        return order