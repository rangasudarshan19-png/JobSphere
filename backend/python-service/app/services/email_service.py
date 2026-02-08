"""
Email Service for Job Tracker
Handles sending email notifications to users
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from typing import Optional, List
import logging
from app.config.settings import SUPPORT_EMAIL

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        """Initialize email service with SMTP configuration"""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "JobSphere")
        
        # Setup Jinja2 for email templates
        template_dir = Path(__file__).parent.parent.parent / "templates" / "emails"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        
        # Log template directory for debugging
        logger.info(f"[EMAIL] Email template directory: {template_dir}")
        logger.info(f"[EMAIL] Template directory exists: {template_dir.exists()}")
        
        # Check if SMTP is configured
        self.is_configured = bool(self.smtp_user and self.smtp_password)
        if not self.is_configured:
            logger.warning("[WARNING] Email service not configured. Set SMTP environment variables.")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[tuple]] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text fallback (optional)
            attachments: List of (filename, content) tuples (optional)
            
        Returns:
            bool: True if email sent successfully
        """
        if not self.is_configured:
            logger.error("[ERROR] Cannot send email: SMTP not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text content (fallback)
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)
            
            # Add HTML content
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)
            
            # Add attachments if any
            if attachments:
                for filename, content in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                    msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"[OK] Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to send email to {to_email}: {str(e)}")
            return False
    
    def render_template(self, template_name: str, **context) -> str:
        """Render email template with context data"""
        try:
            logger.info(f"[EMAIL] Rendering template: {template_name}")
            template = self.env.get_template(template_name)
            rendered = template.render(**context)
            logger.info(f"[EMAIL] Template rendered successfully, length: {len(rendered)} chars")
            return rendered
        except Exception as e:
            logger.error(f"[ERROR] Failed to render template {template_name}: {str(e)}")
            return ""
    
    def send_application_created_email(
        self,
        to_email: str,
        user_name: str,
        company: str,
        position: str,
        location: str = "Not specified",
        status: str = "Applied",
        user_notes: str = "",
        next_phase_date: Optional[str] = None,
        next_phase_type: Optional[str] = None,
        interview_date: Optional[str] = None,
        interview_time: Optional[str] = None,
        interview_details: str = "",
        application_id: Optional[int] = None
    ) -> bool:
        """Send email when application is created"""
        if not self.is_configured:
            logger.warning("Cannot send application created email: SMTP not configured")
            return False
        
        try:
            context = {
                'user_name': user_name,
                'company': company,
                'position': position,
                'location': location,
                'status': status,
                'user_notes': user_notes,
                'next_phase_date': next_phase_date,
                'next_phase_type': next_phase_type,
                'interview_date': interview_date,
                'interview_time': interview_time,
                'interview_details': interview_details,
                'application_id': application_id,
                'dashboard_link': "http://localhost:8000/frontend/dashboard.html"
            }
            
            logger.info(f"[EMAIL] Rendering application created template")
            html_content = self.render_template('application_created.html', **context)
            
            if not html_content or len(html_content) < 100:
                logger.warning(f"Template not found or empty, using fallback HTML")
                interview_section = ""
                if interview_date or interview_time:
                    interview_section = f"""
                    <div style="background-color: #f0fff4; border-left: 4px solid #38b2ac; padding: 15px; border-radius: 8px; margin: 15px 0;">
                        <h3 style="color: #2d3748; font-size: 16px; margin: 0 0 8px 0;">Interview Details</h3>
                        <p style="color: #4a5568; margin: 4px 0;">
                            <strong>Date:</strong> {interview_date or 'TBD'}<br/>
                            <strong>Time:</strong> {interview_time or 'TBD'}<br/>
                            {f'<strong>Details:</strong> {interview_details}' if interview_details else ''}
                        </p>
                    </div>
                    """
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Application Added</title>
                </head>
                <body style="margin: 0; padding: 0; font-family: Arial; background-color: #f7fafc;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 20px; text-align: center;">
                            <h1 style="color: white; margin: 0; font-size: 28px;">Application Added</h1>
                        </div>
                        <div style="padding: 40px 30px;">
                            <p style="color: #2d3748; font-size: 16px; margin: 0 0 20px 0;">Hi <strong>{user_name}</strong>, application added successfully!</p>
                            <div style="background-color: #edf2f7; padding: 20px; border-radius: 12px; margin: 20px 0;">
                                <h2 style="color: #2d3748; font-size: 18px; margin: 0 0 12px 0;">Application Details:</h2>
                                <p style="color: #4a5568; margin: 8px 0;"><strong>Company:</strong> {company}</p>
                                <p style="color: #4a5568; margin: 8px 0;"><strong>Position:</strong> {position}</p>
                                <p style="color: #4a5568; margin: 8px 0;"><strong>Location:</strong> {location}</p>
                                <p style="color: #4a5568; margin: 8px 0;"><strong>Status:</strong> {status}</p>
                            </div>
                            {interview_section}
                            {f'<div style="background-color: #fff5f5; border-left: 4px solid #f56565; padding: 15px; border-radius: 8px; margin: 15px 0;"><strong>Notes:</strong><p style="color: #4a5568; margin: 8px 0;">{user_notes}</p></div>' if user_notes else ''}
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="http://localhost:8000/frontend/dashboard.html" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: bold;">View in Dashboard</a>
                            </div>
                        </div>
                        <div style="background-color: #f7fafc; padding: 20px 30px; text-align: center; border-top: 2px solid #e2e8f0;">
                            <p style="color: #718096; font-size: 12px; margin: 0;">You're on your way to landing your dream job!</p>
                        </div>
                    </div>
                </body>
                </html>
                """
            
            subject = f"Application Added - {company} ({position})"
            result = self.send_email(to_email, subject, html_content)
            
            if result:
                logger.info(f"[OK] Application created email sent to {to_email}")
            else:
                logger.error(f"[ERROR] Failed to send application created email to {to_email}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending application created email: {str(e)}")
            return False
    
    def send_application_status_changed_email(
        self,
        to_email: str,
        user_name: str,
        company: str,
        position: str,
        old_status: str,
        new_status: str,
        location: str = "Not specified",
        interview_date: Optional[str] = None,
        interview_time: Optional[str] = None,
        interview_details: str = "",
        user_notes: str = "",
        application_id: Optional[int] = None
    ) -> bool:
        """Send email when application status changes"""
        if not self.is_configured:
            logger.warning("Cannot send status change email: SMTP not configured")
            return False
        
        try:
            context = {
                'user_name': user_name,
                'company': company,
                'position': position,
                'old_status': old_status,
                'new_status': new_status,
                'location': location,
                'interview_date': interview_date,
                'interview_time': interview_time,
                'interview_details': interview_details,
                'user_notes': user_notes,
                'application_id': application_id,
                'dashboard_link': "http://localhost:8000/frontend/dashboard.html"
            }
            
            logger.info(f"[EMAIL] Rendering status change template")
            html_content = self.render_template('application_status_changed.html', **context)
            
            if not html_content or len(html_content) < 100:
                logger.warning(f"Template not found or empty, using fallback HTML")
                
                new_color = "#667eea"
                interview_section = ""
                if interview_date or interview_time:
                    interview_section = f"""
                    <div style="background-color: #f0fff4; border-left: 4px solid #38b2ac; padding: 15px; border-radius: 8px; margin: 15px 0;">
                        <h3 style="color: #2d3748; font-size: 16px; margin: 0 0 8px 0;">Interview Details</h3>
                        <p style="color: #4a5568; margin: 4px 0;">
                            <strong>Date:</strong> {interview_date or 'TBD'}<br/>
                            <strong>Time:</strong> {interview_time or 'TBD'}<br/>
                            {f'<strong>Details:</strong> {interview_details}' if interview_details else ''}
                        </p>
                    </div>
                    """
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Status Update</title>
                </head>
                <body style="margin: 0; padding: 0; font-family: Arial; background-color: #f7fafc;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 20px; text-align: center;">
                            <h1 style="color: white; margin: 0; font-size: 28px;">Status Updated</h1>
                        </div>
                        <div style="padding: 40px 30px;">
                            <p style="color: #2d3748; font-size: 16px; margin: 0 0 20px 0;">Hi <strong>{user_name}</strong>, your application status has been updated!</p>
                            <div style="background-color: #edf2f7; padding: 20px; border-radius: 12px; margin: 20px 0;">
                                <h2 style="color: #2d3748; font-size: 18px; margin: 0 0 12px 0;">Application Details:</h2>
                                <p style="color: #4a5568; margin: 8px 0;"><strong>Company:</strong> {company}</p>
                                <p style="color: #4a5568; margin: 8px 0;"><strong>Position:</strong> {position}</p>
                                <p style="color: #4a5568; margin: 8px 0;"><strong>Location:</strong> {location}</p>
                            </div>
                            <div style="background: linear-gradient(135deg, {new_color} 0%, {new_color}cc 100%); color: white; padding: 25px; border-radius: 12px; margin: 20px 0; text-align: center;">
                                <p style="font-size: 14px; margin: 0 0 8px 0; opacity: 0.9;">Status Changed</p>
                                <div style="font-size: 24px; font-weight: bold; margin: 0;">{old_status.replace('_', ' ').title()} -> {new_status.replace('_', ' ').title()}</div>
                            </div>
                            {interview_section}
                            {f'<div style="background-color: #fff5f5; border-left: 4px solid #f56565; padding: 15px; border-radius: 8px; margin: 15px 0;"><strong>Notes:</strong><p style="color: #4a5568; margin: 8px 0;">{user_notes}</p></div>' if user_notes else ''}
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="http://localhost:8000/frontend/dashboard.html" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: bold;">View in Dashboard</a>
                            </div>
                        </div>
                        <div style="background-color: #f7fafc; padding: 20px 30px; text-align: center; border-top: 2px solid #e2e8f0;">
                            <p style="color: #718096; font-size: 12px; margin: 0;">Keep up the great work!</p>
                        </div>
                    </div>
                </body>
                </html>
                """
            
            subject = f"Status Update - {company} ({position})"
            result = self.send_email(to_email, subject, html_content)
            
            if result:
                logger.info(f"[OK] Status change email sent to {to_email}")
            else:
                logger.error(f"[ERROR] Failed to send status change email to {to_email}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending status change email: {str(e)}")
            return False
    
    def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """Send welcome email"""
        if not self.is_configured:
            logger.warning("[SKIP] Welcome email: SMTP not configured")
            return False
            
        try:
            subject = "Welcome to JobSphere!"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0;">Welcome to JobSphere! [EMOJI]</h1>
                    </div>
                    <div style="background: #f7fafc; padding: 30px; border-radius: 0 0 10px 10px;">
                        <p style="font-size: 16px;">Hi {user_name},</p>
                        <p>Welcome to JobSphere! We're excited to have you on board.</p>
                        <p>Your account has been successfully created. You can now:</p>
                        <ul style="line-height: 2;">
                            <li>Track your job applications</li>
                            <li>Search for jobs with AI-powered matching</li>
                            <li>Build professional resumes</li>
                            <li>Prepare for interviews</li>
                        </ul>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="http://127.0.0.1:8000/frontend/login.html" 
                               style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                Get Started
                            </a>
                        </div>
                        <p style="color: #718096; font-size: 14px; margin-top: 30px;">
                            If you have any questions, feel free to reach out to our support team.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
Welcome to JobSphere!

Hi {user_name},

Welcome to JobSphere! We're excited to have you on board.

Your account has been successfully created. You can now:
- Track your job applications
- Search for jobs with AI-powered matching
- Build professional resumes
- Prepare for interviews

Get started: http://127.0.0.1:8000/frontend/login.html

If you have any questions, feel free to reach out to our support team.
            """
            
            return self.send_email(to_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            return False
    
    def send_otp_email(self, to_email: str, otp: str, validity_minutes: int = 10, max_attempts: int = 3) -> bool:
        """Send OTP verification email"""
        if not self.is_configured:
            logger.warning("[SKIP] OTP email: SMTP not configured")
            return False
            
        try:
            subject = "JobSphere - Email Verification Code"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0;">Email Verification</h1>
                    </div>
                    <div style="background: #f7fafc; padding: 30px; border-radius: 0 0 10px 10px;">
                        <p style="font-size: 16px;">Your verification code is:</p>
                        <div style="background: white; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; border: 2px dashed #667eea;">
                            <span style="font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 8px;">{otp}</span>
                        </div>
                        <p style="color: #718096;">
                            This code will expire in <strong>{validity_minutes} minutes</strong>.
                        </p>
                        <p style="color: #718096; font-size: 14px; margin-top: 30px;">
                            If you didn't request this code, please ignore this email.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
JobSphere - Email Verification

Your verification code is: {otp}

This code will expire in {validity_minutes} minutes.

If you didn't request this code, please ignore this email.
            """
            
            result = self.send_email(to_email, subject, html_content, text_content)
            
            if result:
                logger.info(f"[SYMBOL] OTP email sent successfully to {to_email}")
            else:
                logger.error(f"[SYMBOL] Failed to send OTP email to {to_email}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error sending OTP email: {str(e)}")
            return False
    
    def send_next_phase_today_email(
        self,
        to_email: str,
        user_name: str,
        company: str,
        position: str,
        phase_type: str,
        phase_time: str,
        location: str = "",
        job_description: str = "",
        user_notes: str = "",
        application_id: int = None
    ) -> bool:
        """Send email for interview happening today"""
        logger.info("[SKIP] Next phase today email: not fully implemented")
        return False
    
    def send_announcement_email(
        self,
        to_email: str,
        user_name: str,
        announcement_title: str,
        announcement_content: str
    ) -> bool:
        """Send announcement email to user"""
        if not self.is_configured:
            logger.warning("Cannot send announcement email: SMTP not configured")
            return False
        
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f7fafc;">
                <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 28px;">[EMOJI] New Announcement</h1>
                    </div>
                    <div style="padding: 30px;">
                        <p style="color: #2d3748; font-size: 16px; margin-bottom: 20px;">Hi {user_name},</p>
                        <div style="background-color: #edf2f7; border-left: 4px solid #667eea; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <h2 style="color: #2d3748; margin: 0 0 15px 0; font-size: 20px;">{announcement_title}</h2>
                            <div style="color: #4a5568; font-size: 15px; line-height: 1.6;">{announcement_content}</div>
                        </div>
                        <p style="color: #718096; font-size: 14px; margin-top: 20px;">Stay tuned for more updates!</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="http://localhost:8000/frontend/dashboard.html" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: bold;">Go to Dashboard</a>
                        </div>
                    </div>
                    <div style="background-color: #f7fafc; padding: 20px 30px; text-align: center; border-top: 2px solid #e2e8f0;">
                        <p style="color: #718096; font-size: 12px; margin: 0;">JobSphere Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = f"[EMOJI] {announcement_title}"
            result = self.send_email(to_email, subject, html_content)
            
            if result:
                logger.info(f"[OK] Announcement email sent to {to_email}")
            else:
                logger.error(f"[ERROR] Failed to send announcement email to {to_email}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending announcement email: {str(e)}")
            return False
    
    def broadcast_announcement(
        self,
        users: List[tuple],
        announcement_title: str,
        announcement_content: str
    ) -> dict:
        """Send announcement to multiple users
        
        Args:
            users: List of (email, name) tuples
            announcement_title: Title of the announcement
            announcement_content: Content of the announcement
            
        Returns:
            dict: Statistics with success_count and failed_count
        """
        if not self.is_configured:
            logger.warning("Cannot broadcast announcement: SMTP not configured")
            return {"success_count": 0, "failed_count": len(users), "total": len(users)}
        
        success_count = 0
        failed_count = 0
        
        for email, name in users:
            try:
                if self.send_announcement_email(email, name, announcement_title, announcement_content):
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error sending to {email}: {str(e)}")
                failed_count += 1
        
        logger.info(f"[BROADCAST] Sent {success_count}/{len(users)} announcement emails successfully")
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total": len(users)
        }
    
    def send_account_suspended_email(
        self,
        to_email: str,
        user_name: str,
        reason: str = "violation of terms of service"
    ) -> bool:
        """Send email when account is suspended"""
        if not self.is_configured:
            logger.warning("Cannot send account suspended email: SMTP not configured")
            return False
        
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f7fafc;">
                <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <div style="background: linear-gradient(135deg, #f56565 0%, #c53030 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 28px;">[SYMBOL]️ Account Suspended</h1>
                    </div>
                    <div style="padding: 30px;">
                        <p style="color: #2d3748; font-size: 16px; margin-bottom: 20px;">Hi {user_name},</p>
                        <div style="background-color: #fff5f5; border-left: 4px solid #f56565; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <p style="color: #2d3748; font-size: 15px; line-height: 1.6; margin: 0;">Your account has been temporarily suspended due to {reason}.</p>
                        </div>
                        <p style="color: #4a5568; font-size: 15px; line-height: 1.6;">During this suspension period:</p>
                        <ul style="color: #4a5568; font-size: 15px; line-height: 1.8; margin: 10px 0;">
                            <li>You will not be able to access your account</li>
                            <li>Your applications are saved and will remain secure</li>
                            <li>You can contact support for more information</li>
                        </ul>
                        <p style="color: #4a5568; font-size: 15px; line-height: 1.6; margin-top: 20px;">If you believe this is a mistake or would like to appeal this decision, please contact our support team.</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="mailto:{support_email}" style="display: inline-block; background: #f56565; color: white; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: bold;">Contact Support</a>
                        </div>
                    </div>
                    <div style="background-color: #f7fafc; padding: 20px 30px; text-align: center; border-top: 2px solid #e2e8f0;">
                        <p style="color: #718096; font-size: 12px; margin: 0;">JobSphere Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Format the email with support email
            html_content = html_content.format(support_email=SUPPORT_EMAIL)
            
            subject = "[SYMBOL]️ Your Account Has Been Suspended"
            result = self.send_email(to_email, subject, html_content)
            
            if result:
                logger.info(f"[OK] Account suspended email sent to {to_email}")
            else:
                logger.error(f"[ERROR] Failed to send account suspended email to {to_email}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending account suspended email: {str(e)}")
            return False
    
    def send_account_activated_email(
        self,
        to_email: str,
        user_name: str
    ) -> bool:
        """Send email when account is activated/reactivated"""
        if not self.is_configured:
            logger.warning("Cannot send account activated email: SMTP not configured")
            return False
        
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f7fafc;">
                <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <div style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 28px;">[SYMBOL] Account Activated</h1>
                    </div>
                    <div style="padding: 30px;">
                        <p style="color: #2d3748; font-size: 16px; margin-bottom: 20px;">Hi {user_name},</p>
                        <div style="background-color: #f0fff4; border-left: 4px solid #48bb78; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <p style="color: #2d3748; font-size: 15px; line-height: 1.6; margin: 0;">Great news! Your account has been activated and you now have full access to JobSphere.</p>
                        </div>
                        <p style="color: #4a5568; font-size: 15px; line-height: 1.6;">You can now:</p>
                        <ul style="color: #4a5568; font-size: 15px; line-height: 1.8; margin: 10px 0;">
                            <li>Access your dashboard and all applications</li>
                            <li>Track your job search progress</li>
                            <li>Use all platform features</li>
                            <li>Continue managing your career journey</li>
                        </ul>
                        <p style="color: #4a5568; font-size: 15px; line-height: 1.6; margin-top: 20px;">Welcome back! We're glad to have you with us.</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="http://localhost:8000/frontend/login.html" style="display: inline-block; background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: bold;">Login to Dashboard</a>
                        </div>
                    </div>
                    <div style="background-color: #f7fafc; padding: 20px 30px; text-align: center; border-top: 2px solid #e2e8f0;">
                        <p style="color: #718096; font-size: 12px; margin: 0;">JobSphere Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = "[SYMBOL] Your Account Has Been Activated"
            result = self.send_email(to_email, subject, html_content)
            
            if result:
                logger.info(f"[OK] Account activated email sent to {to_email}")
            else:
                logger.error(f"[ERROR] Failed to send account activated email to {to_email}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending account activated email: {str(e)}")
            return False
    
    def send_account_deleted_email(
        self,
        to_email: str,
        user_name: str
    ) -> bool:
        """Send email when account is deleted"""
        if not self.is_configured:
            logger.warning("Cannot send account deleted email: SMTP not configured")
            return False
        
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f7fafc;">
                <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <div style="background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 28px;">[EMOJI] Account Deleted</h1>
                    </div>
                    <div style="padding: 30px;">
                        <p style="color: #2d3748; font-size: 16px; margin-bottom: 20px;">Hi {user_name},</p>
                        <div style="background-color: #edf2f7; border-left: 4px solid #4a5568; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <p style="color: #2d3748; font-size: 15px; line-height: 1.6; margin: 0;">Your JobSphere account has been permanently deleted as per administrator action.</p>
                        </div>
                        <p style="color: #4a5568; font-size: 15px; line-height: 1.6;">What this means:</p>
                        <ul style="color: #4a5568; font-size: 15px; line-height: 1.8; margin: 10px 0;">
                            <li>Your account and all associated data have been removed</li>
                            <li>All job applications have been permanently deleted</li>
                            <li>You will no longer receive emails from us</li>
                            <li>You can create a new account anytime if you wish to return</li>
                        </ul>
                        <p style="color: #4a5568; font-size: 15px; line-height: 1.6; margin-top: 20px;">If you believe this was done in error or have questions, please contact our support team immediately.</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="mailto:{support_email}" style="display: inline-block; background: #4a5568; color: white; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: bold;">Contact Support</a>
                        </div>
                        <p style="color: #718096; font-size: 14px; text-align: center; margin-top: 30px;">We're sorry to see you go. Thank you for using JobSphere.</p>
                    </div>
                    <div style="background-color: #f7fafc; padding: 20px 30px; text-align: center; border-top: 2px solid #e2e8f0;">
                        <p style="color: #718096; font-size: 12px; margin: 0;">JobSphere Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Format the email with support email
            html_content = html_content.format(support_email=SUPPORT_EMAIL)
            
            subject = "Account Deletion Confirmation"
            result = self.send_email(to_email, subject, html_content)
            
            if result:
                logger.info(f"[OK] Account deleted email sent to {to_email}")
            else:
                logger.error(f"[ERROR] Failed to send account deleted email to {to_email}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending account deleted email: {str(e)}")
            return False


# Global email service instance
email_service = EmailService()
