"""
Database module for the Rallypoint web application.

This module provides helper functions to initialize the SQLite database and
establish connections. It ensures that the required tables exist before
the application begins serving requests. Tables include:

* ``projects`` – stores client submissions with fields for name, email,
  project title, description, status and a timestamp. The ``status``
  defaults to ``Pending``.
* ``postings`` – stores admin-created job postings visible to
  freelancers. Each posting has a title, description and a timestamp.

The database is persisted to a file named ``rallypoint.db`` in the
application root. SQLite is used because it requires no external
services and is sufficient for an MVP.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


# Path to the SQLite database file. It lives alongside the Python
# modules in the rallypoint package. Using a relative path keeps the
# database portable and self‑contained.
DB_PATH = Path(__file__).resolve().parent / "rallypoint.db"


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row factory set to Row.

    SQLite connections are not thread‑safe by default, so the
    ``check_same_thread`` flag is disabled to allow FastAPI to use the
    connection across different workers. Each call returns a new
    connection; callers should close the connection when finished.

    Returns:
        sqlite3.Connection: A connection object configured for row
        access by column name.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create database tables if they do not already exist.

    This function executes ``CREATE TABLE IF NOT EXISTS`` statements for
    the ``projects`` and ``postings`` tables. It is safe to call this
    function multiple times; the tables will only be created once. Any
    schema changes should be handled via migrations in a more mature
    version of the application.
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Create the projects table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
        """
    )
    # Create the postings table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS postings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            posted_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_project(name: str, email: str, title: str, description: str) -> None:
    """Insert a new project submission into the database.

    Args:
        name: Client's name.
        email: Client's email address.
        title: Project title.
        description: Project description.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO projects (name, email, title, description, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, email, title, description, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_all_projects() -> list[sqlite3.Row]:
    """Retrieve all project submissions ordered by newest first.

    Returns:
        A list of SQLite Row objects representing project entries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM projects
        ORDER BY datetime(created_at) DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_posting(title: str, description: str) -> None:
    """Insert a new job posting into the database.

    Args:
        title: Title of the freelance opportunity.
        description: Detailed description of the opportunity.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO postings (title, description, posted_at)
        VALUES (?, ?, ?)
        """,
        (title, description, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_all_postings() -> list[sqlite3.Row]:
    """Retrieve all job postings ordered by newest first.

    Returns:
        A list of SQLite Row objects representing job postings.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM postings
        ORDER BY datetime(posted_at) DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return rows