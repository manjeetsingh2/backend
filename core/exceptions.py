"""
Custom exception classes for the AGRI application
Centralized error handling with proper HTTP status codes
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AGRIException(Exception):
    """Base exception class for AGRI application"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AGRIException):
    """Exception for data validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        self.field = field
        super().__init__(message, details)


class SecurityException(AGRIException):
    """Exception for security-related errors"""
    pass


class DatabaseException(AGRIException):
    """Exception for database-related errors"""
    pass


class BusinessLogicException(AGRIException):
    """Exception for business logic violations"""
    pass


class ResourceNotFoundException(AGRIException):
    """Exception for resource not found errors"""
    pass


class PermissionDeniedException(AGRIException):
    """Exception for permission denied errors"""
    pass


# HTTP Exception Factory Functions
def create_http_exception(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Factory function to create HTTP exceptions with consistent format"""
    return HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "details": details or {},
            "success": False
        }
    )


def validation_error(message: str, field: Optional[str] = None) -> HTTPException:
    """Create a 422 validation error"""
    details = {"field": field} if field else {}
    return create_http_exception(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        message,
        details
    )


def unauthorized_error(message: str = "Authentication required") -> HTTPException:
    """Create a 401 unauthorized error"""
    return create_http_exception(
        status.HTTP_401_UNAUTHORIZED,
        message
    )


def forbidden_error(message: str = "Insufficient permissions") -> HTTPException:
    """Create a 403 forbidden error"""
    return create_http_exception(
        status.HTTP_403_FORBIDDEN,
        message
    )


def not_found_error(resource: str) -> HTTPException:
    """Create a 404 not found error"""
    return create_http_exception(
        status.HTTP_404_NOT_FOUND,
        f"{resource} not found"
    )


def conflict_error(message: str) -> HTTPException:
    """Create a 409 conflict error"""
    return create_http_exception(
        status.HTTP_409_CONFLICT,
        message
    )


def internal_server_error(message: str = "Internal server error") -> HTTPException:
    """Create a 500 internal server error"""
    return create_http_exception(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        message
    )


# Exception Handler Mapping
EXCEPTION_HANDLERS = {
    ValidationException: lambda exc: validation_error(exc.message, exc.field),
    SecurityException: lambda exc: unauthorized_error(exc.message),
    PermissionDeniedException: lambda exc: forbidden_error(exc.message),
    ResourceNotFoundException: lambda exc: not_found_error(exc.message),
    BusinessLogicException: lambda exc: create_http_exception(
        status.HTTP_400_BAD_REQUEST, exc.message
    ),
    DatabaseException: lambda exc: internal_server_error(
        "Database operation failed"
    ),
}


def handle_exception(exc: Exception) -> HTTPException:
    """Central exception handler that converts custom exceptions to HTTP exceptions"""
    if type(exc) in EXCEPTION_HANDLERS:
        return EXCEPTION_HANDLERS[type(exc)](exc)
    
    # Generic handler for unexpected exceptions
    return internal_server_error(f"Unexpected error: {str(exc)}")