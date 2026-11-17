"""
Comprehensive Verification Test for AIMS Project Requirements.
"""

import sys
import os
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)          # replaces line 7
TMP = tempfile.gettempdir()



from Admin import (
    BaseModel,
    Employee,
    Product,
    Recipient,
    Shipment,
    Sale,
    User,
    AdminUser,
    CashierUser,
    AIMSException,
    ValidationError,
    EmptyFieldException,
    InvalidDataTypeException,
    DuplicateRecordException,
    RecordNotFoundException,
    FileStorageException,
    CSVStorage,
    JSONStorage,
    SQLBackupStorage
)


def run_tests():
    print("==========================================")
    print("STARTING AIMS REQUIREMENTS VERIFICATION")
    print("==========================================")

    # 1. Classes, Objects, Constructors, Encapsulation
    emp = Employee(
        empid=1,
        name="John Doe",
        email="john@aims.com",
        sex="Male",
        contact="9123456789",
        employment_type="Full Time",
        work_shift="Morning",
        address="123 Main St",
        salary=25000.0,
        role="Admin"
    )
    assert emp.name == "John Doe"
    assert emp.salary == 25000.0
    assert emp.contact == "9123456789"
    print("[PASS] 1. Classes, Objects, Constructors & Encapsulation")

    # 2. Inheritance
    assert isinstance(emp, BaseModel)
    admin = AdminUser(1, "Admin", "admin@aims.com")
    cashier = CashierUser(2, "Cashier1", "cashier@aims.com")
    assert isinstance(admin, User)
    assert isinstance(cashier, User)
    assert isinstance(admin, BaseModel)
    print("[PASS] 2. Inheritance Hierarchy (BaseModel -> User -> AdminUser / CashierUser)")

    # 3. Polymorphism
    assert admin.has_permission("delete_employee") is True
    assert cashier.has_permission("delete_employee") is False
    assert admin.get_dashboard_title() == "Admin Dashboard - Admin"
    assert cashier.get_dashboard_title() == "Cashier Dashboard - Cashier1"

    # Polymorphic to_dict and to_treeview_tuple
    emp_dict = emp.to_dict()
    assert isinstance(emp_dict, dict)
    emp_tuple = emp.to_treeview_tuple()
    assert isinstance(emp_tuple, tuple)
    print("[PASS] 3. Polymorphism (has_permission, to_dict, to_treeview_tuple)")

    # 4. Exception Handling: Invalid Input, Empty Fields, Invalid Data Types
    try:
        emp.contact = "12345"  # Too short, not starting with 9
        assert False, "Should have raised InvalidDataTypeException"
    except InvalidDataTypeException as e:
        assert e.field_name == "contact"
        print(f"[PASS] 4a. Exception Handling - Invalid Contact: {e}")

    try:
        emp.name = ""  # Empty name
        assert False, "Should have raised EmptyFieldException"
    except EmptyFieldException as e:
        assert e.field_name == "name"
        print(f"[PASS] 4b. Exception Handling - Empty Field: {e}")

    try:
        emp.salary = -500  # Negative salary
        assert False, "Should have raised InvalidDataTypeException"
    except InvalidDataTypeException as e:
        print(f"[PASS] 4c. Exception Handling - Negative Salary: {e}")

    # 5. File Storage & Exception Handling: Save Data, Load Data, File Errors
    csv_store = CSVStorage()
    json_store = JSONStorage()

    test_records = [
        {"id": 1, "name": "Laptop", "price": 45000.0, "quantity": 10},
        {"id": 2, "name": "Mouse", "price": 500.0, "quantity": 50}
    ]

    csv_path  = os.path.join(TMP, "test_products.csv")
    json_path = os.path.join(TMP, "test_products.json")

    # Save Data
    csv_count = csv_store.save(test_records, csv_path)
    json_count = json_store.save(test_records, json_path)
    assert csv_count == 2
    assert json_count == 2
    print("[PASS] 5a. Functional Feature - Save Data (CSV & JSON)")

    # Load Data
    loaded_csv = csv_store.load(csv_path)
    loaded_json = json_store.load(json_path)
    assert len(loaded_csv) == 2
    assert len(loaded_json) == 2
    print("[PASS] 5b. Functional Feature - Load Data (CSV & JSON)")

    # File Error Handling (Missing File)
    try:
        csv_store.load(os.path.join(TMP, "non_existent_file.csv"))
        assert False, "Should have raised FileStorageException"
    except FileStorageException as e:
        print(f"[PASS] 5c. Exception Handling - Missing File Error: {e}")

    # Cleanup temp test files
    if os.path.exists(csv_path):
        os.remove(csv_path)
    if os.path.exists(json_path):
        os.remove(json_path)

    # 6. Method Overloading Verification
    from Admin.repositories.base import BaseRepository

    class MockRepo(BaseRepository):
        def __init__(self):
            super().__init__(table_name="mock_table", id_column="id")
        def _map_row(self, row):
            return row
        def add(self, entity): pass
        def update(self, entity): pass
        def delete(self, entity_id): pass
        def get_by_id(self, entity_id):
            return f"Found by ID: {entity_id}"
        def get_all(self): return []
        def search(self, column, query):
            return [f"Found by text '{query}' in {column}"]

    mock_repo = MockRepo()
    res1 = mock_repo.find(101)  # int overload -> calls get_by_id
    res2 = mock_repo.find("Sample Query")  # str overload -> calls search
    assert res1 == "Found by ID: 101"
    assert res2 == ["Found by text 'Sample Query' in name"]
    print("[PASS] 6. Method Overloading (find dispatch by int vs str vs dict)")

    print("==========================================")
    print("ALL PROJECT REQUIREMENTS FULLY SATISFIED!")
    print("==========================================")


if __name__ == "__main__":
    run_tests()
