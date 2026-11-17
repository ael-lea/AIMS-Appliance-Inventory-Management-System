"""
Authentication and Security Module.
Demonstrates:
- Object-Oriented Programming (Classes and Objects)
- Abstraction & Interfaces (IAuthenticator abstract interface)
- Inheritance & Polymorphism (WerkzeugAuthenticator implements IAuthenticator)
- Encapsulation (DatabaseConfig, ConnectionFactory)
- Exception Handling (DatabaseOperationException, AuthenticationException)
"""
import hashlib
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from core_exceptions import DatabaseOperationException, AuthenticationException


class DatabaseConfig:
    """Encapsulates MySQL database connection parameters."""
    def __init__(self, host: str = "localhost", user: str = "root", password: str = "", database: str = "inventory_system"):
        self._host = host
        self._user = user
        self._password = password
        self._database = database

    @property
    def host(self) -> str:
        return self._host

    @property
    def user(self) -> str:
        return self._user

    @property
    def password(self) -> str:
        return self._password

    @property
    def database(self) -> str:
        return self._database

    def to_dict(self) -> Dict[str, str]:
        return {
            "host": self._host,
            "user": self._user,
            "password": self._password,
            "database": self._database
        }


class IAuthenticator(ABC):
    """
    Abstract Interface for credential hashing and verification.
    Demonstrates Abstraction and Interface design.
    """

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash cleartext password using cryptographic algorithm."""
        pass

    @abstractmethod
    def verify_password(self, stored_hash: str, entered_password: str) -> Tuple[bool, bool]:
        """Verify entered password against stored hash. Returns (is_correct, needs_upgrade)."""
        pass


class WerkzeugAuthenticator(IAuthenticator):
    """
    Concrete Authenticator implementing Werkzeug scrypt hashing with legacy SHA-256 fallback.
    Demonstrates Inheritance and Polymorphism.
    """

    def hash_password(self, password: str) -> str:
        if not password:
            return ""
        return generate_password_hash(password)

    def verify_password(self, stored_hash: str, entered_password: str) -> Tuple[bool, bool]:
        if not stored_hash or not entered_password:
            return False, False

        # Modern Werkzeug hash (e.g. scrypt:32768:8:1$salt$hash)
        if "$" in stored_hash:
            return check_password_hash(stored_hash, entered_password), False

        # Legacy plain SHA-256 hex string fallback
        if hashlib.sha256(entered_password.encode("utf-8")).hexdigest() == stored_hash:
            return True, True

        return False, False


class ConnectionFactory:
    """
    Encapsulates database connection management and error handling.
    """
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self._config = config or DatabaseConfig()

    def get_connection(self) -> pymysql.Connection:
        try:
            return pymysql.connect(
                host=self._config.host,
                user=self._config.user,
                password=self._config.password,
                database=self._config.database
            )
        except pymysql.MySQLError as err:
            raise DatabaseOperationException(f"Failed to connect to MySQL database: {err}")


# Singletons
_default_config = DatabaseConfig()
_default_authenticator = WerkzeugAuthenticator()
_default_factory = ConnectionFactory(_default_config)

# Legacy compatibility exports
DB_CONFIG = _default_config.to_dict()


def get_connection() -> pymysql.Connection:
    return _default_factory.get_connection()


def hash_password(password: str) -> str:
    return _default_authenticator.hash_password(password)


def verify_password(stored: str, entered: str) -> Tuple[bool, bool]:
    return _default_authenticator.verify_password(stored, entered)
