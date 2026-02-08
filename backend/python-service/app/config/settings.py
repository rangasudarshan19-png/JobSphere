"""
Centralized configuration for application-wide settings with validation
"""
import os
from typing import Literal
from dotenv import load_dotenv
from pydantic import EmailStr, field_validator, Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """
    Application settings with validation using Pydantic.
    
    All settings are validated on application startup to catch
    configuration errors early. Uses environment variables with
    sensible defaults for development.
    """
    
    # ============ ENVIRONMENT ============
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    DEBUG: bool = Field(
        default=True,
        description="Enable debug mode"
    )
    
    # ============ EMAIL CONFIGURATION ============
    SUPPORT_EMAIL: EmailStr = Field(
        default="jobtrackerbysudarshan@gmail.com",
        description="Primary support email address"
    )
    SUPPORT_NAME: str = Field(
        default="JobSphere Support",
        description="Support contact name"
    )
    
    @property
    def SUPPORT_EMAIL_DISPLAY(self) -> str:
        """Formatted support email for display."""
        return f"{self.SUPPORT_NAME} <{self.SUPPORT_EMAIL}>"
    
    # ============ APPLICATION SETTINGS ============
    APP_NAME: str = Field(
        default="JobSphere",
        description="Application name"
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version"
    )
    APP_URL: str = Field(
        default="http://127.0.0.1:8000",
        description="Application base URL"
    )
    
    @field_validator("APP_URL")
    @classmethod
    def validate_app_url(cls, v):
        """Ensure APP_URL is a valid URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("APP_URL must start with http:// or https://")
        return v.rstrip("/")
    
    # ============ SECURITY SETTINGS ============
    MAX_LOGIN_ATTEMPTS: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum login attempts before lockout"
    )
    LOCKOUT_DURATION_MINUTES: int = Field(
        default=15,
        ge=1,
        le=60,
        description="Account lockout duration in minutes"
    )
    SESSION_TIMEOUT_MINUTES: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="Session timeout in minutes"
    )
    
    # JWT Settings
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        min_length=32,
        description="JWT secret key (min 32 characters)"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,
        ge=15,
        description="Access token expiration in minutes"
    )
    
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v, info):
        """Warn if using default secret in production."""
        if info.data.get("ENVIRONMENT") == "production" and v == "your-secret-key-change-in-production":
            raise ValueError("Must set custom JWT_SECRET_KEY in production environment")
        return v
    
    # ============ DATABASE SETTINGS ============
    DATABASE_URL: str = Field(
        default="sqlite:///./job_tracker.db",
        description="Database connection URL"
    )
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v, info):
        """Warn if using SQLite in production."""
        env = info.data.get("ENVIRONMENT")
        if env == "production" and v.startswith("sqlite"):
            raise ValueError("SQLite is not recommended for production. Use PostgreSQL or MySQL.")
        return v
    
    # ============ API SETTINGS ============
    API_RATE_LIMIT_PER_MINUTE: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="API rate limit per minute per IP"
    )
    
    # ============ MESSAGE TEMPLATES ============
    @property
    def ACCOUNT_SUSPENDED_MESSAGE(self) -> str:
        """Account suspension message template."""
        return "Your account has been suspended. Please contact support for assistance."
    
    @property
    def ACCOUNT_SUSPENDED_CONTACT(self) -> str:
        """Account suspension contact info."""
        return f"Contact: {self.SUPPORT_EMAIL}"
    
    @property
    def ACCOUNT_DELETION_PENDING(self) -> str:
        """Account deletion pending message."""
        return "Your account deletion request is being processed."
    
    # ============ EXTERNAL API KEYS ============
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key for AI features"
    )
    
    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v, info):
        """Warn if Gemini API key is missing in production."""
        env = info.data.get("ENVIRONMENT")
        if env == "production" and not v:
            raise ValueError("GEMINI_API_KEY is required for production environment")
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra environment variables


# Create global settings instance
settings = Settings()


# ============ BACKWARD COMPATIBILITY ============
# Keep old variables for existing code
SUPPORT_EMAIL = settings.SUPPORT_EMAIL
SUPPORT_NAME = settings.SUPPORT_NAME
SUPPORT_EMAIL_DISPLAY = settings.SUPPORT_EMAIL_DISPLAY
APP_NAME = settings.APP_NAME
APP_VERSION = settings.APP_VERSION
APP_URL = settings.APP_URL
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOCKOUT_DURATION_MINUTES = settings.LOCKOUT_DURATION_MINUTES
SESSION_TIMEOUT_MINUTES = settings.SESSION_TIMEOUT_MINUTES
ACCOUNT_SUSPENDED_MESSAGE = settings.ACCOUNT_SUSPENDED_MESSAGE
ACCOUNT_SUSPENDED_CONTACT = settings.ACCOUNT_SUSPENDED_CONTACT
ACCOUNT_DELETION_PENDING = settings.ACCOUNT_DELETION_PENDING
API_RATE_LIMIT_PER_MINUTE = settings.API_RATE_LIMIT_PER_MINUTE


def validate_configuration() -> dict:
    """
    Validate all configuration settings on application startup.
    
    Returns:
        dict: Configuration validation results with status and warnings
    
    Raises:
        ValueError: If critical configuration is invalid
    """
    results = {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "warnings": [],
        "info": {}
    }
    
    # Check environment-specific requirements
    if settings.ENVIRONMENT == "production":
        if settings.DEBUG:
            results["warnings"].append("DEBUG mode is enabled in production")
        
        if not settings.APP_URL.startswith("https://"):
            results["warnings"].append("APP_URL should use HTTPS in production")
    
    # Store non-sensitive config info
    results["info"] = {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "database": "PostgreSQL" if "postgresql" in settings.DATABASE_URL else "SQLite",
        "rate_limit": f"{settings.API_RATE_LIMIT_PER_MINUTE} req/min"
    }
    
    return results
