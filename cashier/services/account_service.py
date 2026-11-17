"""Account rules for the logged-in employee (password change)."""
from auth import hash_password, verify_password


class AccountError(Exception):
    """A rule was broken; the message is safe to show to the cashier."""


class AccountService:
    MIN_PASSWORD_LENGTH = 6

    def __init__(self, employees):
        self._employees = employees

    def change_password(self, employee_id, current, new, confirm):
        if not current or not new or not confirm:
            raise AccountError("Fill in all three password fields.")
        if new != confirm:
            raise AccountError("New password and confirmation do not match.")
        if len(new) < self.MIN_PASSWORD_LENGTH:
            raise AccountError(f"Use at least {self.MIN_PASSWORD_LENGTH} characters.")
        if new == current:
            raise AccountError("The new password must be different from the current one.")
        stored = self._employees.get_password_hash(employee_id)
        if stored is None or not verify_password(stored, current)[0]:
            raise AccountError("Your current password is incorrect.")
        self._employees.update_password(employee_id, hash_password(new))
