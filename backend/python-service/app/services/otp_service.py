"""
OTP Service for email verification
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class OTPService:
    def __init__(self):
        """Initialize OTP service with in-memory storage (can be moved to Redis for production)"""
        self.otp_storage = {}  # {email: {'otp': '123456', 'expires_at': datetime, 'attempts': 0}}
        self.max_attempts = 3
        self.otp_validity_minutes = 10
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    def create_otp(self, email: str) -> str:
        """
        Create and store OTP for an email
        
        Args:
            email: User's email address
            
        Returns:
            str: Generated OTP
        """
        otp = self.generate_otp()
        expires_at = datetime.now() + timedelta(minutes=self.otp_validity_minutes)
        
        self.otp_storage[email] = {
            'otp': otp,
            'expires_at': expires_at,
            'attempts': 0,
            'created_at': datetime.now()
        }
        
        logger.info(f"OTP created for {email} (expires in {self.otp_validity_minutes} min)")
        return otp
    
    def verify_otp(self, email: str, otp: str, mark_verified: bool = False) -> tuple[bool, str]:
        """
        Verify OTP for an email
        
        Args:
            email: User's email address
            otp: OTP to verify
            mark_verified: If True, mark as verified instead of deleting (for forgot password flow)
            
        Returns:
            tuple[bool, str]: (Success status, Error message if any)
        """
        # Check if OTP exists for email
        if email not in self.otp_storage:
            return False, "No OTP found for this email. Please request a new one."
        
        stored_data = self.otp_storage[email]
        
        # Check if OTP has expired
        if datetime.now() > stored_data['expires_at']:
            del self.otp_storage[email]
            return False, "OTP has expired. Please request a new one."
        
        # Check attempts
        if stored_data['attempts'] >= self.max_attempts:
            del self.otp_storage[email]
            return False, "Too many failed attempts. Please request a new OTP."
        
        # Verify OTP
        if stored_data['otp'] == otp:
            if mark_verified:
                # Mark as verified but keep in storage for password reset
                stored_data['verified'] = True
                logger.info(f"[SYMBOL] OTP verified and marked for {email}")
            else:
                # Success - remove OTP (for registration flow)
                del self.otp_storage[email]
                logger.info(f"[SYMBOL] OTP verified successfully for {email}")
            return True, ""
        else:
            # Increment attempts
            stored_data['attempts'] += 1
            remaining = self.max_attempts - stored_data['attempts']
            logger.warning(f"[SYMBOL] Invalid OTP for {email}. Attempts remaining: {remaining}")
            return False, f"Invalid OTP. {remaining} attempts remaining."
    
    def is_otp_verified(self, email: str) -> bool:
        """
        Check if OTP has been verified for this email
        
        Args:
            email: User's email address
            
        Returns:
            bool: True if OTP is verified and not expired
        """
        if email not in self.otp_storage:
            return False
        
        stored_data = self.otp_storage[email]
        
        # Check if verified
        if not stored_data.get('verified', False):
            return False
        
        # Check if expired
        if datetime.now() > stored_data['expires_at']:
            del self.otp_storage[email]
            return False
        
        return True
    
    def complete_otp_verification(self, email: str):
        """
        Complete OTP verification and remove from storage
        Called after password reset is complete
        
        Args:
            email: User's email address
        """
        if email in self.otp_storage:
            del self.otp_storage[email]
            logger.info(f"[EMOJI]️ OTP verification completed and cleaned up for {email}")
    
    def resend_otp(self, email: str) -> Optional[str]:
        """
        Resend OTP (create new one)
        
        Args:
            email: User's email address
            
        Returns:
            Optional[str]: New OTP if successful
        """
        # Delete old OTP if exists
        if email in self.otp_storage:
            del self.otp_storage[email]
        
        return self.create_otp(email)
    
    def cleanup_expired_otps(self):
        """Clean up expired OTPs from storage"""
        now = datetime.now()
        expired_emails = [
            email for email, data in self.otp_storage.items()
            if now > data['expires_at']
        ]
        
        for email in expired_emails:
            del self.otp_storage[email]
            logger.info(f"[EMOJI]️ Cleaned up expired OTP for {email}")
        
        return len(expired_emails)


# Global OTP service instance
otp_service = OTPService()
