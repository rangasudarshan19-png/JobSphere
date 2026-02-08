"""
Database migration: Add next_phase_date and next_phase_type to applications table
"""
import sqlite3
import os

# Get database path
db_path = os.path.join(os.path.dirname(__file__), "..", "job_tracker.db")

print("=" * 70)
print("[EMOJI] ADDING NEXT PHASE TRACKING TO APPLICATIONS")
print("=" * 70)
print(f"\n[EMOJI] Database: {db_path}\n")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(applications)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'next_phase_date' in columns:
        print("[SYMBOL]️  next_phase_date column already exists")
    else:
        # Add next_phase_date column
        cursor.execute("""
            ALTER TABLE applications 
            ADD COLUMN next_phase_date DATE
        """)
        print("[SYMBOL] Added next_phase_date column")
    
    if 'next_phase_type' in columns:
        print("[SYMBOL]️  next_phase_type column already exists")
    else:
        # Add next_phase_type column
        cursor.execute("""
            ALTER TABLE applications 
            ADD COLUMN next_phase_type VARCHAR(100)
        """)
        print("[SYMBOL] Added next_phase_type column")
    
    # Commit changes
    conn.commit()
    
    print("\n" + "=" * 70)
    print("[EMOJI] MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("\n[EMOJI] New columns added to applications table:")
    print("   • next_phase_date  - Store date of next interview/assessment")
    print("   • next_phase_type  - Store type (e.g., 'Technical Interview')")
    print("\n[SYMBOL] Applications can now track upcoming phases!")
    print("\n" + "=" * 70)
    print("Next steps:")
    print("1. Update add-application form to include next phase date")
    print("2. Create AI-powered reminder emails")
    print("3. Set up daily scheduler for reminders")
    print("=" * 70)
    
except sqlite3.Error as e:
    print(f"\n[SYMBOL] Migration failed: {e}")
    conn.rollback()
    
finally:
    conn.close()
