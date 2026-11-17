"""Password utilities. Hashing and checking are done by the project-root auth.py."""
from typing import Tuple

import auth as _auth


class PasswordSecurity:
    @staticmethod
    def hash_password(password: str) -> str:
        return _auth.hash_password(password)

    @staticmethod
    def verify_password(stored_hash: str, entered_password: str) -> Tuple[bool, bool]:
        return _auth.verify_password(stored_hash, entered_password)


def hash_password(password: str) -> str:
    return PasswordSecurity.hash_password(password)


def verify_password(stored_hash: str, entered_password: str) -> Tuple[bool, bool]:
    return PasswordSecurity.verify_password(stored_hash, entered_password)