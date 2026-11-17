"""
Employee Domain Model.
Demonstrates:
- Inheritance (Employee inherits from BaseModel)
- Constructors (__init__ with default & keyword arguments)
- Encapsulation (Private/protected attributes with @property getters & validation setters)
- Polymorphism (Overriding to_dict, from_row, to_treeview_tuple, validate)
- Custom Exception handling (EmptyFieldException, InvalidDataTypeException, ValidationError)
"""
import re
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple, Union
from .base import BaseModel
from ..core.exceptions import EmptyFieldException, InvalidDataTypeException, ValidationError


class Employee(BaseModel):
    """
    Represents an employee account within the inventory system.
    Encapsulates all personal, employment, and credential attributes.
    """

    def __init__(
        self,
        empid: Optional[int] = None,
        name: str = "",
        email: str = "",
        sex: str = "",
        dob: Optional[Union[date, str]] = None,
        contact: str = "",
        employment_type: str = "",
        work_shift: str = "",
        address: str = "",
        dj: Optional[Union[date, str]] = None,
        salary: float = 0.0,
        role: str = "",
        password: str = ""
    ):
        """
        Constructor initializing an Employee instance.
        Demonstrates proper constructor chaining with super().__init__().
        """
        super().__init__(entity_id=empid)
        self._name = name.strip()
        self._email = email.strip()
        self._sex = sex
        self._dob = dob or date.today()
        self._contact = contact.strip()
        self._employment_type = employment_type
        self._work_shift = work_shift
        self._address = address.strip()
        self._dj = dj or date.today()
        self._salary = float(salary) if salary else 0.0
        self._role = role
        self._password = password

    # ---------------- ENCAPSULATION: GETTERS AND SETTERS ----------------

    @property
    def empid(self) -> Optional[int]:
        return self._id

    @empid.setter
    def empid(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        val = value.strip()
        if not val:
            raise EmptyFieldException("Name cannot be empty.", field_name="name")
        if not all(char.isalpha() or char.isspace() for char in val):
            raise InvalidDataTypeException("Name must contain letters only.", field_name="name")
        self._name = val

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        val = value.strip()
        if not val:
            raise EmptyFieldException("Email cannot be empty.", field_name="email")
        local, _, domain = val.partition("@")
        if (" " in val or val.count("@") != 1 or not local
                or "." not in domain or domain.startswith(".") or domain.endswith(".")):
            raise InvalidDataTypeException(
                "Invalid email. It must contain an '@' (e.g. name@example.com).", field_name="email")
        self._email = val

    @property
    def sex(self) -> str:
        return self._sex

    @sex.setter
    def sex(self, value: str) -> None:
        if value in ("Select Sex", ""):
            raise EmptyFieldException("Please select a valid sex.", field_name="sex")
        self._sex = value

    @property
    def dob(self) -> Union[date, str]:
        return self._dob

    @dob.setter
    def dob(self, value: Union[date, str]) -> None:
        self._dob = value

    @property
    def contact(self) -> str:
        return self._contact

    @contact.setter
    def contact(self, value: str) -> None:
        val = str(value).strip()
        if not val:
            raise EmptyFieldException("Contact number cannot be empty.", field_name="contact")
        if not val.isdigit():
            raise InvalidDataTypeException("Contact number must contain digits only.", field_name="contact")
        if len(val) != 10:
            raise InvalidDataTypeException("Contact number must contain exactly 10 digits.", field_name="contact")
        if not val.startswith("9"):
            raise InvalidDataTypeException("Contact number must start with 9.", field_name="contact")
        self._contact = val

    @property
    def employment_type(self) -> str:
        return self._employment_type

    @employment_type.setter
    def employment_type(self, value: str) -> None:
        if value in ("Select Type", ""):
            raise EmptyFieldException("Please select an employment type.", field_name="employment_type")
        self._employment_type = value

    @property
    def work_shift(self) -> str:
        return self._work_shift

    @work_shift.setter
    def work_shift(self, value: str) -> None:
        if value in ("Select Work Shift", ""):
            raise EmptyFieldException("Please select a work shift.", field_name="work_shift")
        self._work_shift = value

    @property
    def address(self) -> str:
        return self._address

    @address.setter
    def address(self, value: str) -> None:
        val = value.strip()
        if not val:
            raise EmptyFieldException("Address cannot be empty.", field_name="address")
        self._address = val

    @property
    def dj(self) -> Union[date, str]:
        return self._dj

    @dj.setter
    def dj(self, value: Union[date, str]) -> None:
        self._dj = value

    @property
    def salary(self) -> float:
        return self._salary

    @salary.setter
    def salary(self, value: Union[float, int, str]) -> None:
        try:
            val = float(value)
            if val < 0:
                raise ValueError
            self._salary = val
        except (ValueError, TypeError):
            raise InvalidDataTypeException("Salary must be a valid positive number.", field_name="salary")

    @property
    def role(self) -> str:
        return self._role

    @role.setter
    def role(self, value: str) -> None:
        if value in ("Select Role", ""):
            raise EmptyFieldException("Please select a valid role.", field_name="role")
        self._role = value

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, value: str) -> None:
        self._password = value

    # ---------------- POLYMORPHIC METHODS ----------------

    def validate(self) -> None:
        """
        Validates all employee attributes according to business rules.
        Demonstrates Polymorphism and Exception Handling.
        """
        if (
            not self._name or not self._email or self._sex in ("Select Sex", "") or
            not self._contact or self._employment_type in ("Select Type", "") or
            self._work_shift in ("Select Work Shift", "") or not self._address.strip() or
            self._role in ("Select Role", "")
        ):
            raise EmptyFieldException("All fields must be answered.")

        # Re-trigger property validations
        self.name = self._name
        self.email = self._email
        self.contact = self._contact
        self.salary = self._salary

    def to_dict(self) -> Dict[str, Any]:
        """Polymorphic serialization to dictionary."""
        return {
            "empid": self._id,
            "name": self._name,
            "email": self._email,
            "sex": self._sex,
            "dob": str(self._dob),
            "contact": self._contact,
            "employment_type": self._employment_type,
            "work_shift": self._work_shift,
            "address": self._address,
            "dj": str(self._dj),
            "salary": self._salary,
            "role": self._role
        }

    def to_treeview_tuple(self) -> Tuple[Any, ...]:
        """Polymorphic representation for Tkinter Treeview row display."""
        return (
            self._id,
            self._name,
            self._email,
            self._sex,
            str(self._dob),
            self._contact,
            self._employment_type,
            self._work_shift,
            self._address,
            str(self._dj),
            f"{self._salary:.2f}",
            self._role
        )

    @classmethod
    def from_row(cls, row: Tuple[Any, ...]) -> "Employee":
        """
        Polymorphic factory method to construct an Employee from a database row tuple.
        Supports both 12-column and 13-column (with password) rows.
        """
        if not row:
            raise ValidationError("Cannot construct Employee from empty row.")

        empid = row[0]
        name = row[1]
        email = row[2]
        sex = row[3]
        dob = row[4]
        contact = row[5]
        employment_type = row[6]
        work_shift = row[7]
        address = row[8]
        dj = row[9]
        salary = float(row[10]) if row[10] is not None else 0.0
        role = row[11]
        password = row[12] if len(row) > 12 else ""

        return cls(
            empid=empid,
            name=name,
            email=email,
            sex=sex,
            dob=dob,
            contact=contact,
            employment_type=employment_type,
            work_shift=work_shift,
            address=address,
            dj=dj,
            salary=salary,
            role=role,
            password=password
        )