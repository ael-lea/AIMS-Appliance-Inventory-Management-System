"""Reads and updates the logged-in employee's own account (used by the settings menu)."""
import string
from collections import namedtuple

from auth import hash_password, verify_password
from cashier.database.base_repository import BaseRepository

MIN_PASSWORD_LENGTH = 8          # same rule as the Employees form and Sign Up

EmployeeProfile = namedtuple("EmployeeProfile", "name role email contact date_joined")


class ProfileError(Exception):
    """An input rule was broken (bad value, wrong password...). The message is safe to show the user."""


def password_problems(password):
    """The password rules this password breaks (an empty list means it is fine)."""
    problems = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"At least {MIN_PASSWORD_LENGTH} characters")
    if not any(c.islower() for c in password):
        problems.append("At least one lowercase letter (a-z)")
    if not any(c.isupper() for c in password):
        problems.append("At least one uppercase letter (A-Z)")
    if not any(c in string.punctuation for c in password):
        problems.append("At least one special character (! @ # $ % ...)")
    return problems


class EmployeeRepository(BaseRepository):

    def ensure_schema(self):
        """Nothing to create: employee_data belongs to the Admin Employees module."""

    def get_profile(self, employee_id):
        """Name, role, email, contact number and date joined. None if the account is gone."""
        with self._database.cursor() as cursor:
            cursor.execute(
                "SELECT name, role, email, contact, dj FROM employee_data WHERE empid=%s",
                (employee_id,))
            row = cursor.fetchone()
        return EmployeeProfile(*row) if row else None

    def update_profile(self, employee_id, name, email, contact):
        """Save the details a cashier may change about themselves. Returns the saved name.

        Role, salary and the other fields are not touched here, so a cashier can never
        change their own role. Same input rules as the Employees form.
        """
        name = (name or "").strip()
        email = (email or "").strip()
        contact = (contact or "").strip()
        if not name or not email or not contact:
            raise ProfileError("Name, email and contact number are required.")
        if not all(ch.isalpha() or ch.isspace() for ch in name):
            raise ProfileError("Name must contain letters only.")
        if len(name) > 100 or len(email) > 100:
            raise ProfileError("Name and email must be at most 100 characters.")
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ProfileError("Enter a valid email address.")
        if not contact.isdigit():
            raise ProfileError("Contact number must contain digits only.")
        if len(contact) != 10:
            raise ProfileError("Contact number must contain exactly 10 digits.")
        if not contact.startswith("9"):
            raise ProfileError("Contact number must start with 9.")

        with self._database.cursor() as cursor:
            cursor.execute("SELECT empid FROM employee_data WHERE name=%s AND empid<>%s",
                           (name, employee_id))
            taken = cursor.fetchone() is not None
        if taken:
            raise ProfileError("That name is already used by another employee.")

        with self._database.cursor(commit=True) as cursor:
            cursor.execute("UPDATE employee_data SET name=%s, email=%s, contact=%s WHERE empid=%s",
                           (name, email, contact, employee_id))
        return name

    def change_password(self, employee_id, current, new, confirm):
        """Change the logged-in employee's own password (the current one must be correct)."""
        if not current or not new or not confirm:
            raise ProfileError("All fields are required.")
        with self._database.cursor() as cursor:
            cursor.execute("SELECT password FROM employee_data WHERE empid=%s", (employee_id,))
            row = cursor.fetchone()
        if row is None:
            raise ProfileError("Account not found.")
        is_correct, _ = verify_password(row[0], current)
        if not is_correct:
            raise ProfileError("Current password is incorrect.")
        if new != confirm:
            raise ProfileError("New Password and Confirm Password must be the same.")
        if new == current:
            raise ProfileError("The new password must be different from the current one.")
        problems = password_problems(new)
        if problems:
            raise ProfileError("The password must have:\n\n- " + "\n- ".join(problems))
        with self._database.cursor(commit=True) as cursor:
            cursor.execute("UPDATE employee_data SET password=%s WHERE empid=%s",
                           (hash_password(new), employee_id))