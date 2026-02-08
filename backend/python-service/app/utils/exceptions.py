"""
Custom exception classes for better error handling
"""
from fastapi import HTTPException, status


class JobTrackerException(Exception):
    """Base exception for Job Tracker application"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(JobTrackerException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(JobTrackerException):
    """Raised when user doesn't have permission"""
    def __init__(self, message: str = "You don't have permission to perform this action"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ResourceNotFoundError(JobTrackerException):
    """Raised when a resource is not found"""
    def __init__(self, resource: str, resource_id: int = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id {resource_id} not found"
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ValidationError(JobTrackerException):
    """Raised when validation fails"""
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class DuplicateResourceError(JobTrackerException):
    """Raised when trying to create a duplicate resource"""
    def __init__(self, resource: str, field: str = None):
        message = f"{resource} already exists"
        if field:
            message = f"{resource} with this {field} already exists"
        super().__init__(message, status.HTTP_409_CONFLICT)


class ExternalServiceError(JobTrackerException):
    """Raised when an external service fails"""
    def __init__(self, service: str, message: str = None):
        error_message = f"External service '{service}' failed"
        if message:
            error_message = f"{error_message}: {message}"
        super().__init__(error_message, status.HTTP_503_SERVICE_UNAVAILABLE)


class RateLimitError(JobTrackerException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS)
