from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Time, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    website = Column(String(255))
    industry = Column(String(100))
    location = Column(String(255))
    logo_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    applications = relationship("Application", back_populates="company")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"))
    job_title = Column(String(255), nullable=False)
    job_description = Column(Text)
    job_url = Column(String(500))
    status = Column(String(50), default="applied")  # applied, screening, interview_scheduled, interviewed, offer, rejected
    salary_range = Column(String(100))
    location = Column(String(255))
    job_type = Column(String(50))  # Full-time, Part-time, Contract, Internship
    applied_date = Column(Date, nullable=False)
    deadline = Column(Date)
    next_phase_date = Column(Date)  # Date of next interview/assessment/round
    next_phase_type = Column(String(100))  # e.g., "Technical Interview", "HR Round", "Assessment"
    interview_date = Column(Date)  # Interview date
    interview_time = Column(Time)  # Interview time
    interview_details = Column(Text)  # Zoom link, interviewer name, etc.
    send_notifications = Column(Boolean, default=True)  # Whether to send email notifications
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="applications")
    company = relationship("Company", back_populates="applications")
    notifications = relationship("Notification", back_populates="application", cascade="all, delete-orphan")
