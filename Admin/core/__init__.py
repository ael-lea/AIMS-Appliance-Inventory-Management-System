"""
Core Package for AIMS.
Exposes database management, custom exceptions, interfaces, session, security, and storage.
"""
from .exceptions import (
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
from .interfaces import IModel, IRepository, IDataStorage, IView
from .database import DatabaseManager, DatabaseConfig
from .session import SessionManager, current_user
from .security import PasswordSecurity, hash_password, verify_password
from .storage import CSVStorage, JSONStorage, SQLBackupStorage

__all__ = [
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
    "current_user",
    "PasswordSecurity",
    "hash_password",
    "verify_password",
    "CSVStorage",
    "JSONStorage",
    "SQLBackupStorage"
]
