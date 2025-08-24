"""
Authentication service with comprehensive security features
Implements secure authentication, session management, and account security
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from .base import BaseService, ServiceResult
from models.user import User, UserRole
from models.audit import AuditLog, AuditAction
from core.security import security_manager
from core.exceptions import SecurityException, ValidationException


class AuthService(BaseService[User]):
    """Authentication service with advanced security features"""
    
    def __init__(self, db_session: Session):
        super().__init__(User, db_session)
    
    def login(self, username: str, password: str, 
              ip_address: str = None, user_agent: str = None) -> ServiceResult:
        """
        Authenticate user with comprehensive security checks
        """
        try:
            # Find user by username
            user = self.db.query(User).filter(
                User.username == username,
                User.is_active == True
            ).first()
            
            if not user:
                # Log failed login attempt
                self._log_failed_login(username, "User not found", ip_address)
                return ServiceResult.error_result("Invalid username or password")
            
            # Check if account is locked
            if user.is_locked:
                time_remaining = user.locked_until - datetime.utcnow()
                return ServiceResult.error_result(
                    f"Account locked. Try again in {int(time_remaining.total_seconds() / 60)} minutes"
                )
            
            # Verify password
            if not security_manager.verify_password(password, user.password_hash):
                user.record_failed_login()
                self.db.commit()
                
                self._log_failed_login(user.username, "Invalid password", ip_address)
                return ServiceResult.error_result("Invalid username or password")
            
            # Successful login
            user.record_successful_login()
            self.db.commit()
            
            # Generate JWT token
            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "role": user.role.value,
                "login_time": datetime.utcnow().isoformat()
            }
            
            access_token = security_manager.create_access_token(token_data)
            
            # Log successful login
            self._log_successful_login(user, ip_address, user_agent)
            
            return ServiceResult.success_result(
                data={
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": user.get_profile_summary()
                },
                message="Login successful"
            )
            
        except Exception as e:
            return ServiceResult.error_result(f"Authentication error: {str(e)}")
    
    def register(self, username: str, password: str, role: str,
                 email: str = None, full_name: str = None,
                 created_by: str = None) -> ServiceResult:
        """
        Register new user with validation
        """
        try:
            # Validate input
            validation_result = self._validate_registration_data(
                username, password, role, email
            )
            if not validation_result.success:
                return validation_result
            
            # Check if username exists
            existing_user = self.db.query(User).filter(
                User.username == username
            ).first()
            
            if existing_user:
                return ServiceResult.error_result("Username already exists")
            
            # Check if email exists (if provided)
            if email:
                existing_email = self.db.query(User).filter(
                    User.email == email
                ).first()
                
                if existing_email:
                    return ServiceResult.error_result("Email already registered")
            
            # Hash password
            password_hash = security_manager.hash_password(password)
            
            # Create user
            user_data = {
                "username": username,
                "password_hash": password_hash,
                "role": UserRole(role),
                "email": email,
                "full_name": full_name,
                "is_active": True,
                "is_verified": False if email else True  # Email verification required
            }
            
            create_result = self.create(user_data, created_by)
            
            if create_result.success:
                # Log user creation
                self._log_user_creation(username, role, created_by)
            
            return create_result
            
        except Exception as e:
            return ServiceResult.error_result(f"Registration error: {str(e)}")
    
    def change_password(self, user_id: str, current_password: str, 
                       new_password: str) -> ServiceResult:
        """
        Change user password with security validation
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return ServiceResult.error_result("User not found")
            
            # Verify current password
            if not security_manager.verify_password(current_password, user.password_hash):
                return ServiceResult.error_result("Current password is incorrect")
            
            # Validate new password
            if len(new_password) < 8:
                return ServiceResult.error_result("Password must be at least 8 characters long")
            
            if new_password == current_password:
                return ServiceResult.error_result("New password must be different from current password")
            
            # Hash and set new password
            user.password_hash = security_manager.hash_password(new_password)
            user.password_changed_at = datetime.utcnow()
            
            self.db.commit()
            
            # Log password change
            self._log_password_change(user)
            
            return ServiceResult.success_result(message="Password changed successfully")
            
        except Exception as e:
            return ServiceResult.error_result(f"Password change error: {str(e)}")
    
    def logout(self, user_id: str, ip_address: str = None) -> ServiceResult:
        """
        Handle user logout (for audit trail)
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if user:
                # Log logout
                self._log_logout(user, ip_address)
            
            return ServiceResult.success_result(message="Logout successful")
            
        except Exception as e:
            return ServiceResult.error_result(f"Logout error: {str(e)}")
    
    def unlock_account(self, user_id: str, unlocked_by: str) -> ServiceResult:
        """
        Unlock user account (admin function)
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return ServiceResult.error_result("User not found")
            
            user.unlock_account()
            self.db.commit()
            
            # Log account unlock
            self._log_account_unlock(user, unlocked_by)
            
            return ServiceResult.success_result(message="Account unlocked successfully")
            
        except Exception as e:
            return ServiceResult.error_result(f"Account unlock error: {str(e)}")
    
    def _validate_registration_data(self, username: str, password: str, 
                                  role: str, email: str = None) -> ServiceResult:
        """Validate registration data"""
        errors = []
        
        # Username validation
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        
        if not username.isalnum():
            errors.append("Username must contain only alphanumeric characters")
        
        # Password validation
        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        # Role validation
        try:
            UserRole(role)
        except ValueError:
            errors.append(f"Invalid role: {role}")
        
        # Email validation (basic)
        if email and "@" not in email:
            errors.append("Invalid email format")
        
        if errors:
            return ServiceResult.error_result("Validation failed", errors)
        
        return ServiceResult.success_result()
    
    # Audit logging methods
    def _log_successful_login(self, user: User, ip_address: str = None, 
                            user_agent: str = None) -> None:
        """Log successful login"""
        audit_log = AuditLog.create_log(
            action=AuditAction.LOGIN,
            resource_type="user",
            user_id=str(user.id),
            username=user.username,
            resource_id=str(user.id),
            description=f"Successful login for user {user.username}",
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(audit_log)
    
    def _log_failed_login(self, username: str, reason: str, 
                         ip_address: str = None) -> None:
        """Log failed login attempt"""
        audit_log = AuditLog.create_log(
            action=AuditAction.LOGIN,
            resource_type="user",
            username=username,
            description=f"Failed login attempt for {username}: {reason}",
            ip_address=ip_address,
            business_context={"login_success": False, "failure_reason": reason}
        )
        self.db.add(audit_log)
    
    def _log_logout(self, user: User, ip_address: str = None) -> None:
        """Log user logout"""
        audit_log = AuditLog.create_log(
            action=AuditAction.LOGOUT,
            resource_type="user",
            user_id=str(user.id),
            username=user.username,
            resource_id=str(user.id),
            description=f"User {user.username} logged out",
            ip_address=ip_address
        )
        self.db.add(audit_log)
    
    def _log_user_creation(self, username: str, role: str, 
                          created_by: str = None) -> None:
        """Log new user creation"""
        audit_log = AuditLog.create_log(
            action=AuditAction.CREATE,
            resource_type="user",
            user_id=created_by,
            description=f"New user created: {username} with role {role}",
            business_context={"new_username": username, "new_user_role": role}
        )
        self.db.add(audit_log)
    
    def _log_password_change(self, user: User) -> None:
        """Log password change"""
        audit_log = AuditLog.create_log(
            action=AuditAction.UPDATE,
            resource_type="user",
            user_id=str(user.id),
            username=user.username,
            resource_id=str(user.id),
            description=f"Password changed for user {user.username}"
        )
        self.db.add(audit_log)
    
    def _log_account_unlock(self, user: User, unlocked_by: str) -> None:
        """Log account unlock"""
        audit_log = AuditLog.create_log(
            action=AuditAction.UPDATE,
            resource_type="user",
            user_id=unlocked_by,
            resource_id=str(user.id),
            description=f"Account unlocked for user {user.username}",
            business_context={"action": "account_unlock", "target_user": user.username}
        )
        self.db.add(audit_log)