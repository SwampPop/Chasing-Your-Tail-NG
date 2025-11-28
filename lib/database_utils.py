"""
Centralized database utilities for CYT
Provides common database initialization and schema management patterns
"""
import sqlite3
import os
import logging
from typing import Callable, Optional, Dict, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseInitError(Exception):
    """Raised when database initialization fails"""
    pass


class DatabaseSchema:
    """Represents a database schema definition"""

    def __init__(self, db_name: str, tables: Dict[str, str]):
        """
        Initialize a database schema.

        Args:
            db_name: Name of the database file (e.g., 'watchlist.db')
            tables: Dict mapping table names to CREATE TABLE SQL statements
        """
        self.db_name = db_name
        self.tables = tables
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            db_name
        )

    def initialize(self) -> None:
        """Initialize the database with defined schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for table_name, create_sql in self.tables.items():
                    cursor.execute(create_sql)
                conn.commit()
                logger.info(f"Database '{self.db_name}' initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database '{self.db_name}': {e}")
            raise DatabaseInitError(f"Failed to initialize {self.db_name}: {e}") from e


@contextmanager
def safe_db_connection(db_path: str):
    """
    Context manager for safe database connections.

    Args:
        db_path: Path to the database file

    Yields:
        sqlite3.Connection: Database connection

    Raises:
        sqlite3.Error: If connection or operations fail
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_safe_query(
        db_path: str,
        query: str,
        params: tuple = (),
        fetch_mode: str = 'all') -> Optional[List]:
    """
    Execute a query safely with proper error handling.

    Args:
        db_path: Path to the database
        query: SQL query to execute
        params: Query parameters for parameterized queries
        fetch_mode: 'all', 'one', or 'none' (for INSERT/UPDATE)

    Returns:
        Query results based on fetch_mode, or None for fetch_mode='none'

    Raises:
        sqlite3.Error: If query execution fails
    """
    try:
        with safe_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if fetch_mode == 'all':
                return cursor.fetchall()
            elif fetch_mode == 'one':
                return cursor.fetchone()
            else:  # fetch_mode == 'none'
                return None

    except sqlite3.Error as e:
        logger.error(f"Query execution failed: {query}, params: {params}, error: {e}")
        raise


# Define common schemas
HISTORY_SCHEMA = DatabaseSchema(
    db_name='cyt_history.db',
    tables={
        'devices': '''
            CREATE TABLE IF NOT EXISTS devices (
                mac TEXT PRIMARY KEY,
                first_seen REAL,
                last_seen REAL
            )
        ''',
        'appearances': '''
            CREATE TABLE IF NOT EXISTS appearances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT,
                timestamp REAL,
                location_id TEXT,
                FOREIGN KEY (mac) REFERENCES devices (mac)
            )
        '''
    }
)

WATCHLIST_SCHEMA = DatabaseSchema(
    db_name='watchlist.db',
    tables={
        'devices': '''
            CREATE TABLE IF NOT EXISTS devices (
                mac TEXT PRIMARY KEY,
                alias TEXT NOT NULL,
                device_type TEXT,
                notes TEXT
            )
        '''
    }
)
