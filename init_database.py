"""Initialize the AgriNext SQLite schema without seeding demo or user data.

Run from the backend directory:
    python init_database.py

Set AGRINEXT_DB_PATH to choose a non-default database location.
"""
from database import DB_PATH, init_db


if __name__ == "__main__":
    init_db()
    print(f"AgriNext database schema initialized at: {DB_PATH}")
