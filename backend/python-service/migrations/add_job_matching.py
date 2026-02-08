"""
Migration script to add Job Matching feature tables:
- enhanced_resumes: Store AI-enhanced resumes with extracted skills
- matched_jobs: Cache job search results with match scores
- user_job_preferences: Store user's job search preferences
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.application import Application, Company
from app.models.notification import Notification, NotificationPreferences
from app.models.enhanced_resume import EnhancedResume, MatchedJob, UserJobPreferences

print("[EMOJI] Starting Job Matching feature migration...")
print("=" * 60)

try:
    # Create all tables (will only create new ones, existing tables are unchanged)
    print("\n[EMOJI] Creating new tables...")
    Base.metadata.create_all(bind=engine)
    
    print("[SYMBOL] enhanced_resumes table created")
    print("[SYMBOL] matched_jobs table created")
    print("[SYMBOL] user_job_preferences table created")
    
    # Verify tables exist
    print("\n[EMOJI] Verifying tables...")
    db = SessionLocal()
    
    try:
        # Check if we can query new tables
        resume_count = db.query(EnhancedResume).count()
        job_count = db.query(MatchedJob).count()
        pref_count = db.query(UserJobPreferences).count()
        
        print(f"[SYMBOL] enhanced_resumes: {resume_count} records")
        print(f"[SYMBOL] matched_jobs: {job_count} records")
        print(f"[SYMBOL] user_job_preferences: {pref_count} records")
        
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("[SYMBOL] Migration completed successfully!")
    print("\n[EMOJI] New features available:")
    print("  • Save AI-enhanced resumes")
    print("  • Extract skills and profile from resumes")
    print("  • Search and match jobs with AI")
    print("  • Track matched jobs with 80%+ scores")
    print("  • Set job search preferences")
    print("\n[EMOJI] Next steps:")
    print("  1. Restart the backend server")
    print("  2. Test resume enhancement")
    print("  3. Try job matching feature")
    
except Exception as e:
    print(f"\n[SYMBOL] Migration failed: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

