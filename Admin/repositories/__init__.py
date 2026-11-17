"""
Repositories Package for AIMS.
Exposes data access objects: BaseRepository, EmployeeRepository, ProductRepository,
RecipientRepository, ShipmentRepository, SalesRepository.
"""
from .base import BaseRepository
from .employee_repo import EmployeeRepository
from .product_repo import ProductRepository
from .recipient_repo import RecipientRepository
from .shipment_repo import ShipmentRepository
from .sales_repo import SalesRepository

__all__ = [
    "BaseRepository",
    "EmployeeRepository",
    "ProductRepository",
    "RecipientRepository",
    "ShipmentRepository",
    "SalesRepository"
]
