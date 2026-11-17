"""
Employee Repository Module.
Demonstrates:
- Inheritance (Inherits from BaseRepository)
- Polymorphism (Overriding add, update, delete, get_by_id, get_all, search)
- Encapsulated Business Rules & Constraints
- Custom Exception Handling (DuplicateRecordException, ValidationError, RecordNotFoundException)
"""
from typing import Any, List, Optional, Tuple
from .base import BaseRepository
from ..models.employee import Employee
from ..core.session import SessionManager
from ..core.exceptions import (
    DuplicateRecordException,
    ValidationError,
    RecordNotFoundException,
    DatabaseOperationException
)


class EmployeeRepository(BaseRepository):
    """
    Repository handling database CRUD operations for the employee_data table.
    """

    def __init__(self):
        super().__init__(table_name="employee_data", id_column="empid")

    def _map_row(self, row: Tuple[Any, ...]) -> Employee:
        return Employee.from_row(row)

    def add(self, employee: Employee) -> int:
        """
        Inserts a new employee record.
        Validates uniqueness of name and returns new empid.
        """
        employee.validate()

        # Check for duplicate employee name
        existing = self.execute_query(
            "SELECT empid FROM employee_data WHERE name = %s",
            (employee.name.strip(),),
            fetch="one"
        )
        if existing:
            raise DuplicateRecordException("Employee with this name already exists.")

        dob_str = employee.dob.strftime("%Y-%m-%d") if hasattr(employee.dob, "strftime") else str(employee.dob)
        dj_str = employee.dj.strftime("%Y-%m-%d") if hasattr(employee.dj, "strftime") else str(employee.dj)

        query = """
            INSERT INTO employee_data
            (name, email, sex, dob, contact, employment_type, work_shift, address, dj, salary, role, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            employee.name,
            employee.email,
            employee.sex,
            dob_str,
            employee.contact,
            employee.employment_type,
            employee.work_shift,
            employee.address,
            dj_str,
            employee.salary,
            employee.role,
            employee.password
        )
        new_id = self.execute_query(query, params, fetch="lastrowid")
        employee.empid = new_id
        return new_id

    def update(self, employee: Employee) -> bool:
        """
        Updates an existing employee.
        Enforces:
        1. Cannot demote the last Admin account.
        2. Cannot change name to match another existing employee.
        """
        if not employee.empid:
            raise ValidationError("Cannot update employee without a valid employee ID.")

        employee.validate()

        # 1. Protect last admin demotion
        if employee.role != "Admin":
            current = self.execute_query(
                "SELECT role FROM employee_data WHERE empid = %s",
                (employee.empid,),
                fetch="one"
            )
            if current and current[0] == "Admin":
                admin_count = self.count_admins()
                if admin_count <= 1:
                    raise ValidationError("You cannot change the role of the last Admin account.")

        # 2. Check duplicate name with another employee
        duplicate = self.execute_query(
            "SELECT empid FROM employee_data WHERE name = %s AND empid <> %s",
            (employee.name.strip(), employee.empid),
            fetch="one"
        )
        if duplicate:
            raise DuplicateRecordException("Another employee already uses that name.")

        dob_str = employee.dob.strftime("%Y-%m-%d") if hasattr(employee.dob, "strftime") else str(employee.dob)
        dj_str = employee.dj.strftime("%Y-%m-%d") if hasattr(employee.dj, "strftime") else str(employee.dj)

        query = """
            UPDATE employee_data
            SET name=%s, email=%s, sex=%s, dob=%s, contact=%s, employment_type=%s,
                work_shift=%s, address=%s, dj=%s, salary=%s, role=%s
            WHERE empid=%s
        """
        params = (
            employee.name,
            employee.email,
            employee.sex,
            dob_str,
            employee.contact,
            employee.employment_type,
            employee.work_shift,
            employee.address,
            dj_str,
            employee.salary,
            employee.role,
            employee.empid
        )
        self.execute_query(query, params)
        return True

    def delete(self, empid: int) -> bool:
        """
        Deletes an employee record.
        Enforces:
        1. Cannot delete currently logged in account.
        2. Cannot delete the last Admin account.
        """
        if not empid:
            raise RecordNotFoundException("Please select an employee to delete.")

        # 1. Cannot delete logged in account
        current_id = SessionManager.get_user_id()
        if current_id and str(empid) == str(current_id):
            raise ValidationError("You cannot delete the account you are currently logged in with.")

        # 2. Cannot delete last admin
        record = self.execute_query("SELECT role FROM employee_data WHERE empid=%s", (empid,), fetch="one")
        if not record:
            raise RecordNotFoundException(f"Employee ID {empid} not found.")

        if record[0] == "Admin" and self.count_admins() <= 1:
            raise ValidationError("You cannot delete the last Admin account.")

        self.execute_query("DELETE FROM employee_data WHERE empid=%s", (empid,))
        return True

    def get_by_id(self, empid: int) -> Optional[Employee]:
        row = self.execute_query(
            "SELECT empid, name, email, sex, dob, contact, employment_type, work_shift, address, dj, salary, role FROM employee_data WHERE empid=%s",
            (empid,),
            fetch="one"
        )
        return self._map_row(row) if row else None

    def get_all(self) -> List[Employee]:
        rows = self.execute_query(
            "SELECT empid, name, email, sex, dob, contact, employment_type, work_shift, address, dj, salary, role FROM employee_data ORDER BY empid",
            fetch="all"
        )
        return [self._map_row(r) for r in rows] if rows else []

    def search(self, column: str, query: str) -> List[Employee]:
        valid_columns = {
            "ID": "empid",
            "empid": "empid",
            "Name": "name",
            "name": "name",
            "Email": "email",
            "email": "email",
            "Employment Type": "employment_type",
            "employment_type": "employment_type",
            "Work Shift": "work_shift",
            "work_shift": "work_shift"
        }
        col = valid_columns.get(column, "name")
        sql = f"SELECT empid, name, email, sex, dob, contact, employment_type, work_shift, address, dj, salary, role FROM employee_data WHERE {col} LIKE %s"
        rows = self.execute_query(sql, (f"%{query}%",), fetch="all")
        return [self._map_row(r) for r in rows] if rows else []

    def count_all(self) -> int:
        row = self.execute_query("SELECT COUNT(*) FROM employee_data", fetch="one")
        return row[0] if row else 0

    def count_admins(self) -> int:
        row = self.execute_query("SELECT COUNT(*) FROM employee_data WHERE role='Admin'", fetch="one")
        return row[0] if row else 0
