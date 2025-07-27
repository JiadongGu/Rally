"""
Database utilities for the Rallypoint application.

This module encapsulates all direct interactions with the SQLite database.
It exposes helper functions to initialize the database schema and provide
connections in a context-managed fashion.

Tables
------
service_requests
    Stores all client service submissions. Fields:
        id INTEGER PRIMARY KEY AUTOINCREMENT
        name TEXT NOT NULL
        email TEXT NOT NULL
        description TEXT NOT NULL
        created_at TEXT (ISO-8601 timestamp)

job_postings
    Stores job postings created by admins. Fields:
        id INTEGER PRIMARY KEY AUTOINCREMENT
        title TEXT NOT NULL
        description TEXT NOT NULL
        created_at TEXT (ISO-8601 timestamp)
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


# Name of the SQLite database file.
DB_NAME = "rallypoint.db"


def init_db() -> None:
    """Initialise the SQLite database and create tables if they don't exist.

    This function should be called once at application startup. It creates
    the required tables for service requests and job postings. The database
    file lives in the root of the repository by default.
    """
    db_path = Path(DB_NAME)
    # Ensure the database directory exists (it's the project root, so fine).
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Create service_requests table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS service_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # Create job_postings table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS job_postings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def reset_data() -> None:
    """Clear all existing data from the database tables.

    This helper deletes every row from the ``service_requests`` and
    ``job_postings`` tables. It can be used at application startup to ensure
    that each run of the development server begins with an empty board. It is
    intended for demonstration purposes and should not be used in production.
    """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM service_requests")
        cursor.execute("DELETE FROM job_postings")
        conn.commit()


@contextmanager
def get_db() -> sqlite3.Connection:
    """Context manager for obtaining a SQLite database connection.

    Usage:
        with get_db() as conn:
            cursor = conn.cursor()
            ...

    Ensures the connection is properly closed after use.
    """
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()