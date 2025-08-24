"""
Security management module
Centralized authentication, authorization, and security utilities
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import get_settings
from .exceptions import SecurityException, ValidationException


class SecurityManager:
    """Centralized security operations manager"""
    
    def __init__(self):
        self.settings = get_settings()
        self.pwd_context = CryptContext(
            schemes=["bcrypt"], 
            deprecated="auto",
            bcrypt__rounds=self.settings.password_hash_rounds
        )
        self.security_scheme = HTTPBearer()
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        if not password or len(password) < 6:
            raise ValidationException("Password must be at least 6 characters long")
        
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            raise SecurityException(f"Password verification failed: {str(e)}")
    
    def create_access_token(self, user_data: Dict[str, Any], 
                          expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = user_data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.settings.jwt_expiration_hours)
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode, 
                self.settings.jwt_secret_key, 
                algorithm=self.settings.jwt_algorithm
            )
            return encoded_jwt
        except Exception as e:
            raise SecurityException(f"Token creation failed: {str(e)}")
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials) -> str:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                credentials.credentials, 
                self.settings.jwt_secret_key, 
                algorithms=[self.settings.jwt_algorithm]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise SecurityException("Invalid token: missing user ID")
            return user_id
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def get_token_dependency(self):
        """FastAPI dependency for token verification"""
        def verify_token_dependency(
            credentials: HTTPAuthorizationCredentials = Depends(self.security_scheme)
        ) -> str:
            return self.verify_token(credentials)
        return verify_token_dependency
    
    @staticmethod
    def require_roles(allowed_roles: list):
        """Decorator for role-based access control"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # This would be implemented with the user service
                return func(*args, **kwargs)
            return wrapper
        return decorator


class PermissionManager:
    """Role and permission management"""
    
    ROLES = {
        "VO": {
            "name": "Village Officer",
            "permissions": [
                "crop_target:create",
                "crop_target:read_own",
                "crop_target:update_own",
                "dashboard:view_own"
            ]
        },
        "BO": {
            "name": "Block Officer", 
            "permissions": [
                "crop_target:read_all",
                "crop_target:approve",
                "crop_target:reject",
                "dashboard:view_all",
                "user:read"
            ]
        }
    }
    
    @classmethod
    def get_role_permissions(cls, role: str) -> list:
        """Get permissions for a specific role"""
        return cls.ROLES.get(role, {}).get("permissions", [])
    
    @classmethod
    def check_permission(cls, user_role: str, required_permission: str) -> bool:
        """Check if a user role has a specific permission"""
        user_permissions = cls.get_role_permissions(user_role)
        return required_permission in user_permissions
    
    @classmethod
    def validate_role(cls, role: str) -> bool:
        """Validate if a role exists"""
        return role in cls.ROLES


# Global security manager instance
security_manager = SecurityManager()
permission_manager = PermissionManager()