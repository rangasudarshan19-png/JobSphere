"""
Notification Service for Job Tracker
Handles notification triggers, scheduling, and delivery
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from app.models.notification import Notification, NotificationPreferences
from app.models.application import Application
from app.models.user import User
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications and triggers"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_notification(
        self,
        user_id: int,
        type: str,
        title: str,
        message: str = None,
        application_id: int = None,
        send_email: bool = True
    ) -> Notification:
        """
        Create a new notification
        
        Args:
            user_id: User ID
            type: Notification type (status_change, interview_reminder, etc.)
            title: Notification title
            message: Notification message (optional)
            application_id: Related application ID (optional)
            send_email: Whether to send email (default True)
            
        Returns:
            Notification: Created notification object
        """
        # Create notification record
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            application_id=application_id,
            email_sent=False
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        # Send email if requested and user preferences allow
        if send_email:
            self._send_notification_email(notification)
        
        return notification
    
    def _send_notification_email(self, notification: Notification) -> bool:
        """
        Send email for a notification based on user preferences
        
        Args:
            notification: Notification object
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Get user preferences
            prefs = NotificationPreferences.get_or_create_default(
                self.db, 
                notification.user_id
            )
            
            # Check if should send this notification type
            if not prefs.should_send_notification(notification.type):
                logger.info(f"Notification {notification.type} disabled for user {notification.user_id}")
                return False
            
            # Get user and application details
            user = self.db.query(User).filter(User.id == notification.user_id).first()
            if not user:
                logger.error(f"User {notification.user_id} not found")
                return False
            
            # Send appropriate email based on type
            email_sent = False
            
            if notification.type == 'status_change' and notification.application_id:
                email_sent = self._send_status_change_email(notification, user)
            
            elif notification.type == 'interview_reminder' and notification.application_id:
                email_sent = self._send_interview_reminder_email(notification, user)
            
            elif notification.type == 'follow_up' and notification.application_id:
                email_sent = self._send_follow_up_email(notification, user)
            
            elif notification.type == 'offer' and notification.application_id:
                email_sent = self._send_offer_email(notification, user)
            
            elif notification.type == 'weekly_summary':
                email_sent = self._send_weekly_summary_email(notification, user)
            
            # Update notification record
            if email_sent:
                notification.email_sent = True
                self.db.commit()
                logger.info(f"Email sent for notification {notification.id}")
            
            return email_sent
            
        except Exception as e:
            logger.error(f"Failed to send notification email: {str(e)}")
            return False
    
    def _send_status_change_email(self, notification: Notification, user: User) -> bool:
        """Status change emails are not yet implemented."""
        logger.info("Skipping status change email: feature not implemented")
        return False
    
    def _send_interview_reminder_email(self, notification: Notification, user: User) -> bool:
        """Send interview reminder email"""
        app = self.db.query(Application).filter(
            Application.id == notification.application_id
        ).first()
        
        if not app:
            return False
        
        company = app.company.name if app.company else "Unknown Company"
        
        # Determine hours until interview from notification message
        hours_until = 24  # default
        if '1 hour' in notification.title.lower():
            hours_until = 1
        
        # Parse interview date/time from notes or use deadline
        interview_date = app.deadline.strftime('%B %d, %Y') if app.deadline else 'TBD'
        interview_time = 'TBD'
        
        # Try to extract time from notes
        if app.notes:
            # Simple extraction - you can enhance this
            if 'time:' in app.notes.lower():
                try:
                    time_part = app.notes.lower().split('time:')[1].split('\n')[0].strip()
                    interview_time = time_part
                except:
                    pass
        
        return email_service.send_interview_reminder_email(
            to_email=user.email,
            user_name=user.full_name,
            company=company,
            position=app.job_title,
            interview_date=interview_date,
            interview_time=interview_time,
            location=app.location,
            hours_until=hours_until
        )
    
    def _send_follow_up_email(self, notification: Notification, user: User) -> bool:
        """Send follow-up reminder email"""
        app = self.db.query(Application).filter(
            Application.id == notification.application_id
        ).first()
        
        if not app:
            return False
        
        company = app.company.name if app.company else "Unknown Company"
        days_since = (datetime.now().date() - app.applied_date).days
        
        return email_service.send_follow_up_reminder_email(
            to_email=user.email,
            user_name=user.full_name,
            company=company,
            position=app.job_title,
            days_since_application=days_since,
            application_id=app.id
        )
    
    def _send_offer_email(self, notification: Notification, user: User) -> bool:
        """Send offer notification email"""
        app = self.db.query(Application).filter(
            Application.id == notification.application_id
        ).first()
        
        if not app:
            return False
        
        company = app.company.name if app.company else "Unknown Company"
        
        return email_service.send_offer_notification_email(
            to_email=user.email,
            user_name=user.full_name,
            company=company,
            position=app.job_title,
            salary=app.salary_range,
            application_id=app.id
        )
    
    def _send_weekly_summary_email(self, notification: Notification, user: User) -> bool:
        """Send weekly summary email"""
        # Calculate stats for the past week
        week_ago = datetime.now() - timedelta(days=7)
        
        applications = self.db.query(Application).filter(
            and_(
                Application.user_id == user.id,
                Application.created_at >= week_ago
            )
        ).all()
        
        # Calculate stats
        stats = {
            'applications_sent': len(applications),
            'interviews_scheduled': len([a for a in applications if 'interview' in a.status.lower()]),
            'offers_received': len([a for a in applications if a.status.lower() == 'offer']),
            'rejections': len([a for a in applications if a.status.lower() == 'rejected']),
            'pending': len([a for a in applications if a.status.lower() in ['applied', 'screening']]),
            'response_rate': 0
        }
        
        # Calculate response rate
        if stats['applications_sent'] > 0:
            responses = stats['interviews_scheduled'] + stats['offers_received'] + stats['rejections']
            stats['response_rate'] = round((responses / stats['applications_sent']) * 100)
        
        return email_service.send_weekly_summary_email(
            to_email=user.email,
            user_name=user.full_name,
            stats=stats
        )
    
    def notify_status_change(
        self,
        application_id: int,
        old_status: str,
        new_status: str
    ) -> Optional[Notification]:
        """
        Send notification when application status changes
        
        Args:
            application_id: Application ID
            old_status: Previous status
            new_status: New status
            
        Returns:
            Notification object if created
        """
        app = self.db.query(Application).filter(
            Application.id == application_id
        ).first()
        
        if not app:
            logger.error(f"Application {application_id} not found")
            return None
        
        company = app.company.name if app.company else "Unknown Company"
        
        return self.create_notification(
            user_id=app.user_id,
            type='status_change',
            title=f"Status Updated: {company}",
            message=f"{old_status} -> {new_status}",
            application_id=application_id,
            send_email=True
        )
    
    def check_interview_reminders(self) -> List[Notification]:
        """
        Check for upcoming interviews and send reminders
        Should be run by a scheduler every hour
        
        Returns:
            List of notifications created
        """
        notifications = []
        
        # Get applications with interviews in the next 24-48 hours
        tomorrow = datetime.now().date() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        applications = self.db.query(Application).filter(
            and_(
                Application.status.in_(['interview_scheduled', 'Interview Scheduled']),
                Application.deadline >= tomorrow,
                Application.deadline <= day_after
            )
        ).all()
        
        for app in applications:
            # Check if we already sent a reminder
            existing = self.db.query(Notification).filter(
                and_(
                    Notification.application_id == app.id,
                    Notification.type == 'interview_reminder',
                    Notification.sent_at >= datetime.now() - timedelta(hours=24)
                )
            ).first()
            
            if not existing:
                company = app.company.name if app.company else "Unknown Company"
                notification = self.create_notification(
                    user_id=app.user_id,
                    type='interview_reminder',
                    title=f"Interview Tomorrow: {company}",
                    message=f"Your interview for {app.job_title} is tomorrow!",
                    application_id=app.id,
                    send_email=True
                )
                notifications.append(notification)
                logger.info(f"Sent interview reminder for application {app.id}")
        
        return notifications
    
    def check_follow_up_reminders(self) -> List[Notification]:
        """
        Check for applications that need follow-up
        Should be run by a scheduler daily
        
        Returns:
            List of notifications created
        """
        notifications = []
        
        # Get applications applied 7 days ago with no response
        week_ago = datetime.now().date() - timedelta(days=7)
        
        applications = self.db.query(Application).filter(
            and_(
                Application.applied_date == week_ago,
                Application.status.in_(['applied', 'Applied', 'screening', 'Screening'])
            )
        ).all()
        
        for app in applications:
            # Check if we already sent a follow-up reminder
            existing = self.db.query(Notification).filter(
                and_(
                    Notification.application_id == app.id,
                    Notification.type == 'follow_up'
                )
            ).first()
            
            if not existing:
                company = app.company.name if app.company else "Unknown Company"
                notification = self.create_notification(
                    user_id=app.user_id,
                    type='follow_up',
                    title=f"Time to Follow Up: {company}",
                    message=f"It's been 7 days since you applied to {company}",
                    application_id=app.id,
                    send_email=True
                )
                notifications.append(notification)
                logger.info(f"Sent follow-up reminder for application {app.id}")
        
        return notifications
    
    def send_weekly_summaries(self) -> List[Notification]:
        """
        Send weekly summaries to all users
        Should be run by a scheduler every Monday
        
        Returns:
            List of notifications created
        """
        notifications = []
        
        # Get all users with weekly summary enabled
        users = self.db.query(User).all()
        
        for user in users:
            prefs = NotificationPreferences.get_or_create_default(self.db, user.id)
            
            if prefs.weekly_summary and prefs.email_enabled:
                notification = self.create_notification(
                    user_id=user.id,
                    type='weekly_summary',
                    title="Your Weekly Job Search Summary",
                    message="Here's your progress from the past week",
                    send_email=True
                )
                notifications.append(notification)
                logger.info(f"Sent weekly summary to user {user.id}")
        
        return notifications
    
    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """
        Get notifications for a user
        
        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            limit: Maximum number of notifications to return
            
        Returns:
            List of notifications
        """
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id
        )
        
        if unread_only:
            query = query.filter(Notification.read_at == None)
        
        return query.order_by(Notification.sent_at.desc()).limit(limit).all()
    
    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """
        Mark a notification as read
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for security)
            
        Returns:
            bool: True if marked as read
        """
        notification = self.db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        ).first()
        
        if notification:
            notification.mark_as_read()
            self.db.commit()
            return True
        
        return False
    
    def send_test_email(self, user_id: int) -> bool:
        """
        Send a test email to verify configuration
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if test email sent successfully
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        return email_service.send_test_email(user.email, user.full_name)
    
    def check_next_phase_reminders(self) -> List[Notification]:
        """
        Check for upcoming next phases and send reminder emails
        
        Sends two types of reminders:
        1. 24-hour reminder (1 day before)
        2. Day-of reminder (morning of the phase)
        
        Should be run by scheduler twice daily (morning and evening)
        
        Returns:
            List of notifications created
        """
        from datetime import datetime, timedelta, date
        from app.models.application import Application
        
        notifications = []
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        logger.info(f"Checking next phase reminders for {today}")
        
        # Check for next phases happening tomorrow (24h reminder)
        tomorrow_phases = self.db.query(Application).filter(
            Application.next_phase_date == tomorrow
        ).all()
        
        for app in tomorrow_phases:
            user = self.db.query(User).filter(User.id == app.user_id).first()
            if not user:
                continue
            
            prefs = NotificationPreferences.get_or_create_default(self.db, app.user_id)
            
            # Check if user wants reminders and it's not quiet hours
            if not prefs.should_send_notification('interview_reminders'):
                continue
            
            # Check if we already sent tomorrow's reminder
            existing = self.db.query(Notification).filter(
                and_(
                    Notification.user_id == app.user_id,
                    Notification.application_id == app.id,
                    Notification.type == 'next_phase_reminder_24h',
                    Notification.sent_at >= datetime.utcnow() - timedelta(hours=30)
                )
            ).first()
            
            if existing:
                continue  # Already sent
            
            # Send 24-hour reminder
            phase_type = app.next_phase_type or "Interview"
            company_name = app.company.name if app.company else "the company"
            
            try:
                email_service.send_next_phase_reminder_email(
                    to_email=user.email,
                    user_name=user.full_name,
                    company=company_name,
                    position=app.job_title,
                    phase_type=phase_type,
                    phase_date=tomorrow.strftime("%B %d, %Y"),
                    phase_time="Not specified",  # Add time field later if needed
                    location="",
                    job_description=app.job_description or "",
                    application_id=app.id
                )
                
                notification = self.create_notification(
                    user_id=app.user_id,
                    type='next_phase_reminder_24h',
                    title=f"Tomorrow: {phase_type} - {app.job_title}",
                    message=f"Your {phase_type} for {app.job_title} at {company_name} is tomorrow. Check your email for preparation tips!",
                    application_id=app.id,
                    send_email=False  # Already sent above
                )
                notifications.append(notification)
                logger.info(f"Sent 24h reminder for application {app.id}")
            except Exception as e:
                logger.error(f"Failed to send 24h reminder for application {app.id}: {e}")
        
        # Check for next phases happening today (day-of reminder)
        today_phases = self.db.query(Application).filter(
            Application.next_phase_date == today
        ).all()
        
        for app in today_phases:
            user = self.db.query(User).filter(User.id == app.user_id).first()
            if not user:
                continue
            
            prefs = NotificationPreferences.get_or_create_default(self.db, app.user_id)
            
            if not prefs.should_send_notification('interview_reminders'):
                continue
            
            # Check if we already sent today's reminder
            existing = self.db.query(Notification).filter(
                and_(
                    Notification.user_id == app.user_id,
                    Notification.application_id == app.id,
                    Notification.type == 'next_phase_today',
                    Notification.sent_at >= datetime.utcnow() - timedelta(hours=12)
                )
            ).first()
            
            if existing:
                continue  # Already sent
            
            # Send day-of reminder
            phase_type = app.next_phase_type or "Interview"
            company_name = app.company.name if app.company else "the company"
            
            try:
                email_service.send_next_phase_today_email(
                    to_email=user.email,
                    user_name=user.full_name,
                    company=company_name,
                    position=app.job_title,
                    phase_type=phase_type,
                    phase_time="Check your calendar",
                    location="",
                    job_description=app.job_description or "",
                    application_id=app.id
                )
                
                notification = self.create_notification(
                    user_id=app.user_id,
                    type='next_phase_today',
                    title=f"TODAY: {phase_type} - {app.job_title}",
                    message=f"All the best for your {phase_type} today! {phase_type} for {app.job_title} at {company_name}.",
                    application_id=app.id,
                    send_email=False  # Already sent above
                )
                notifications.append(notification)
                logger.info(f"Sent day-of reminder for application {app.id}")
            except Exception as e:
                logger.error(f"Failed to send day-of reminder for application {app.id}: {e}")
        
        logger.info(f"Sent {len(notifications)} next phase reminders")
        return notifications


# Helper function to get notification service
def get_notification_service(db: Session) -> NotificationService:
    """Get notification service instance"""
    return NotificationService(db)
