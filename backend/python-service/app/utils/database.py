from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Database URL - Use absolute path for SQLite to ensure consistency
# Default to database folder in project root
project_root = Path(__file__).parent.parent.parent.parent
database_dir = project_root / "database"
database_dir.mkdir(exist_ok=True)  # Ensure directory exists
default_db_path = database_dir / "job_tracker.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")

# Database info (using plain text for Windows terminal compatibility)
print(f"Database URL: {DATABASE_URL}")
print(f"Database location: {default_db_path if 'sqlite' in DATABASE_URL else 'PostgreSQL'}")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
