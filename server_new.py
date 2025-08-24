#!/usr/bin/env python3
"""
AGRI Crop Target Management System - FastAPI Backend with PostgreSQL & SQLAlchemy ORM
Production-ready backend with proper ORM models, services, and authentication
"""

import os
import sys
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

# FastAPI imports
from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# SQLAlchemy imports
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# JWT imports
import jwt
from passlib.context import CryptContext

# Pydantic models for request/response validation
from pydantic import BaseModel, Field

# Import our custom modules
from core.config import settings
from core.database import get_db, init_database
from models.user import User
from models.crop_target import CropTarget
from services.user_service import user_service
from services.crop_target_service import crop_target_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AGRI Crop Target Management API",
    description="Agricultural crop target planning and approval system with PostgreSQL & SQLAlchemy ORM",
    version="2.0.0",
    docs_url="/docs" if settings.is_development() else None,
    redoc_url="/redoc" if settings.is_development() else None
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    **settings.get_cors_config()
)

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic schemas for API validation
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=6)

class LoginResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class CropTargetCreate(BaseModel):
    year: int = Field(..., ge=2020, le=2030)
    season: str = Field(..., min_length=1, max_length=50)
    district: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    village: str = Field(..., min_length=1, max_length=100)
    crop_name: str = Field(..., min_length=1, max_length=100)
    crop_variety: Optional[str] = Field(None, max_length=100)
    cultivable_area: float = Field(..., gt=0, le=10000)
    target_area: float = Field(..., gt=0, le=10000)
    target_yield: Optional[float] = Field(None, gt=0, le=100)
    remarks: Optional[str] = Field(None, max_length=1000)

class CropTargetUpdate(BaseModel):
    year: Optional[int] = Field(None, ge=2020, le=2030)
    season: Optional[str] = Field(None, min_length=1, max_length=50)
    village: Optional[str] = Field(None, min_length=1, max_length=100)
    crop_name: Optional[str] = Field(None, min_length=1, max_length=100)
    crop_variety: Optional[str] = Field(None, max_length=100)
    cultivable_area: Optional[float] = Field(None, gt=0, le=10000)
    target_area: Optional[float] = Field(None, gt=0, le=10000)
    target_yield: Optional[float] = Field(None, gt=0, le=100)
    remarks: Optional[str] = Field(None, max_length=1000)

class ApprovalRequest(BaseModel):
    action: str = Field(..., regex="^(approve|reject)$")
    remarks: Optional[str] = Field(None, max_length=1000)
    rejection_reason: Optional[str] = Field(None, max_length=1000)

# Authentication utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and extract user ID"""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(user_id: str = Depends(verify_token), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    try:
        user_uuid = uuid.UUID(user_id)
        user = user_service.get(db, user_uuid)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID")
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

def require_role(allowed_roles: List[str]):
    """Dependency to require specific roles"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Required role: {' or '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "AGRI API is running with PostgreSQL & SQLAlchemy ORM",
        "environment": settings.environment,
        "database": "PostgreSQL",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    try:
        # Get client info
        ip_address = req.client.host
        user_agent = req.headers.get("user-agent")
        
        # Authenticate user
        user = user_service.authenticate(
            db, 
            request.username, 
            request.password,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not user:
            return LoginResponse(
                success=False,
                message="Invalid username or password",
                data={}
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return LoginResponse(
            success=True,
            message="Login successful",
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.jwt_expire_minutes * 60,
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": user.role,
                    "district": user.district,
                    "village": user.village
                }
            }
        )
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        return LoginResponse(
            success=False,
            message="Login failed due to server error",
            data={}
        )

@app.get("/api/v1/users/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    user_data = current_user.to_dict()
    return {
        "success": True,
        "data": user_data
    }

# Village Officer (VO) Routes
@app.get("/api/v1/vo/dashboard/summary")
async def get_vo_summary(
    year: Optional[int] = Query(None),
    season: Optional[str] = Query(None),
    current_user: User = Depends(require_role(["VO"])),
    db: Session = Depends(get_db)
):
    """Get VO dashboard summary"""
    summary = crop_target_service.get_dashboard_summary(
        db, 
        user_id=current_user.id,
        year=year,
        season=season
    )
    
    return {
        "success": True,
        "data": summary
    }

@app.get("/api/v1/vo/crop-targets/my-submissions")
async def get_my_submissions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    season: Optional[str] = Query(None),
    current_user: User = Depends(require_role(["VO"])),
    db: Session = Depends(get_db)
):
    """Get VO's crop target submissions"""
    filters = {}
    if status:
        filters['status'] = status
    if year:
        filters['year'] = year
    if season:
        filters['season'] = season
    
    skip = (page - 1) * per_page
    targets = crop_target_service.get_by_submitter(
        db,
        current_user.id,
        skip=skip,
        limit=per_page,
        filters=filters
    )
    
    total = len(crop_target_service.get_by_submitter(db, current_user.id, filters=filters))
    
    return {
        "success": True,
        "data": {
            "items": [target.to_dict() for target in targets],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
    }

@app.post("/api/v1/vo/crop-targets")
async def create_crop_target(
    target_data: CropTargetCreate,
    current_user: User = Depends(require_role(["VO"])),
    db: Session = Depends(get_db)
):
    """Create new crop target"""
    try:
        # Add submitter info
        create_data = target_data.dict()
        create_data['district'] = current_user.district
        create_data['state'] = current_user.state
        
        target = crop_target_service.create_crop_target(
            db, 
            create_data, 
            current_user.id
        )
        
        return {
            "success": True,
            "message": "Crop target created successfully",
            "data": target.to_dict()
        }
    
    except IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        raise HTTPException(status_code=400, detail="Invalid data provided")
    except Exception as e:
        logger.error(f"Error creating crop target: {e}")
        raise HTTPException(status_code=500, detail="Failed to create crop target")

@app.put("/api/v1/vo/crop-targets/{target_id}")
async def update_crop_target(
    target_id: uuid.UUID,
    target_data: CropTargetUpdate,
    current_user: User = Depends(require_role(["VO"])),
    db: Session = Depends(get_db)
):
    """Update crop target (only drafts)"""
    target = crop_target_service.get(db, target_id)
    
    if not target or target.submitted_by != current_user.id:
        raise HTTPException(status_code=404, detail="Crop target not found")
    
    if not target.is_editable:
        raise HTTPException(status_code=400, detail="Cannot edit submitted crop target")
    
    try:
        updated_target = crop_target_service.update(
            db, 
            target_id, 
            target_data.dict(exclude_unset=True),
            current_user.id
        )
        
        return {
            "success": True,
            "message": "Crop target updated successfully",
            "data": updated_target.to_dict()
        }
    
    except Exception as e:
        logger.error(f"Error updating crop target: {e}")
        raise HTTPException(status_code=500, detail="Failed to update crop target")

@app.post("/api/v1/vo/crop-targets/{target_id}/submit")
async def submit_crop_target(
    target_id: uuid.UUID,
    current_user: User = Depends(require_role(["VO"])),
    db: Session = Depends(get_db)
):
    """Submit crop target for approval"""
    target = crop_target_service.submit_for_approval(db, target_id, current_user.id)
    
    if not target:
        raise HTTPException(status_code=404, detail="Crop target not found or cannot be submitted")
    
    return {
        "success": True,
        "message": "Crop target submitted for approval",
        "data": target.to_dict()
    }

# Block Officer (BO) Routes
@app.get("/api/v1/bo/dashboard/summary")
async def get_bo_summary(
    year: Optional[int] = Query(None),
    season: Optional[str] = Query(None),
    current_user: User = Depends(require_role(["BO"])),
    db: Session = Depends(get_db)
):
    """Get BO dashboard summary"""
    summary = crop_target_service.get_dashboard_summary(
        db,
        year=year,
        season=season
    )
    
    return {
        "success": True,
        "data": summary
    }

@app.get("/api/v1/bo/crop-targets/pending")
async def get_pending_approvals(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    year: Optional[int] = Query(None),
    season: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    village: Optional[str] = Query(None),
    crop_name: Optional[str] = Query(None),
    current_user: User = Depends(require_role(["BO"])),
    db: Session = Depends(get_db)
):
    """Get pending crop targets for approval"""
    filters = {}
    if year:
        filters['year'] = year
    if season:
        filters['season'] = season
    if district:
        filters['district'] = district
    if village:
        filters['village'] = village
    if crop_name:
        filters['crop_name'] = crop_name
    
    skip = (page - 1) * per_page
    targets = crop_target_service.get_pending_approvals(
        db,
        skip=skip,
        limit=per_page,
        filters=filters
    )
    
    total = len(crop_target_service.get_pending_approvals(db, filters=filters))
    
    return {
        "success": True,
        "data": {
            "items": [target.to_dict() for target in targets],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
    }

@app.post("/api/v1/bo/crop-targets/{target_id}/approve")
async def approve_crop_target(
    target_id: uuid.UUID,
    approval_data: ApprovalRequest,
    current_user: User = Depends(require_role(["BO"])),
    db: Session = Depends(get_db)
):
    """Approve or reject crop target"""
    try:
        if approval_data.action == "approve":
            target = crop_target_service.approve_target(
                db, 
                target_id, 
                current_user.id,
                approval_data.remarks
            )
            message = "Crop target approved successfully"
        elif approval_data.action == "reject":
            if not approval_data.rejection_reason:
                raise HTTPException(status_code=400, detail="Rejection reason is required")
            
            target = crop_target_service.reject_target(
                db,
                target_id,
                current_user.id,
                approval_data.rejection_reason
            )
            message = "Crop target rejected successfully"
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        if not target:
            raise HTTPException(status_code=404, detail="Crop target not found or not pending approval")
        
        return {
            "success": True,
            "message": message,
            "data": target.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing approval: {e}")
        raise HTTPException(status_code=500, detail="Failed to process approval")

# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"success": False, "message": str(exc)}
    )

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=400,
        content={"success": False, "message": "Data integrity constraint violated"}
    )

# Application startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Starting AGRI API with PostgreSQL & SQLAlchemy ORM")
    try:
        init_database()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server_new:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development(),
        log_level=settings.log_level.lower()
    )