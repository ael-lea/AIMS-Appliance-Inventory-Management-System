"""
AIMS (Admin Inventory Management System) Package.
A fully Object-Oriented Inventory, Logistics, and Personnel Management Application.
"""

from .core.exceptions import (
    AIMSException,
    ValidationError,
    EmptyFieldException,
    InvalidDataTypeException,
    DuplicateRecordException,
    RecordNotFoundException,
    FileStorageException,
    DatabaseOperationException,
    AuthenticationException
)
from .core.interfaces import IModel, IRepository, IDataStorage, IView
from .core.database import DatabaseManager, DatabaseConfig
from .core.session import SessionManager
from .core.security import PasswordSecurity
from .core.storage import CSVStorage, JSONStorage, SQLBackupStorage

from .models.base import BaseModel
from .models.employee import Employee
from .models.product import Product
from .models.recipient import Recipient
from .models.shipment import Shipment
from .models.sale import Sale
from .models.user import User, AdminUser, CashierUser

from .repositories.employee_repo import EmployeeRepository
from .repositories.product_repo import ProductRepository
from .repositories.recipient_repo import RecipientRepository
from .repositories.shipment_repo import ShipmentRepository
from .repositories.sales_repo import SalesRepository

from .views.dashboard_view import DashboardWindow
from .views.employees_view import EmployeeView
from .views.products_view import ProductView
from .views.recipient_view import RecipientView
from .views.shipment_view import ShipmentView
from .views.sales_view import SalesView
from .views.admin_settings_view import AdminSettingsView

__all__ = [
    # Core
    "AIMSException",
    "ValidationError",
    "EmptyFieldException",
    "InvalidDataTypeException",
    "DuplicateRecordException",
    "RecordNotFoundException",
    "FileStorageException",
    "DatabaseOperationException",
    "AuthenticationException",
    "IModel",
    "IRepository",
    "IDataStorage",
    "IView",
    "DatabaseManager",
    "DatabaseConfig",
    "SessionManager",
    "PasswordSecurity",
    # Models
    "Employee",
    "Product",
    "Recipient",
    "Shipment",
    "Sale",
    "User",
    "AdminUser",
    "CashierUser",
    # Repositories
    "EmployeeRepository",
    "ProductRepository",
    "RecipientRepository",
    "ShipmentRepository",
    "SalesRepository",
    # Views
    "DashboardWindow",
    "EmployeeView",
    "ProductView",
    "RecipientView",
    "ShipmentView",
    "SalesView",
    "AdminSettingsView"
]
