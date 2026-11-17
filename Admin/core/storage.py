"""
File Storage and Data Persistence Module.
Demonstrates:
- Inheritance (BaseFileStorage -> CSVStorage, JSONStorage, SQLBackupStorage)
- Polymorphism (Overriding save() and load() across distinct storage formats)
- Exception Handling (Handling FileNotFoundError, PermissionError, JSONDecodeError, FileStorageException)
- Functional Features: Save Data, Load Data
"""
import os
import csv
import json
from typing import List, Dict, Any
from datetime import datetime
from .interfaces import IDataStorage
from .exceptions import FileStorageException


class BaseFileStorage(IDataStorage):
    """
    Abstract base class for file-based persistence.
    Demonstrates Inheritance from IDataStorage.
    """
    def __init__(self, default_extension: str):
        self._default_extension = default_extension

    @property
    def default_extension(self) -> str:
        return self._default_extension

    def _ensure_directory(self, file_path: str) -> None:
        """Helper to ensure the parent folder exists."""
        directory = os.path.dirname(os.path.abspath(file_path))
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as err:
                raise FileStorageException(f"Failed to create directory '{directory}': {err}")


class CSVStorage(BaseFileStorage):
    """
    Handles saving and loading data in CSV format.
    Demonstrates Polymorphism by overriding save() and load().
    """
    def __init__(self):
        super().__init__(default_extension=".csv")

    def save(self, data: List[Dict[str, Any]], file_path: str) -> int:
        """
        Saves a list of dictionaries to a CSV file.
        Raises FileStorageException on file or permission errors.
        """
        if not data:
            raise FileStorageException("No data provided to save.")

        self._ensure_directory(file_path)

        try:
            fieldnames = list(data[0].keys())
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            return len(data)
        except PermissionError:
            raise FileStorageException(f"Permission denied when writing to file: {file_path}")
        except OSError as err:
            raise FileStorageException(f"Failed to write CSV file: {err}")

    def load(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Loads records from a CSV file into a list of dictionaries.
        Raises FileStorageException on missing file or read errors.
        """
        if not os.path.isfile(file_path):
            raise FileStorageException(f"File not found: {file_path}")

        try:
            with open(file_path, mode="r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                records = [dict(row) for row in reader]
            return records
        except PermissionError:
            raise FileStorageException(f"Permission denied when reading file: {file_path}")
        except csv.Error as err:
            raise FileStorageException(f"Malformed CSV file format: {err}")
        except OSError as err:
            raise FileStorageException(f"Failed to read CSV file: {err}")


class JSONStorage(BaseFileStorage):
    """
    Handles saving and loading data in JSON format.
    Demonstrates Polymorphism by overriding save() and load().
    """
    def __init__(self):
        super().__init__(default_extension=".json")

    def save(self, data: List[Dict[str, Any]], file_path: str) -> int:
        """Saves a list of dictionaries to a JSON file."""
        if not data:
            raise FileStorageException("No data provided to save.")

        self._ensure_directory(file_path)

        try:
            # Custom JSON serializer for dates and decimals
            def default_serializer(obj):
                if hasattr(obj, "isoformat"):
                    return obj.isoformat()
                return str(obj)

            with open(file_path, mode="w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, default=default_serializer)
            return len(data)
        except PermissionError:
            raise FileStorageException(f"Permission denied when writing to file: {file_path}")
        except OSError as err:
            raise FileStorageException(f"Failed to write JSON file: {err}")

    def load(self, file_path: str) -> List[Dict[str, Any]]:
        """Loads records from a JSON file."""
        if not os.path.isfile(file_path):
            raise FileStorageException(f"File not found: {file_path}")

        try:
            with open(file_path, mode="r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, list):
                raise FileStorageException("Invalid JSON format: expected a list of records.")
            return data
        except json.JSONDecodeError as err:
            raise FileStorageException(f"Corrupted or invalid JSON data: {err}")
        except OSError as err:
            raise FileStorageException(f"Failed to read JSON file: {err}")


class SQLBackupStorage(BaseFileStorage):
    """
    Handles SQL Database Backup and Restore statements.
    Demonstrates Polymorphism for raw database dump files.
    """
    def __init__(self):
        super().__init__(default_extension=".sql")

    def save(self, data: Any, file_path: str) -> int:
        """
        Saves SQL statements or structured dump string to a .sql backup file.
        """
        self._ensure_directory(file_path)
        try:
            content = data if isinstance(data, str) else "\n".join(str(item) for item in data)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)
            return 1
        except OSError as err:
            raise FileStorageException(f"Failed to write SQL backup file: {err}")

    def load(self, file_path: str) -> List[str]:
        """
        Parses a .sql backup file into individual executable SQL statements.
        """
        if not os.path.isfile(file_path):
            raise FileStorageException(f"Backup file not found: {file_path}")

        statements = []
        buffer = []
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                header = file.readline()
                if not header.startswith("-- AIMS backup"):
                    raise FileStorageException("Invalid AIMS backup file header.")

                file.seek(0)
                for line in file:
                    line = line.rstrip("\n")
                    if not buffer and (line.strip() == "" or line.startswith("--")):
                        continue
                    buffer.append(line)
                    if line.rstrip().endswith(";"):
                        statements.append("\n".join(buffer).rstrip().rstrip(";"))
                        buffer = []
            return statements
        except OSError as err:
            raise FileStorageException(f"Failed to read SQL backup file: {err}")
