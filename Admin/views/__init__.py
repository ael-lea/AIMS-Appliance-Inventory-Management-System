"""
Views Package for AIMS.
Exposes view components:
- BaseFormView
- EmployeeView
- ProductView
- RecipientView
- ShipmentView
- SalesView
- AdminSettingsView
- LoginWindow
- DashboardWindow
"""
from .base_view import BaseFormView
from .employees_view import EmployeeView
from .products_view import ProductView
from .recipient_view import RecipientView
from .shipment_view import ShipmentView
from .sales_view import SalesView
from .admin_settings_view import AdminSettingsView
from .dashboard_view import DashboardWindow

__all__ = [
    "BaseFormView",
    "EmployeeView",
    "ProductView",
    "RecipientView",
    "ShipmentView",
    "SalesView",
    "AdminSettingsView",
    "DashboardWindow"
]
