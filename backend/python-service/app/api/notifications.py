"""
Notification API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import time

from app.utils.database import get_db
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification, NotificationPreferences
from app.services.notification_service import get_notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# Pydantic models for request/response
class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: Optional[str]
    application_id: Optional[int]
    sent_at: str
    read_at: Optional[str]
    email_sent: bool
    is_read: bool
    
    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    status_change: Optional[bool] = None
    interview_reminders: Optional[bool] = None
    follow_up_reminders: Optional[bool] = None
    offer_notifications: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    email_frequency: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None  # Format: "HH:MM"
    quiet_hours_end: Optional[str] = None    # Format: "HH:MM"


class NotificationPreferencesResponse(BaseModel):
    id: int
    user_id: int
    email_enabled: bool
    email_verified: bool
    status_change: bool
    interview_reminders: bool
    follow_up_reminders: bool
    offer_notifications: bool
    weekly_summary: bool
    email_frequency: str
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's notifications
    
    - **unread_only**: Only return unread notifications
    - **limit**: Maximum number of notifications (default 50)
    """
    service = get_notification_service(db)
    notifications = service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit
    )
    
    return [n.to_dict() for n in notifications]


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    service = get_notification_service(db)
    success = service.mark_as_read(notification_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification marked as read"}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's notification preferences"""
    prefs = NotificationPreferences.get_or_create_default(db, current_user.id)
    return prefs.to_dict()


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's notification preferences
    
    Example request body:
    ```json
    {
        "email_enabled": true,
        "status_change": true,
        "interview_reminders": true,
        "follow_up_reminders": true,
        "offer_notifications": true,
        "weekly_summary": true,
        "email_frequency": "instant",
        "quiet_hours_enabled": true,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "07:00"
    }
    ```
    """
    prefs = NotificationPreferences.get_or_create_default(db, current_user.id)
    
    # Update fields if provided
    if preferences.email_enabled is not None:
        prefs.email_enabled = preferences.email_enabled
    
    if preferences.status_change is not None:
        prefs.status_change = preferences.status_change
    
    if preferences.interview_reminders is not None:
        prefs.interview_reminders = preferences.interview_reminders
    
    if preferences.follow_up_reminders is not None:
        prefs.follow_up_reminders = preferences.follow_up_reminders
    
    if preferences.offer_notifications is not None:
        prefs.offer_notifications = preferences.offer_notifications
    
    if preferences.weekly_summary is not None:
        prefs.weekly_summary = preferences.weekly_summary
    
    if preferences.email_frequency is not None:
        if preferences.email_frequency not in ['instant', 'daily', 'weekly']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_frequency must be 'instant', 'daily', or 'weekly'"
            )
        prefs.email_frequency = preferences.email_frequency
    
    if preferences.quiet_hours_enabled is not None:
        prefs.quiet_hours_enabled = preferences.quiet_hours_enabled
    
    if preferences.quiet_hours_start is not None:
        try:
            # Parse time string (HH:MM)
            parts = preferences.quiet_hours_start.split(':')
            prefs.quiet_hours_start = time(int(parts[0]), int(parts[1]))
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quiet_hours_start must be in format 'HH:MM'"
            )
    
    if preferences.quiet_hours_end is not None:
        try:
            # Parse time string (HH:MM)
            parts = preferences.quiet_hours_end.split(':')
            prefs.quiet_hours_end = time(int(parts[0]), int(parts[1]))
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quiet_hours_end must be in format 'HH:MM'"
            )
    
    db.commit()
    db.refresh(prefs)
    
    return prefs.to_dict()


@router.post("/test-email")
async def send_test_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a test email to verify email configuration"""
    service = get_notification_service(db)
    success = service.send_test_email(current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test email. Check SMTP configuration."
        )
    
    return {
        "message": "Test email sent successfully",
        "email": current_user.email
    }


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read_at == None
    ).count()
    
    return {"unread_count": count}


@router.post("/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read_at == None
    ).all()
    
    for notification in notifications:
        notification.mark_as_read()
    
    db.commit()
    
    return {
        "message": f"Marked {len(notifications)} notifications as read"
    }
