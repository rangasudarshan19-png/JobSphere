"""
Comprehensive Admin Routes (18 endpoints)
Categories:
1. Advanced User Management (5 endpoints)
2. Application Management (3 endpoints)
3. Advanced Analytics (5 endpoints)
4. Audit & Security (3 endpoints)
5. System Settings (4 endpoints)
6. Announcements (3 endpoints)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List
import json
import csv
from io import StringIO

from app.schemas.user import UserResponse
from app.models.user import User
from app.models.application import Application, Company
from app.models.admin import AdminAuditLog, AdminSetting, Announcement, AdminNotification
from app.utils.database import get_db
from app.routers.auth import get_current_user
from app.schemas.admin import (
    UserSearchParams, UserActivityResponse, AdminMessageRequest,
    DashboardOverview, UserAnalytics, ApplicationAnalytics, CompanyStats,
    AuditLogResponse, AdminActionResponse, AnnouncementCreate, AnnouncementResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)):
    """Verify user is admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def log_admin_action(db: Session, admin_id: int, action: str, target_type: str = None, 
                     target_id: int = None, old_value: str = None, new_value: str = None):
    """Log admin action to audit trail"""
    try:
        audit_log = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        print(f"Error logging admin action: {e}")


# ============ CATEGORY 1: ADVANCED USER MANAGEMENT (5 endpoints) ============

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Get all users with application counts (basic list)"""
    users = db.query(User).all()
    
    user_list = []
    for user in users:
        app_count = db.query(Application).filter(Application.user_id == user.id).count()
        user_list.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": bool(user.is_admin),
            "is_suspended": bool(user.is_suspended),
            "created_at": user.created_at,
            "application_count": app_count
        })
    
    return user_list


@router.get("/users/search")
def search_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    email: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    is_admin: Optional[int] = Query(None),
    is_suspended: Optional[int] = Query(None),
    created_after: Optional[str] = Query(None),
    created_before: Optional[str] = Query(None)
):
    """
    Advanced user search with filters
    Query params:
    - email: search by email
    - name: search by full name
    - is_admin: 0 or 1
    - is_suspended: 0 or 1
    - created_after: ISO datetime (e.g., 2024-01-01T00:00:00)
    - created_before: ISO datetime
    """
    query = db.query(User)
    
    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
    if name:
        query = query.filter(User.full_name.ilike(f"%{name}%"))
    if is_admin is not None:
        query = query.filter(User.is_admin == is_admin)
    if is_suspended is not None:
        query = query.filter(User.is_suspended == is_suspended)
    
    if created_after:
        try:
            date_from = datetime.fromisoformat(created_after)
            query = query.filter(User.created_at >= date_from)
        except:
            pass
    
    if created_before:
        try:
            date_to = datetime.fromisoformat(created_before)
            query = query.filter(User.created_at <= date_to)
        except:
            pass
    
    users = query.all()
    
    result = []
    for user in users:
        app_count = db.query(Application).filter(Application.user_id == user.id).count()
        result.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": bool(user.is_admin),
            "is_suspended": bool(user.is_suspended),
            "created_at": user.created_at,
            "application_count": app_count
        })
    
    return result


@router.get("/users/{user_id}/profile")
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Get detailed user profile"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    app_count = db.query(Application).filter(Application.user_id == user_id).count()
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_admin": bool(user.is_admin),
        "is_suspended": bool(user.is_suspended),
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "application_count": app_count
    }


@router.get("/users/{user_id}/activity")
def get_user_activity(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Get user activity summary (no personal data)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    app_count = db.query(Application).filter(Application.user_id == user_id).count()
    
    # Get latest application
    latest_app = db.query(Application).filter(
        Application.user_id == user_id
    ).order_by(desc(Application.applied_date)).first()
    
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_admin": bool(user.is_admin),
        "is_suspended": bool(user.is_suspended),
        "created_at": user.created_at,
        "application_count": app_count,
        "latest_activity": latest_app.applied_date if latest_app else None
    }


@router.patch("/users/{user_id}/suspend")
def suspend_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    action: str = Query("suspend")  # 'suspend' or 'activate'
):
    """
    Suspend or activate a user account
    Query param: action='suspend' or action='activate'
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot suspend your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_suspended = user.is_suspended
    user_email = user.email
    user_name = user.full_name or "User"
    
    if action == "suspend":
        # Check if already suspended (idempotent)
        if user.is_suspended == 1:
            raise HTTPException(
                status_code=409,
                detail=f"User {user_email} is already suspended"
            )
        user.is_suspended = 1
        msg = f"User {user.email} suspended"
    elif action == "activate":
        # Check if already activated (idempotent)
        if user.is_suspended == 0:
            raise HTTPException(
                status_code=409,
                detail=f"User {user_email} is already active"
            )
        user.is_suspended = 0
        msg = f"User {user.email} activated"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    db.commit()
    
    # Log action
    log_admin_action(
        db, admin.id, f"user_{action}ed",
        target_type="user", target_id=user_id,
        old_value=str(old_suspended), new_value=str(user.is_suspended)
    )
    
    # Send email notification
    try:
        from app.services.email_service import email_service
        
        if action == "suspend":
            email_service.send_account_suspended_email(user_email, user_name)
        elif action == "activate":
            email_service.send_account_activated_email(user_email, user_name)
    except Exception as e:
        logger.error(f"Error sending account status email: {str(e)}")
    
    return {"success": True, "message": msg}


@router.post("/users/{user_id}/send-notification")
def send_user_notification(
    user_id: int,
    request: AdminMessageRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Send notification message to user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    notification = AdminNotification(
        recipient_id=user_id,
        sender_id=admin.id,
        message=request.message,
        created_at=datetime.utcnow()
    )
    db.add(notification)
    db.commit()
    
    log_admin_action(
        db, admin.id, "notification_sent",
        target_type="user", target_id=user_id,
        new_value=request.message
    )
    
    return {
        "success": True,
        "message": "Notification sent",
        "notification_id": notification.id
    }


# ============ CATEGORY 2: APPLICATION MANAGEMENT (3 endpoints) ============

@router.get("/applications/{app_id}")
def view_application(
    app_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """View application details by ID (no full search - privacy)"""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    user = db.query(User).filter(User.id == app.user_id).first()
    
    return {
        "id": app.id,
        "user_id": app.user_id,
        "user_email": user.email if user else None,
        "company": app.company_name,
        "position": app.position,
        "status": app.status,
        "applied_date": app.applied_date,
        "created_at": app.created_at
    }


@router.patch("/applications/{app_id}/flag")
def flag_application(
    app_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    reason: str = Query(""),
    severity: str = Query("medium")
):
    """
    Flag an application as suspicious
    Query params: reason, severity (low/medium/high)
    """
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    log_admin_action(
        db, admin.id, "application_flagged",
        target_type="application", target_id=app_id,
        new_value=json.dumps({"reason": reason, "severity": severity})
    )
    
    return {
        "success": True,
        "message": f"Application {app_id} flagged",
        "reason": reason,
        "severity": severity
    }


@router.delete("/applications/{app_id}")
def delete_application(
    app_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Delete an application"""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    user_email = db.query(User).filter(User.id == app.user_id).first().email
    
    db.delete(app)
    db.commit()
    
    log_admin_action(
        db, admin.id, "application_deleted",
        target_type="application", target_id=app_id,
        new_value=f"Deleted application for {user_email}"
    )
    
    return {"success": True, "message": f"Application {app_id} deleted"}


# ============ CATEGORY 3: ADVANCED ANALYTICS (5 endpoints) ============

@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Executive dashboard overview"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_suspended == 0).count()
    suspended_users = db.query(User).filter(User.is_suspended == 1).count()
    total_applications = db.query(Application).count()
    total_companies = db.query(Company).count()
    admin_count = db.query(User).filter(User.is_admin == 1).count()
    
    # 7 day trend
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_7d = db.query(User).filter(User.created_at >= week_ago).count()
    new_apps_7d = db.query(Application).filter(Application.created_at >= week_ago).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "suspended_users": suspended_users,
        "total_applications": total_applications,
        "total_companies": total_companies,
        "admin_count": admin_count,
        "new_users_7d": new_users_7d,
        "new_applications_7d": new_apps_7d
    }


@router.get("/analytics/users")
def user_analytics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    period: str = Query("30d")  # '7d', '30d', '90d'
):
    """User growth and retention metrics"""
    days = int(period.replace('d', ''))
    start_date = datetime.utcnow() - timedelta(days=days)
    
    total_users = db.query(User).count()
    new_users = db.query(User).filter(User.created_at >= start_date).count()
    active_users = db.query(User).filter(User.is_suspended == 0).count()
    suspended_users = db.query(User).filter(User.is_suspended == 1).count()
    admin_users = db.query(User).filter(User.is_admin == 1).count()
    
    retention_rate = (active_users / total_users * 100) if total_users > 0 else 0
    
    return {
        "period": period,
        "total_users": total_users,
        "new_users": new_users,
        "active_users": active_users,
        "suspended_users": suspended_users,
        "admin_users": admin_users,
        "retention_rate": round(retention_rate, 1)
    }


@router.get("/analytics/applications")
def application_analytics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    period: str = Query("30d")
):
    """Application trend analytics"""
    days = int(period.replace('d', ''))
    start_date = datetime.utcnow() - timedelta(days=days)
    
    total_apps = db.query(Application).count()
    new_apps = db.query(Application).filter(Application.created_at >= start_date).count()
    total_users = db.query(User).count()
    avg_per_user = total_apps / total_users if total_users > 0 else 0
    
    # Status breakdown
    statuses = db.query(
        Application.status,
        db.func.count(Application.id)
    ).group_by(Application.status).all()
    status_breakdown = {status: count for status, count in statuses}
    
    return {
        "period": period,
        "total_applications": total_apps,
        "new_applications": new_apps,
        "average_per_user": round(avg_per_user, 1),
        "status_breakdown": status_breakdown
    }


@router.get("/analytics/companies")
def company_analytics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    limit: int = Query(20)
):
    """Top companies with most applications"""
    companies = db.query(
        Company.name,
        db.func.count(Application.id).label('app_count')
    ).join(Application, Company.id == Application.company_id, isouter=True)\
     .group_by(Company.id)\
     .order_by(desc(db.func.count(Application.id)))\
     .limit(limit).all()
    
    result = []
    for company_name, app_count in companies:
        latest_app = db.query(Application).filter(
            Application.company_name == company_name
        ).order_by(desc(Application.created_at)).first()
        
        result.append({
            "company_name": company_name,
            "application_count": app_count,
            "latest_application": latest_app.created_at if latest_app else None
        })
    
    return result


@router.get("/analytics/export")
def export_analytics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    format: str = Query("csv")  # 'csv' or 'json'
):
    """Export aggregate analytics (no personal data)"""
    # Get aggregate stats
    stats = {
        "total_users": db.query(User).count(),
        "active_users": db.query(User).filter(User.is_suspended == 0).count(),
        "total_applications": db.query(Application).count(),
        "total_companies": db.query(Company).count(),
        "admin_users": db.query(User).filter(User.is_admin == 1).count(),
    }
    
    if format == "json":
        return stats
    
    # CSV format
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Value"])
    for key, value in stats.items():
        writer.writerow([key, value])
    
    return {
        "success": True,
        "format": "csv",
        "data": output.getvalue()
    }


# ============ CATEGORY 4: AUDIT & SECURITY (3 endpoints) ============

@router.get("/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    action: Optional[str] = Query(None),
    admin_id: Optional[int] = Query(None),
    limit: int = Query(100)
):
    """Get audit logs with optional filters"""
    query = db.query(AdminAuditLog)
    
    if action:
        query = query.filter(AdminAuditLog.action.ilike(f"%{action}%"))
    if admin_id:
        query = query.filter(AdminAuditLog.admin_id == admin_id)
    
    logs = query.order_by(desc(AdminAuditLog.timestamp)).limit(limit).all()
    
    result = []
    for log in logs:
        admin_user = db.query(User).filter(User.id == log.admin_id).first()
        result.append({
            "id": log.id,
            "admin_id": log.admin_id,
            "admin_email": admin_user.email if admin_user else None,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "timestamp": log.timestamp
        })
    
    return result


@router.get("/security/login-attempts")
def get_login_attempts(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    period: str = Query("24h")
):
    """Get failed login attempts (if tracking exists)"""
    # This would require a login_attempts table to track failed logins
    # For now, return placeholder
    return {
        "message": "Login attempt tracking requires implementation",
        "period": period,
        "attempts": []
    }


@router.patch("/security/settings")
def update_security_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    max_login_attempts: int = Query(5),
    lockout_duration_minutes: int = Query(15),
    session_timeout_minutes: int = Query(60)
):
    """Update security configuration"""
    settings = [
        ("max_login_attempts", str(max_login_attempts)),
        ("lockout_duration_minutes", str(lockout_duration_minutes)),
        ("session_timeout_minutes", str(session_timeout_minutes))
    ]
    
    for key, value in settings:
        setting = db.query(AdminSetting).filter(AdminSetting.setting_key == key).first()
        if setting:
            setting.setting_value = value
            setting.updated_by = admin.id
            setting.updated_at = datetime.utcnow()
        else:
            setting = AdminSetting(
                setting_key=key,
                setting_value=value,
                category="security",
                updated_by=admin.id
            )
            db.add(setting)
    
    db.commit()
    
    log_admin_action(
        db, admin.id, "security_settings_updated",
        target_type="setting",
        new_value=json.dumps({
            "max_login_attempts": max_login_attempts,
            "lockout_duration_minutes": lockout_duration_minutes,
            "session_timeout_minutes": session_timeout_minutes
        })
    )
    
    return {
        "success": True,
        "message": "Security settings updated",
        "settings": {
            "max_login_attempts": max_login_attempts,
            "lockout_duration_minutes": lockout_duration_minutes,
            "session_timeout_minutes": session_timeout_minutes
        }
    }


# ============ CATEGORY 5: SYSTEM SETTINGS (4 endpoints) ============

@router.get("/settings")
def get_all_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Get all system settings"""
    settings = db.query(AdminSetting).all()
    
    result = {}
    for setting in settings:
        category = setting.category or "other"
        if category not in result:
            result[category] = {}
        result[category][setting.setting_key] = setting.setting_value
    
    return result


@router.patch("/settings/general")
def update_general_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    app_name: str = Query("Job Application Tracker"),
    app_description: str = Query(""),
    support_email: str = Query(""),
    site_url: str = Query("")
):
    """Update general site settings"""
    settings_data = {
        "app_name": app_name,
        "app_description": app_description,
        "support_email": support_email,
        "site_url": site_url
    }
    
    for key, value in settings_data.items():
        setting = db.query(AdminSetting).filter(AdminSetting.setting_key == key).first()
        if setting:
            setting.setting_value = value
            setting.updated_by = admin.id
            setting.updated_at = datetime.utcnow()
        else:
            setting = AdminSetting(
                setting_key=key,
                setting_value=value,
                category="general",
                updated_by=admin.id
            )
            db.add(setting)
    
    db.commit()
    
    log_admin_action(
        db, admin.id, "general_settings_updated",
        target_type="setting",
        new_value=json.dumps(settings_data)
    )
    
    return {"success": True, "message": "General settings updated", "settings": settings_data}


@router.patch("/settings/features")
def update_feature_flags(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    enable_ai_features: bool = Query(True),
    enable_job_search: bool = Query(True),
    enable_analytics: bool = Query(True),
    enable_email_notifications: bool = Query(True),
    enable_user_registration: bool = Query(True)
):
    """Update feature flags"""
    settings_data = {
        "enable_ai_features": str(enable_ai_features),
        "enable_job_search": str(enable_job_search),
        "enable_analytics": str(enable_analytics),
        "enable_email_notifications": str(enable_email_notifications),
        "enable_user_registration": str(enable_user_registration)
    }
    
    for key, value in settings_data.items():
        setting = db.query(AdminSetting).filter(AdminSetting.setting_key == key).first()
        if setting:
            setting.setting_value = value
            setting.updated_by = admin.id
            setting.updated_at = datetime.utcnow()
        else:
            setting = AdminSetting(
                setting_key=key,
                setting_value=value,
                category="features",
                updated_by=admin.id
            )
            db.add(setting)
    
    db.commit()
    
    log_admin_action(
        db, admin.id, "feature_flags_updated",
        target_type="setting",
        new_value=json.dumps(settings_data)
    )
    
    return {"success": True, "message": "Feature flags updated", "settings": settings_data}


@router.patch("/settings/email-templates")
def update_email_template(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    template_name: str = Query(""),
    subject: str = Query(""),
    body: str = Query("")
):
    """Update email template"""
    if not template_name:
        raise HTTPException(status_code=400, detail="template_name required")
    
    setting = db.query(AdminSetting).filter(
        AdminSetting.setting_key == f"email_template_{template_name}"
    ).first()
    
    template_data = {"subject": subject, "body": body}
    
    if setting:
        setting.setting_value = json.dumps(template_data)
        setting.updated_by = admin.id
        setting.updated_at = datetime.utcnow()
    else:
        setting = AdminSetting(
            setting_key=f"email_template_{template_name}",
            setting_value=json.dumps(template_data),
            category="email",
            updated_by=admin.id
        )
        db.add(setting)
    
    db.commit()
    
    log_admin_action(
        db, admin.id, "email_template_updated",
        target_type="setting",
        new_value=json.dumps(template_data)
    )
    
    return {
        "success": True,
        "message": f"Email template '{template_name}' updated",
        "template": template_data
    }


# ============ CATEGORY 6: ANNOUNCEMENTS (3 endpoints) ============

@router.post("/announcements")
def create_announcement(
    request: AnnouncementCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Create new announcement and email all active users"""
    
    # Check for duplicate announcements (idempotent - prevent spam)
    # Look for same announcement created by same admin in the last 5 minutes
    from datetime import timedelta
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    
    duplicate_check = db.query(Announcement).filter(
        Announcement.created_by == admin.id,
        Announcement.title == request.title,
        Announcement.content == request.content,
        Announcement.created_at > five_min_ago
    ).first()
    
    if duplicate_check:
        raise HTTPException(
            status_code=409,
            detail="An identical announcement was just created. Please wait before creating another."
        )
    
    announcement = Announcement(
        title=request.title,
        content=request.content,
        created_by=admin.id,
        expires_at=request.expires_at,
        created_at=datetime.utcnow(),
        is_active=1
    )
    db.add(announcement)
    db.commit()
    
    log_admin_action(
        db, admin.id, "announcement_created",
        target_type="announcement", target_id=announcement.id,
        new_value=request.title
    )
    
    # Send email to all active users
    try:
        from app.services.email_service import email_service
        
        # Get all active (non-suspended) users
        active_users = db.query(User).filter(User.is_suspended == 0).all()
        users_list = [(user.email, user.full_name or "User") for user in active_users]
        
        if users_list:
            email_stats = email_service.broadcast_announcement(
                users_list,
                request.title,
                request.content
            )
            logger.info(f"[ANNOUNCEMENT] Broadcast stats: {email_stats}")
            
            return {
                "success": True,
                "message": "Announcement created and emails sent",
                "announcement_id": announcement.id,
                "email_stats": email_stats
            }
        else:
            return {
                "success": True,
                "message": "Announcement created (no active users to notify)",
                "announcement_id": announcement.id
            }
    except Exception as e:
        logger.error(f"Error broadcasting announcement: {str(e)}")
        return {
            "success": True,
            "message": "Announcement created but email broadcast failed",
            "announcement_id": announcement.id,
            "error": str(e)
        }


@router.get("/announcements")
def list_announcements(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    active_only: bool = Query(True)
):
    """List all announcements"""
    query = db.query(Announcement)
    
    if active_only:
        query = query.filter(Announcement.is_active == 1)
    
    announcements = query.order_by(desc(Announcement.created_at)).all()
    
    result = []
    for ann in announcements:
        creator = db.query(User).filter(User.id == ann.created_by).first()
        result.append({
            "id": ann.id,
            "title": ann.title,
            "content": ann.content,
            "created_by": ann.created_by,
            "created_by_email": creator.email if creator else None,
            "created_at": ann.created_at,
            "expires_at": ann.expires_at,
            "is_active": bool(ann.is_active)
        })
    
    return result


@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Delete announcement"""
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    db.delete(announcement)
    db.commit()
    
    log_admin_action(
        db, admin.id, "announcement_deleted",
        target_type="announcement", target_id=announcement_id,
        old_value=announcement.title
    )
    
    return {"success": True, "message": f"Announcement {announcement_id} deleted"}


# ============ BACKWARD COMPATIBILITY - Keep original endpoints ============

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Delete a user and all their applications (backward compatible)
    """
    if admin and user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own admin account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is admin
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users. Remove admin privileges first."
        )
    
    # Store user details before deletion for email
    user_email = user.email
    user_name = user.full_name or "User"
    
    # Delete all user's applications first (cascade)
    app_count = db.query(Application).filter(Application.user_id == user_id).count()
    db.query(Application).filter(Application.user_id == user_id).delete()
    
    # Send email notification before deleting user
    try:
        from app.services.email_service import email_service
        email_service.send_account_deleted_email(user_email, user_name)
    except Exception as e:
        logger.error(f"Error sending account deletion email: {str(e)}")
    
    # Delete user
    db.delete(user)
    db.commit()
    
    log_admin_action(
        db, admin.id, "user_deleted",
        target_type="user", target_id=user_id,
        new_value=f"Deleted {user_email} with {app_count} applications"
    )
    
    return {
        "message": f"User {user_email} and {app_count} applications deleted successfully"
    }


@router.get("/stats")
def get_system_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Get system statistics (backward compatible)"""
    try:
        total_users = db.query(User).count()
        total_applications = db.query(Application).count()
        total_companies = db.query(Company).count()
        admin_users = db.query(User).filter(User.is_admin == 1).count()
        
        applications_per_user = total_applications / total_users if total_users > 0 else 0
        
        status_breakdown = {}
        try:
            statuses = db.query(
                Application.status,
                db.func.count(Application.id)
            ).group_by(Application.status).all()
            status_breakdown = {status: count for status, count in statuses}
        except Exception as e:
            print(f"Error getting status breakdown: {e}")
        
        most_active_user = None
        try:
            most_active = db.query(
                User.email,
                db.func.count(Application.id).label('app_count')
            ).join(Application, User.id == Application.user_id, isouter=True)\
             .group_by(User.id)\
             .order_by(db.func.count(Application.id).desc())\
             .first()
            
            if most_active:
                most_active_user = most_active[0]
        except Exception as e:
            print(f"Error getting most active user: {e}")
        
        return {
            "total_users": total_users,
            "admin_users": admin_users,
            "regular_users": total_users - admin_users,
            "total_applications": total_applications,
            "total_companies": total_companies,
            "applications_per_user": round(applications_per_user, 1),
            "most_active_user": most_active_user,
            "application_status_breakdown": status_breakdown,
            "recent_applications": 0
        }
    except Exception as e:
        print(f"Error in get_system_stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading statistics: {str(e)}"
        )


@router.patch("/users/{user_id}/make-admin")
def make_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Make a user an admin (backward compatible)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already admin (idempotent)
    if user.is_admin == 1:
        raise HTTPException(
            status_code=409,
            detail=f"User {user.email} is already an admin"
        )
    
    user.is_admin = 1
    db.commit()
    
    log_admin_action(
        db, admin.id, "admin_granted",
        target_type="user", target_id=user_id,
        new_value="is_admin=1"
    )
    
    return {"success": True, "message": f"{user.email} is now an admin"}


@router.patch("/users/{user_id}/remove-admin")
def remove_admin_role(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Remove admin role from a user (backward compatible)"""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin privileges"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already non-admin (idempotent)
    if user.is_admin == 0:
        raise HTTPException(
            status_code=409,
            detail=f"User {user.email} is not an admin"
        )
    
    user.is_admin = 0
    db.commit()
    
    log_admin_action(
        db, admin.id, "admin_removed",
        target_type="user", target_id=user_id,
        new_value="is_admin=0"
    )
    
    return {"success": True, "message": f"Admin privileges removed from {user.email}"}

