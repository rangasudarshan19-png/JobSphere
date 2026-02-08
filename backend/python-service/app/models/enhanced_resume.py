from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base


class EnhancedResume(Base):
    """Store AI-enhanced resumes with extracted profile data"""
    __tablename__ = "enhanced_resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Resume content
    original_resume_text = Column(Text, nullable=True)
    enhanced_resume_text = Column(Text, nullable=False)
    resume_file_path = Column(String(500), nullable=True)  # Path to stored PDF/DOCX
    
    # Extracted profile for matching (stored as JSON)
    skills = Column(Text, nullable=True)  # JSON array: ["Python", "Selenium", "API Testing"]
    experience_years = Column(Integer, nullable=True)
    job_titles = Column(Text, nullable=True)  # JSON array: ["QA Engineer", "Software Tester"]
    location_preference = Column(String(255), nullable=True)
    education = Column(Text, nullable=True)  # JSON array
    certifications = Column(Text, nullable=True)  # JSON array
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Integer, default=1)  # Allow multiple resume versions, mark active one
    
    # Relationships
    user = relationship("User", back_populates="enhanced_resumes")
    matched_jobs = relationship("MatchedJob", back_populates="resume", cascade="all, delete-orphan")


class MatchedJob(Base):
    """Store cached job matches for user resumes"""
    __tablename__ = "matched_jobs"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("enhanced_resumes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Job details
    job_id = Column(String(255), nullable=True, index=True)  # External job ID from API
    job_title = Column(String(500), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    salary_range = Column(String(100))
    job_type = Column(String(50))  # Full-time, Part-time, Contract, etc.
    description = Column(Text)
    requirements = Column(Text)
    external_url = Column(String(1000), nullable=False)  # Link to apply
    source = Column(String(100))  # Indeed, LinkedIn, Glassdoor, etc.
    
    # Matching data
    match_score = Column(Integer, nullable=False, index=True)  # 0-100
    matching_skills = Column(Text)  # JSON array: ["Python", "Selenium"]
    missing_skills = Column(Text)  # JSON array: ["AWS", "Docker"]
    match_reason = Column(Text)  # AI explanation of why this matches
    
    # Application tracking
    is_applied = Column(Integer, default=0)
    is_saved = Column(Integer, default=0)
    applied_date = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Job posts expire
    
    # Relationships
    resume = relationship("EnhancedResume", back_populates="matched_jobs")
    user = relationship("User", back_populates="matched_jobs")


class UserJobPreferences(Base):
    """Store user's job search preferences"""
    __tablename__ = "user_job_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Search preferences
    preferred_job_titles = Column(Text)  # JSON array: ["QA Engineer", "Test Automation Engineer"]
    preferred_locations = Column(Text)  # JSON array: ["Bangalore", "Remote"]
    min_salary = Column(Integer, nullable=True)
    max_salary = Column(Integer, nullable=True)
    job_types = Column(Text)  # JSON array: ["Full-time", "Contract"]
    remote_preference = Column(String(50))  # "only", "hybrid", "no_preference", "office_only"
    
    # Matching settings
    min_match_score = Column(Integer, default=80)  # 0-100, default 80%
    email_alerts_enabled = Column(Integer, default=1)
    alert_frequency = Column(String(50), default="daily")  # daily, weekly, instant
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="job_preferences")

