"""
Migration: Add admin features - audit logs, settings, announcements
Adds is_suspended field to users table
"""
import sqlite3
from pathlib import Path


def upgrade():
    """Apply migration"""
    # The actual database is job_tracker.db in the root of python-service
    db_path = Path(__file__).parent.parent / "job_tracker.db"
    
    print(f"Using database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 1. Add is_suspended column to users table
        cursor.execute("""
            ALTER TABLE users ADD COLUMN is_suspended INTEGER DEFAULT 0
        """)
        print("[SYMBOL] Added is_suspended to users table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("[SYMBOL] is_suspended already exists")
        else:
            raise
    
    try:
        # 2. Create admin_audit_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                ip_address TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users(id)
            )
        """)
        print("[SYMBOL] Created admin_audit_log table")
    except sqlite3.OperationalError as e:
        print(f"[SYMBOL] admin_audit_log: {e}")
    
    try:
        # 3. Create admin_settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                category TEXT,
                updated_by INTEGER,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        """)
        print("[SYMBOL] Created admin_settings table")
    except sqlite3.OperationalError as e:
        print(f"[SYMBOL] admin_settings: {e}")
    
    try:
        # 4. Create announcements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        print("[SYMBOL] Created announcements table")
    except sqlite3.OperationalError as e:
        print(f"[SYMBOL] announcements: {e}")
    
    try:
        # 5. Create admin_notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                read_at DATETIME,
                FOREIGN KEY (recipient_id) REFERENCES users(id),
                FOREIGN KEY (sender_id) REFERENCES users(id)
            )
        """)
        print("[SYMBOL] Created admin_notifications table")
    except sqlite3.OperationalError as e:
        print(f"[SYMBOL] admin_notifications: {e}")
    
    conn.commit()
    conn.close()
    print("\n[SYMBOL] Migration completed successfully")


if __name__ == "__main__":
    upgrade()
