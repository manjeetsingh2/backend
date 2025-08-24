"""
API routes module
Modular route organization with dependency injection
"""

from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .crop_targets import router as crop_targets_router
from .dashboard import router as dashboard_router
from .audit import router as audit_router
from .health import router as health_router


def create_api_router() -> APIRouter:
    """
    Create main API router with all sub-routers
    Implements modular routing structure
    """
    api_router = APIRouter()
    
    # Health and system endpoints
    api_router.include_router(
        health_router,
        tags=["Health"]
    )
    
    # Authentication endpoints
    api_router.include_router(
        auth_router,
        prefix="/auth",
        tags=["Authentication"]
    )
    
    # User management endpoints
    api_router.include_router(
        users_router,
        prefix="/users",
        tags=["Users"]
    )
    
    # Crop target endpoints
    api_router.include_router(
        crop_targets_router,
        prefix="/crop-targets", 
        tags=["Crop Targets"]
    )
    
    # Dashboard endpoints
    api_router.include_router(
        dashboard_router,
        prefix="/dashboard",
        tags=["Dashboard"]
    )
    
    # Audit endpoints
    api_router.include_router(
        audit_router,
        prefix="/audit",
        tags=["Audit"]
    )
    
    return api_router