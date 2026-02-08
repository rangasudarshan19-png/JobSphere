from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    is_admin = Column(Integer, default=0)  # 0 = regular user, 1 = admin
    is_suspended = Column(Integer, default=0)  # 0 = active, 1 = suspended
    first_login = Column(Integer, default=1)  # 1 = first login, 0 = not first login
    resume_data = Column(Text, nullable=True)  # JSON string storing resume data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    notification_preferences = relationship("NotificationPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    enhanced_resumes = relationship("EnhancedResume", back_populates="user", cascade="all, delete-orphan")
    matched_jobs = relationship("MatchedJob", back_populates="user", cascade="all, delete-orphan")
    job_preferences = relationship("UserJobPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
