"""
Database Management Module.
Encapsulates database connectivity, configuration, connection pooling, and schema initialization.
"""
import pymysql
from typing import Optional, Tuple, Any
from .exceptions import DatabaseOperationException
import auth
from core_exceptions import DatabaseOperationException as _AuthDBError
from shipping_schema import ensure_shipping_schema, ensure_recipient_schema


class DatabaseConfig:
    """Encapsulates database configuration parameters."""
    def __init__(self, host: str = None, user: str = None, password: str = None, database: str = None, port: int = 3306):
        self._host = host or auth.DB_CONFIG["host"]
        self._user = user or auth.DB_CONFIG["user"]
        self._password = password if password is not None else auth.DB_CONFIG["password"]
        self._database = database or auth.DB_CONFIG["database"]
        self._port = port

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

    @property
    def port(self) -> int:
        return self._port

_DEFAULT_CONFIG = DatabaseConfig()

class DatabaseManager:
    """
    Singleton Database Manager class.
    Provides encapsulated methods to connect, execute queries, and initialize tables.
    """
    _instance: Optional["DatabaseManager"] = None
    _config: DatabaseConfig = _DEFAULT_CONFIG

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def set_config(cls, config: DatabaseConfig) -> None:
        """Update database configuration."""
        cls._config = config

    @classmethod
    def get_connection(cls, select_db: bool = True) -> pymysql.Connection:
        """
        Creates and returns a new MySQL database connection.
        Raises DatabaseOperationException if connection fails.
        """
        try:
            if select_db and cls._config is _DEFAULT_CONFIG:
                return auth.get_connection()           
            kwargs = {
                "host": cls._config.host,
                "user": cls._config.user,
                "password": cls._config.password,
                "port": cls._config.port,
                "autocommit": False
            }
            if select_db:
                kwargs["database"] = cls._config.database

            connection = pymysql.connect(**kwargs)
            return connection
        except pymysql.MySQLError as err:
            raise DatabaseOperationException(f"Database connectivity issue: {err}")

    @classmethod
    def get_cursor_and_connection(cls, select_db: bool = True) -> Tuple[Any, pymysql.Connection]:
        """Convenience method returning (cursor, connection)."""
        connection = cls.get_connection(select_db=select_db)
        cursor = connection.cursor()
        return cursor, connection

    @classmethod
    def initialize_database(cls) -> None:
        """
        Ensures the database and all required tables exist.
        Tables: employee_data, products, recipient_data, shipping_orders, sales.
        """
        try:
            # 1. Connect without selecting db to ensure database exists
            connection = cls.get_connection(select_db=False)
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{cls._config.database}`")
            connection.commit()
            cursor.close()
            connection.close()

            # 2. Connect to the database and initialize all tables
            connection = cls.get_connection(select_db=True)
            cursor = connection.cursor()

            # Employee table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employee_data (
                    empid INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    sex VARCHAR(20),
                    dob DATE,
                    contact VARCHAR(10),
                    employment_type VARCHAR(50),
                    work_shift VARCHAR(50),
                    address VARCHAR(255),
                    dj DATE,
                    salary DECIMAL(10, 2),
                    role VARCHAR(50),
                    password VARCHAR(255)
                )
            """)

            # Products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    category VARCHAR(100),
                    price DECIMAL(10,2) NOT NULL,
                    quantity INT NOT NULL DEFAULT 0,
                    image_path VARCHAR(500) NULL
                )
            """)

            # Ensure image_path exists in products
            cursor.execute("SHOW COLUMNS FROM products LIKE 'image_path'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE products ADD COLUMN image_path VARCHAR(500) NULL")

            # Recipient table
            ensure_recipient_schema(cursor)

            # Ensure address and description exist in recipient_data
            cursor.execute("SHOW COLUMNS FROM recipient_data LIKE 'address'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE recipient_data ADD COLUMN address TEXT NULL")
            cursor.execute("SHOW COLUMNS FROM recipient_data LIKE 'description'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE recipient_data ADD COLUMN description TEXT NULL")

            # Shipping orders table
            ensure_shipping_schema(cursor)

            # Sales table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NULL,
                    product_name VARCHAR(100) NOT NULL,
                    category VARCHAR(100) NULL,
                    quantity INT NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    total DECIMAL(10,2) NOT NULL,
                    sale_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            connection.commit()
            cursor.close()
            connection.close()

        except pymysql.MySQLError as err:
            raise DatabaseOperationException(f"Failed to initialize database tables: {err}")
