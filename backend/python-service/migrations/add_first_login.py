"""
Migration: Add first_login flag to track new vs returning users
"""
import sqlite3
from pathlib import Path


def upgrade():
    """Apply migration"""
    db_path = Path(__file__).parent.parent / "job_tracker.db"
    
    print(f"Using database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Add first_login column to users table
        cursor.execute("""
            ALTER TABLE users ADD COLUMN first_login INTEGER DEFAULT 0
        """)
        print("[SYMBOL] Added first_login to users table")
        
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("[SYMBOL] first_login already exists")
        else:
            raise
    finally:
        conn.close()


def downgrade():
    """Revert migration"""
    db_path = Path(__file__).parent.parent / "job_tracker.db"
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Note: SQLite doesn't support DROP COLUMN easily, so we skip it
        print("[SYMBOL] Downgrade not supported for SQLite")
    finally:
        conn.close()


if __name__ == "__main__":
    upgrade()
    print("Migration completed!")
