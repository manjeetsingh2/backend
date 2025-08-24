"""
Health check and system status endpoints
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.config import get_settings
from core.database import get_db_session, DatabaseManager

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint with system information"""
    settings = get_settings()
    return {
        "message": "AGRI - Crop Target Management System",
        "status": "running",
        "database": "PostgreSQL",
        "protocol": settings.protocol.upper(),
        "port": settings.port,
        "https_enabled": settings.use_https,
        "version": settings.app_version,
        "environment": settings.environment
    }


@router.get("/health")
async def health_check(db: Session = Depends(get_db_session)):
    """
    Comprehensive health check endpoint
    Returns system status and database connectivity
    """
    settings = get_settings()
    
    # Check database health
    db_health = DatabaseManager.health_check()
    
    # Get database statistics
    db_stats = DatabaseManager.get_stats()
    
    return {
        "status": "ok" if db_health["status"] == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "protocol": settings.protocol.upper(),
            "port": settings.port,
            "https_enabled": settings.use_https
        },
        "database": db_health,
        "statistics": db_stats,
        "cors_origins": settings.cors_origins
    }


@router.get("/version")
async def get_version():
    """Get application version information"""
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "build_date": datetime.utcnow().isoformat()  # Mock build date
    }


@router.get("/status")
async def get_system_status(db: Session = Depends(get_db_session)):
    """
    Get detailed system status for monitoring
    """
    try:
        # Database statistics
        db_stats = DatabaseManager.get_stats()
        
        # System metrics (mock data - would come from actual monitoring)
        system_metrics = {
            "uptime": "99.9%",
            "memory_usage": "45%",
            "cpu_usage": "23%",
            "disk_usage": "67%",
            "active_connections": 12
        }
        
        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_stats,
            "system_metrics": system_metrics,
            "service_status": {
                "api": "operational",
                "database": "operational",
                "authentication": "operational",
                "file_storage": "operational"
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "service_status": {
                "api": "operational",
                "database": "error",
                "authentication": "unknown",
                "file_storage": "unknown"
            }
        }