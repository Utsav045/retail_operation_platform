"""
Database Migration Script: Add Soft Delete columns and indexes to all tables.
Ensures zero data loss while upgrading all tables with is_deleted and deleted_at.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "retail_ops.db")

TABLES = [
    "stores",
    "devices",
    "staff",
    "departments",
    "tax_groups",
    "items",
    "business_accounts",
    "transactions",
    "transaction_lines",
    "transaction_tenders",
    "transaction_taxes",
    "gift_card_activities",
    "cash_drops",
    "shift_summaries",
    "end_of_day_summaries",
    "file_import_logs",
    "quarantined_files",
    "security_audit_logs",
    "users",
]


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}, skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Starting Soft Delete migration on {DB_PATH}...")
    for table in TABLES:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            print(f"Table '{table}' does not exist, skipping.")
            continue

        # Get existing columns
        cursor.execute(f"PRAGMA table_info({table})")
        existing_cols = [row[1] for row in cursor.fetchall()]

        # Add is_deleted
        if "is_deleted" not in existing_cols:
            print(f"Adding is_deleted column to '{table}'...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN is_deleted BOOLEAN DEFAULT 0 NOT NULL")
            cursor.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_is_deleted ON {table} (is_deleted)")
        else:
            print(f"Column is_deleted already exists on '{table}'.")

        # Add deleted_at
        if "deleted_at" not in existing_cols:
            print(f"Adding deleted_at column to '{table}'...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at TIMESTAMP NULL")
            cursor.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_deleted_at ON {table} (deleted_at)")
        else:
            print(f"Column deleted_at already exists on '{table}'.")

    conn.commit()
    conn.close()
    print("Soft Delete migration completed successfully!")


if __name__ == "__main__":
    migrate()
