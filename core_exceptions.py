"""
Core Custom Exceptions for AIMS Main Application.
Fulfills Project Requirement: Exception Handling (Custom Exceptions, Invalid Input, Empty Fields, File Errors, Invalid Data Types).
"""


class AIMSException(Exception):
    """Base exception for all AIMS system errors."""
    def __init__(self, message: str, error_code: str = "AIMS_ERR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self):
        return f"[{self.error_code}] {self.message}"


class ValidationError(AIMSException):
    """Raised when data validation fails."""
    def __init__(self, message: str, field_name: str = None):
        super().__init__(message, error_code="VALIDATION_ERR")
        self.field_name = field_name


class EmptyFieldException(ValidationError):
    """Raised when required fields are blank."""
    def __init__(self, message: str = "All required fields must be answered.", field_name: str = None):
        super().__init__(message, field_name=field_name)
        self.error_code = "EMPTY_FIELD_ERR"


class InvalidDataTypeException(ValidationError):
    """Raised when data type or format is invalid."""
    def __init__(self, message: str = "Invalid data format or value provided.", field_name: str = None):
        super().__init__(message, field_name=field_name)
        self.error_code = "INVALID_TYPE_ERR"


class AuthenticationException(AIMSException):
    """Raised when login or credentials verification fails."""
    def __init__(self, message: str = "Authentication failed. Invalid credentials or permissions."):
        super().__init__(message, error_code="AUTH_ERR")


class DatabaseOperationException(AIMSException):
    """Raised on database query or connection failure."""
    def __init__(self, message: str = "A database error occurred."):
        super().__init__(message, error_code="DB_OPERATION_ERR")


class FileStorageException(AIMSException):
    """Raised on file load/save error."""
    def __init__(self, message: str = "A file storage error occurred."):
        super().__init__(message, error_code="FILE_STORAGE_ERR")
