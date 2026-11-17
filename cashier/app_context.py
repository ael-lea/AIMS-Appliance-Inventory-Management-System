"""Creates and holds every shared object (dependency container)."""
from cashier.database.connection import DatabaseManager
from cashier.database.employee_repository import EmployeeRepository
from cashier.database.order_repository import OrderRepository
from cashier.database.product_repository import ProductRepository
from cashier.database.recipient_repository import RecipientRepository
from cashier.database.sales_repository import SalesRepository
from cashier.database.shipment_repository import ShipmentRepository
from cashier.services.checkout_service import CheckoutService
from cashier.services.receipt import ReceiptPrinter
from cashier.state import PendingOrderBuffer


class AppContext:
    """Pages receive this object instead of creating their own database code."""

    def __init__(self):
        database = DatabaseManager()
        self._products = ProductRepository(database)
        self._orders = OrderRepository(database)
        self._sales = SalesRepository(database)
        self._shipments = ShipmentRepository(database)
        self._employees = EmployeeRepository(database)
        self._recipients = RecipientRepository(database)
        self._checkout = CheckoutService(database, self._orders, self._sales,
                                         self._shipments, self._products)
        self._receipts = ReceiptPrinter()
        self._pending_order = PendingOrderBuffer()

    @property
    def products(self):
        return self._products

    @property
    def orders(self):
        return self._orders

    @property
    def sales(self):
        return self._sales

    @property
    def shipments(self):
        return self._shipments

    @property
    def employees(self):
        return self._employees

    @property
    def recipients(self):
        return self._recipients

    @property
    def checkout(self):
        return self._checkout

    @property
    def receipts(self):
        return self._receipts

    @property
    def pending_order(self):
        return self._pending_order

    def initialize_schema(self):
        """Polymorphism: every repository prepares its own tables."""
        for repository in (self._products, self._orders, self._sales,
                           self._shipments, self._recipients):
            repository.ensure_schema()