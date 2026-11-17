"""
Custom Exceptions Module for AIMS (Admin Inventory Management System).
Fulfills Project Requirement: Exception Handling (Custom Exceptions, Invalid Input, Empty Fields, File Errors, Invalid Data Types).
"""


class AIMSException(Exception):
    """Base exception class for all custom application errors."""
    def __init__(self, message: str, error_code: str = "AIMS_ERR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self):
        return f"[{self.error_code}] {self.message}"


class ValidationError(AIMSException):
    """Base exception raised when input validation fails."""
    def __init__(self, message: str, field_name: str = None):
        super().__init__(message, error_code="VALIDATION_ERR")
        self.field_name = field_name


class EmptyFieldException(ValidationError):
    """Raised when one or more required input fields are left blank."""
    def __init__(self, message: str = "All required fields must be answered.", field_name: str = None):
        super().__init__(message, field_name=field_name)
        self.error_code = "EMPTY_FIELD_ERR"


class InvalidDataTypeException(ValidationError):
    """Raised when an input value cannot be converted or violates type constraints (e.g. non-numeric contact, negative salary)."""
    def __init__(self, message: str = "Invalid data type or format provided.", field_name: str = None):
        super().__init__(message, field_name=field_name)
        self.error_code = "INVALID_TYPE_ERR"


class DuplicateRecordException(AIMSException):
    """Raised when attempting to insert or update a record with unique constraints that already exists."""
    def __init__(self, message: str = "A record with these details already exists."):
        super().__init__(message, error_code="DUPLICATE_RECORD_ERR")


class RecordNotFoundException(AIMSException):
    """Raised when a specified record or row is not found in the database or table."""
    def __init__(self, message: str = "The requested record was not found or row is not selected."):
        super().__init__(message, error_code="RECORD_NOT_FOUND_ERR")


class FileStorageException(AIMSException):
    """Raised when file reading, writing, parsing, or backup/restore operations fail."""
    def __init__(self, message: str = "An error occurred during file save or load operations."):
        super().__init__(message, error_code="FILE_STORAGE_ERR")


class DatabaseOperationException(AIMSException):
    """Raised when a database query or connection fails."""
    def __init__(self, message: str = "A database error occurred."):
        super().__init__(message, error_code="DB_OPERATION_ERR")


class AuthenticationException(AIMSException):
    """Raised when authentication or authorization fails (e.g. wrong password or unauthorized role)."""
    def __init__(self, message: str = "Authentication failed or insufficient permissions."):
        super().__init__(message, error_code="AUTH_ERR")
