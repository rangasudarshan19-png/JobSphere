"""
Notification models for tracking and managing user notifications
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Time, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.database import Base


class Notification(Base):
    """Model for storing notification history"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # status_change, interview_reminder, follow_up, offer, weekly_summary
    title = Column(String(200), nullable=False)
    message = Column(Text)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    email_sent = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    application = relationship("Application", back_populates="notifications")
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.read_at = datetime.utcnow()
    
    @property
    def is_read(self) -> bool:
        """Check if notification has been read"""
        return self.read_at is not None
    
    def to_dict(self):
        """Convert notification to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'application_id': self.application_id,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'email_sent': self.email_sent,
            'is_read': self.is_read
        }


class NotificationPreferences(Base):
    """Model for storing user notification preferences"""
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Email settings
    email_enabled = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    
    # Notification types
    status_change = Column(Boolean, default=True)
    interview_reminders = Column(Boolean, default=True)
    follow_up_reminders = Column(Boolean, default=True)
    offer_notifications = Column(Boolean, default=True)
    weekly_summary = Column(Boolean, default=True)
    
    # Frequency settings
    email_frequency = Column(String(20), default='instant')  # instant, daily, weekly
    
    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(Time, nullable=True)  # e.g., 22:00
    quiet_hours_end = Column(Time, nullable=True)    # e.g., 07:00
    
    # Relationships
    user = relationship("User", back_populates="notification_preferences")
    
    def to_dict(self):
        """Convert preferences to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_enabled': self.email_enabled,
            'email_verified': self.email_verified,
            'status_change': self.status_change,
            'interview_reminders': self.interview_reminders,
            'follow_up_reminders': self.follow_up_reminders,
            'offer_notifications': self.offer_notifications,
            'weekly_summary': self.weekly_summary,
            'email_frequency': self.email_frequency,
            'quiet_hours_enabled': self.quiet_hours_enabled,
            'quiet_hours_start': self.quiet_hours_start.isoformat() if self.quiet_hours_start else None,
            'quiet_hours_end': self.quiet_hours_end.isoformat() if self.quiet_hours_end else None
        }
    
    def is_in_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled or not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = datetime.now().time()
        start = self.quiet_hours_start
        end = self.quiet_hours_end
        
        # Handle quiet hours that span midnight
        if start < end:
            return start <= now <= end
        else:
            return now >= start or now <= end
    
    def should_send_notification(self, notification_type: str) -> bool:
        """
        Check if a notification of given type should be sent
        
        Args:
            notification_type: Type of notification (status_change, interview_reminder, etc.)
            
        Returns:
            bool: True if notification should be sent
        """
        if not self.email_enabled:
            return False
        
        if self.is_in_quiet_hours():
            return False
        
        # Check type-specific preferences
        type_mapping = {
            'status_change': self.status_change,
            'interview_reminder': self.interview_reminders,
            'follow_up': self.follow_up_reminders,
            'offer': self.offer_notifications,
            'weekly_summary': self.weekly_summary
        }
        
        return type_mapping.get(notification_type, False)
    
    @staticmethod
    def get_or_create_default(db, user_id: int):
        """Get or create default preferences for a user"""
        prefs = db.query(NotificationPreferences).filter(
            NotificationPreferences.user_id == user_id
        ).first()
        
        if not prefs:
            prefs = NotificationPreferences(
                user_id=user_id,
                email_enabled=True,
                status_change=True,
                interview_reminders=True,
                follow_up_reminders=True,
                offer_notifications=True,
                weekly_summary=True,
                email_frequency='instant'
            )
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
        
        return prefs
