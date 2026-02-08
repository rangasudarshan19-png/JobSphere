from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta
from typing import Optional, Dict, Any

from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.models.user import User
from app.utils.database import get_db
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.services.email_service import email_service
from app.services.otp_service import otp_service
from app.config.settings import SUPPORT_EMAIL, ACCOUNT_SUSPENDED_MESSAGE
from pydantic import BaseModel, EmailStr
import logging

logger = logging.getLogger(__name__)


class ProfileUpdateRequest(BaseModel):
    """Request model for updating user profile information."""
    full_name: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Request model for changing user password."""
    current_password: str
    new_password: str


class SendOTPRequest(BaseModel):
    """Request model for sending OTP to email."""
    email: EmailStr


class SendVerificationRequest(BaseModel):
    """Request model for sending verification email."""
    email: EmailStr
    full_name: str


class VerifyOTPRequest(BaseModel):
    """Request model for verifying OTP code."""
    email: EmailStr
    otp: str
    purpose: Optional[str] = "registration"  # "registration" or "password_reset"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract token from credentials
    token = credentials.credentials
    
    email = decode_access_token(token)
    if email is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)), 
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token with optional authentication.
    
    Allows anonymous access by returning None if no token is provided
    or if the token is invalid. Used for endpoints that work with or
    without authentication.
    
    Args:
        credentials: Optional JWT token from Authorization header
        db: Database session for user lookup
        
    Returns:
        User object if authenticated, None otherwise
        
    Example:
        user = get_current_user_optional(credentials, db)
        if user:
            # Show personalized content
        else:
            # Show public content
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        email = decode_access_token(token)
        if email is None:
            return None
        
        user = db.query(User).filter(User.email == email).first()
        return user
    except Exception:
        return None


@router.post("/send-verification")
def send_verification(request: SendVerificationRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Send OTP verification code for new user signup.
    
    This is Step 1 of the registration process. Generates and sends
    a one-time password (OTP) to the provided email address. The OTP
    is valid for 10 minutes and must be verified before completing
    registration.
    
    Args:
        request: Contains email and full_name for the new user
        db: Database session for checking existing users
        
    Returns:
        dict: Success message and timeout information
        
    Raises:
        HTTPException 400: If email already exists in database
        HTTPException 500: If email sending fails
        
    Example:
        POST /api/auth/send-verification
        {
            "email": "newuser@example.com",
            "full_name": "John Doe"
        }
        
        Response:
        {
            "message": "Verification code sent to newuser@example.com",
            "expires_in_minutes": 10
        }
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Generate and send OTP
        otp = otp_service.create_otp(request.email)
        
        # Send OTP email with user's name
        email_sent = email_service.send_otp_email(
            to_email=request.email,
            otp=otp,
            validity_minutes=10,
            max_attempts=3
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification code"
            )
        
        logger.info(f"[EMOJI] Verification code sent to {request.email} for {request.full_name}")
        
        return {
            "success": True,
            "message": f"Verification code sent to {request.email}",
            "email": request.email,
            "validity_minutes": 10
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending verification code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification code: {str(e)}"
        )


@router.post("/send-otp")
def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    """
    Send OTP to email for verification
    Used for password reset flow
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Generate and send OTP
        otp = otp_service.create_otp(request.email)
        
        # Send OTP email
        email_sent = email_service.send_otp_email(
            to_email=request.email,
            otp=otp,
            validity_minutes=10,
            max_attempts=3
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email"
            )
        
        logger.info(f"[EMOJI] OTP sent to {request.email}")
        
        return {
            "success": True,
            "message": "OTP sent to your email",
            "email": request.email,
            "validity_minutes": 10
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {str(e)}"
        )


@router.post("/verify-otp")
def verify_otp(request: VerifyOTPRequest):
    """
    Verify OTP
    Step 2 of registration/password reset process
    For password reset: marks as verified (keeps OTP for password reset step)
    For registration: removes OTP after verification
    """
    try:
        # For password reset, mark as verified instead of deleting
        mark_verified = (request.purpose == "password_reset")
        
        success, error_message = otp_service.verify_otp(
            request.email, 
            request.otp, 
            mark_verified=mark_verified
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        logger.info(f"[SYMBOL] OTP verified for {request.email} (purpose: {request.purpose})")
        
        return {
            "success": True,
            "message": "Email verified successfully",
            "email": request.email,
            "verified": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify OTP: {str(e)}"
        )


@router.post("/resend-otp")
def resend_otp(request: SendOTPRequest):
    """Resend OTP to email"""
    try:
        # Generate new OTP
        otp = otp_service.resend_otp(request.email)
        
        if not otp:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate OTP"
            )
        
        # Send OTP email
        email_sent = email_service.send_otp_email(
            to_email=request.email,
            otp=otp,
            validity_minutes=10,
            max_attempts=3
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email"
            )
        
        logger.info(f"[EMOJI] OTP resent to {request.email}")
        
        return {
            "success": True,
            "message": "New OTP sent to your email",
            "email": request.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend OTP: {str(e)}"
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with email verification"""
    try:
        # Normalize email to enforce case-insensitive uniqueness
        normalized_email = user.email.strip().lower()

        # Check if user already exists (case-insensitive)
        existing_user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # If verification code is provided, verify it
        if user.verification_code:
            success, error_message = otp_service.verify_otp(
                normalized_email,
                user.verification_code,
                mark_verified=False  # Delete OTP after successful verification
            )
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message or "Invalid verification code"
                )
            
            logger.info(f"[SYMBOL] Email verified for {normalized_email}")
        
        # Create new user (regular user by default)
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=normalized_email,
            password_hash=hashed_password,
            full_name=user.full_name,
            phone=user.phone,
            is_admin=0  # Regular user by default
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Send welcome email (non-blocking)
        try:
            logger.info(f"[EMOJI] Sending welcome email to {db_user.email}")
            email_service.send_welcome_email(
                to_email=db_user.email,
                user_name=db_user.full_name or "User"
            )
        except Exception as e:
            # Don't fail registration if email fails
            logger.error(f"Failed to send welcome email: {str(e)}")
        
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error during user registration: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.post("/login", response_model=Token)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    # Normalize email for case-insensitive lookup
    normalized_email = user.email.strip().lower()

    # Check if user exists (case-insensitive)
    db_user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if account is suspended
    if db_user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{ACCOUNT_SUSPENDED_MESSAGE} Contact: {SUPPORT_EMAIL}"
        )
    
    # Verify password
    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Mark first_login as false on first login
    if db_user.first_login:
        db_user.first_login = 0
        db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "full_name": db_user.full_name}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information including admin status"""
    return current_user


@router.put("/update-profile", response_model=UserResponse)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    try:
        if request.full_name:
            current_user.full_name = request.full_name
        if request.phone:
            current_user.phone = request.phone
        
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )
    
    try:
        # Update password
        current_user.password_hash = get_password_hash(request.new_password)
        db.commit()
        return {"message": "Password changed successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}"
        )


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Send OTP to email for password reset
    Step 1 of forgot password process
    """
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            # Don't reveal if email exists for security
            # But still return success to avoid email enumeration
            logger.warning(f"Password reset requested for non-existent email: {request.email}")
            return {
                "success": True,
                "message": "If your email is registered, you will receive an OTP shortly",
                "email": request.email
            }
        
        # Generate and send OTP
        otp = otp_service.create_otp(request.email)
        
        # Send OTP email
        email_sent = email_service.send_otp_email(
            to_email=request.email,
            otp=otp,
            validity_minutes=10,
            max_attempts=3
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email"
            )
        
        logger.info(f"[EMOJI] Password reset OTP sent to {request.email}")
        
        return {
            "success": True,
            "message": "If your email is registered, you will receive an OTP shortly",
            "email": request.email,
            "validity_minutes": 10
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in forgot password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process request: {str(e)}"
        )


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using OTP
    Step 3 of forgot password process (after OTP verification)
    """
    try:
        # Check if OTP was verified (not verifying again, just checking the flag)
        if not otp_service.is_otp_verified(request.email):
            # If not verified, try to verify the OTP one more time
            success, error_message = otp_service.verify_otp(request.email, request.otp, mark_verified=True)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message
                )
        
        # Check if user exists
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate new password
        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        # Update password
        user.password_hash = get_password_hash(request.new_password)
        db.commit()
        
        # Clean up OTP after successful password reset
        otp_service.complete_otp_verification(request.email)
        
        logger.info(f"[SYMBOL] Password reset successful for {request.email}")
        
        return {
            "success": True,
            "message": "Password reset successfully. You can now login with your new password."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )
