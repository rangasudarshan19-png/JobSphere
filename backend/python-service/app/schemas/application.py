from pydantic import BaseModel, HttpUrl, Field
from datetime import date, datetime, time
from typing import Optional


class CompanyBase(BaseModel):
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationBase(BaseModel):
    job_title: str
    job_description: Optional[str] = None
    job_url: Optional[str] = None
    status: str = "applied"
    salary_range: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    applied_date: date = Field(default_factory=date.today)
    deadline: Optional[date] = None
    notes: Optional[str] = None
    next_phase_date: Optional[date] = None
    next_phase_type: Optional[str] = None
    interview_date: Optional[date] = None
    interview_time: Optional[time] = None
    interview_details: Optional[str] = None
    send_notifications: bool = True


class ApplicationCreate(ApplicationBase):
    company_id: Optional[int] = None
    company_name: Optional[str] = None  # If company doesn't exist, we'll create it


class ApplicationUpdate(BaseModel):
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    job_url: Optional[str] = None
    status: Optional[str] = None
    salary_range: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    applied_date: Optional[date] = None
    deadline: Optional[date] = None
    notes: Optional[str] = None
    interview_date: Optional[date] = None
    interview_time: Optional[time] = None
    interview_details: Optional[str] = None
    send_notifications: Optional[bool] = None


class ApplicationResponse(ApplicationBase):
    id: int
    user_id: int
    company_id: Optional[int]
    company: Optional[CompanyResponse] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
