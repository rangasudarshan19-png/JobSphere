"""
Database migration to add notification tables
Run this script to add notification and notification_preferences tables
"""
import sqlite3
import os
from pathlib import Path

# Get database path
db_path = Path(__file__).parent.parent / "job_tracker.db"

print(f"[EMOJI] Migrating database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tables already exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
    if cursor.fetchone():
        print("[SYMBOL]️  Notifications table already exists, skipping...")
    else:
        # Create notifications table
        cursor.execute("""
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(200) NOT NULL,
            message TEXT,
            application_id INTEGER,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP,
            email_sent BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
        )
        """)
        print("[SYMBOL] Created notifications table")
        
        # Create index for better query performance
        cursor.execute("""
        CREATE INDEX idx_notifications_user_id ON notifications(user_id)
        """)
        cursor.execute("""
        CREATE INDEX idx_notifications_read_at ON notifications(read_at)
        """)
        print("[SYMBOL] Created notifications indexes")
    
    # Check if notification_preferences table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notification_preferences'")
    if cursor.fetchone():
        print("[SYMBOL]️  Notification preferences table already exists, skipping...")
    else:
        # Create notification_preferences table
        cursor.execute("""
        CREATE TABLE notification_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            email_enabled BOOLEAN DEFAULT 1,
            email_verified BOOLEAN DEFAULT 0,
            status_change BOOLEAN DEFAULT 1,
            interview_reminders BOOLEAN DEFAULT 1,
            follow_up_reminders BOOLEAN DEFAULT 1,
            offer_notifications BOOLEAN DEFAULT 1,
            weekly_summary BOOLEAN DEFAULT 1,
            email_frequency VARCHAR(20) DEFAULT 'instant',
            quiet_hours_enabled BOOLEAN DEFAULT 0,
            quiet_hours_start TIME,
            quiet_hours_end TIME,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        print("[SYMBOL] Created notification_preferences table")
        
        # Create index
        cursor.execute("""
        CREATE INDEX idx_notification_prefs_user_id ON notification_preferences(user_id)
        """)
        print("[SYMBOL] Created notification_preferences index")
    
    # Commit changes
    conn.commit()
    print("\n[EMOJI] Database migration completed successfully!")
    print("\n[EMOJI] New tables added:")
    print("   • notifications")
    print("   • notification_preferences")
    print("\n[SYMBOL] Your database is ready for email notifications!")
    
except sqlite3.Error as e:
    print(f"\n[SYMBOL] Migration failed: {e}")
    conn.rollback()
    
finally:
    conn.close()

print("\n" + "="*50)
print("Next steps:")
print("1. Restart your FastAPI server")
print("2. Test the notification endpoints at http://localhost:8080/docs")
print("3. Send a test email to verify SMTP configuration")
print("="*50)
