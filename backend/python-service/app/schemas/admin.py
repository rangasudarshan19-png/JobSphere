"""
Admin request/response schemas
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


# ============ USER MANAGEMENT SCHEMAS ============

class UserSearchParams(BaseModel):
    """Query params for user search"""
    email: Optional[str] = None
    name: Optional[str] = None
    is_admin: Optional[int] = None
    is_suspended: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class UserActivityResponse(BaseModel):
    """User activity summary"""
    user_id: int
    email: str
    full_name: str
    is_admin: bool
    is_suspended: bool
    created_at: datetime
    application_count: int
    last_login: Optional[datetime] = None


class AdminMessageRequest(BaseModel):
    """Send message to user"""
    message: str
    recipient_id: int


# ============ APPLICATION MANAGEMENT SCHEMAS ============

class ApplicationFlagRequest(BaseModel):
    """Flag an application as suspicious"""
    reason: str
    severity: str = "medium"  # low, medium, high


# ============ ANALYTICS SCHEMAS ============

class DashboardOverview(BaseModel):
    """Executive dashboard data"""
    total_users: int
    active_users: int
    suspended_users: int
    total_applications: int
    total_companies: int
    admin_count: int
    registration_trend_7d: int  # New registrations last 7 days
    applications_trend_7d: int  # New applications last 7 days


class UserAnalytics(BaseModel):
    """User metrics over period"""
    period: str  # '7d', '30d', '90d'
    total_users: int
    new_users: int
    active_users: int
    suspended_users: int
    admin_users: int
    user_retention_rate: float


class ApplicationAnalytics(BaseModel):
    """Application metrics over period"""
    period: str
    total_applications: int
    new_applications: int
    status_breakdown: Dict[str, int]
    average_apps_per_user: float


class CompanyStats(BaseModel):
    """Top companies with most applications"""
    company_name: str
    application_count: int
    latest_application: datetime


# ============ AUDIT & SECURITY SCHEMAS ============

class AuditLogResponse(BaseModel):
    """Admin audit log entry"""
    id: int
    admin_id: int
    admin_email: str
    action: str
    target_type: Optional[str]
    target_id: Optional[int]
    old_value: Optional[str]
    new_value: Optional[str]
    timestamp: datetime


class LoginAttempt(BaseModel):
    """Failed login attempt"""
    user_email: str
    attempt_time: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]


class SecuritySettings(BaseModel):
    """Security configuration"""
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    require_email_verification: bool = True
    require_strong_password: bool = True
    session_timeout_minutes: int = 60


# ============ SYSTEM SETTINGS SCHEMAS ============

class GeneralSettings(BaseModel):
    """General site settings"""
    app_name: str = "Job Application Tracker"
    app_description: str = ""
    support_email: str = ""
    site_url: str = ""


class FeatureFlags(BaseModel):
    """Feature enablement"""
    enable_ai_features: bool = True
    enable_job_search: bool = True
    enable_analytics: bool = True
    enable_email_notifications: bool = True
    enable_user_registration: bool = True


class EmailTemplate(BaseModel):
    """Email template customization"""
    template_name: str
    subject: str
    body: str
    is_active: bool = True


# ============ ANNOUNCEMENTS SCHEMAS ============

class AnnouncementCreate(BaseModel):
    """Create announcement"""
    title: str
    content: str
    expires_at: Optional[datetime] = None


class AnnouncementResponse(BaseModel):
    """Announcement data"""
    id: int
    title: str
    content: str
    created_by: int
    created_by_email: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool


# ============ RESPONSE SCHEMAS ============

class AdminActionResponse(BaseModel):
    """Generic admin action response"""
    success: bool
    message: str
    timestamp: datetime = datetime.utcnow()


class AdminErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: str
    timestamp: datetime = datetime.utcnow()
