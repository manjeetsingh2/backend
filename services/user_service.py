"""
User service with authentication and user management using SQLAlchemy ORM
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models.user import User
from models.audit_log import AuditLog
from .base_service import BaseService
import uuid

class UserService(BaseService):
    """User service with authentication capabilities"""
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(
            User.username == username,
            User.is_active == True
        ).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()
    
    def authenticate(self, db: Session, username: str, password: str, 
                    ip_address: str = None, user_agent: str = None) -> Optional[User]:
        """Authenticate user with username and password"""
        user = self.get_by_username(db, username)
        
        if user and user.check_password(password):
            # Record successful login
            user.record_login()
            
            # Log successful authentication
            AuditLog.log_action(
                db_session=db,
                user_id=user.id,
                action="LOGIN_SUCCESS",
                resource_type="User",
                resource_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                description=f"User {username} logged in successfully"
            )
            
            db.commit()
            return user
        else:
            # Log failed authentication
            AuditLog.log_action(
                db_session=db,
                user_id=user.id if user else None,
                action="LOGIN_FAILED", 
                resource_type="User",
                ip_address=ip_address,
                user_agent=user_agent,
                description=f"Failed login attempt for username: {username}",
                success=False
            )
            
            return None
    
    def create_user(self, db: Session, user_data: Dict[str, Any], 
                   created_by: uuid.UUID = None) -> User:
        """Create new user with password hashing"""
        # Extract password and hash it
        password = user_data.pop('password', None)
        if not password:
            raise ValueError("Password is required")
        
        # Create user
        user = User(**user_data)
        user.set_password(password)
        
        db.add(user)
        db.flush()
        
        # Log user creation
        if created_by:
            AuditLog.log_action(
                db_session=db,
                user_id=created_by,
                action="CREATE_USER",
                resource_type="User",
                resource_id=user.id,
                new_values=user_data,
                description=f"Created new user: {user.username}"
            )
        
        db.commit()
        db.refresh(user)
        return user
    
    def change_password(self, db: Session, user_id: uuid.UUID, 
                       old_password: str, new_password: str) -> bool:
        """Change user password with verification"""
        user = self.get(db, user_id)
        if not user:
            return False
        
        # Verify old password
        if not user.check_password(old_password):
            # Log failed password change
            AuditLog.log_action(
                db_session=db,
                user_id=user_id,
                action="PASSWORD_CHANGE_FAILED",
                resource_type="User",
                resource_id=user_id,
                description="Failed password change - incorrect old password",
                success=False
            )
            return False
        
        # Set new password
        user.set_password(new_password)
        
        # Log successful password change
        AuditLog.log_action(
            db_session=db,
            user_id=user_id,
            action="PASSWORD_CHANGED",
            resource_type="User", 
            resource_id=user_id,
            description="Password changed successfully"
        )
        
        db.commit()
        return True
    
    def get_users_by_role(self, db: Session, role: str, skip: int = 0, 
                         limit: int = 100) -> list[User]:
        """Get users filtered by role"""
        return db.query(User).filter(
            User.role == role,
            User.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_user_statistics(self, db: Session) -> Dict[str, Any]:
        """Get user statistics"""
        total_users = db.query(User).filter(User.is_active == True).count()
        vo_count = db.query(User).filter(User.role == 'VO', User.is_active == True).count()
        bo_count = db.query(User).filter(User.role == 'BO', User.is_active == True).count()
        
        return {
            "total_users": total_users,
            "village_officers": vo_count,
            "block_officers": bo_count,
            "active_users": total_users
        }

# Global service instance
user_service = UserService()