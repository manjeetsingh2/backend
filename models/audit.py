"""
Audit log model for tracking system changes
Implements comprehensive audit trail functionality
"""

import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel, UUIDMixin


class AuditAction(enum.Enum):
    """Types of audit actions"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    SUBMIT = "SUBMIT"
    EXPORT = "EXPORT"


class AuditLog(BaseModel, UUIDMixin):
    """Comprehensive audit logging model"""
    
    __tablename__ = "audit_logs"
    
    # Who performed the action
    user_id = Column(
        UUID(as_uuid=True),
        nullable=True,  # Some actions might be system-generated
        index=True,
        comment="User who performed the action"
    )
    
    username = Column(
        String(80),
        nullable=True,
        index=True,
        comment="Username at time of action (for historical tracking)"
    )
    
    # What action was performed
    action = Column(
        Enum(AuditAction),
        nullable=False,
        index=True,
        comment="Type of action performed"
    )
    
    resource_type = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Type of resource affected (e.g., 'crop_target', 'user')"
    )
    
    resource_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID of the affected resource"
    )
    
    # When the action occurred
    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="When the action occurred"
    )
    
    # Additional context
    description = Column(
        Text,
        nullable=True,
        comment="Human-readable description of the action"
    )
    
    # Technical details
    old_values = Column(
        JSON,
        nullable=True,
        comment="Previous values before change (for UPDATE actions)"
    )
    
    new_values = Column(
        JSON,
        nullable=True,
        comment="New values after change (for CREATE/UPDATE actions)"
    )
    
    # Request context
    ip_address = Column(
        String(45),  # Support IPv6
        nullable=True,
        comment="IP address of the request"
    )
    
    user_agent = Column(
        String(500),
        nullable=True,
        comment="User agent string from the request"
    )
    
    session_id = Column(
        String(255),
        nullable=True,
        comment="Session identifier"
    )
    
    # System context
    api_endpoint = Column(
        String(255),
        nullable=True,
        comment="API endpoint that was called"
    )
    
    http_method = Column(
        String(10),
        nullable=True,
        comment="HTTP method (GET, POST, etc.)"
    )
    
    response_status = Column(
        String(10),
        nullable=True,
        comment="HTTP response status code"
    )
    
    duration_ms = Column(
        String(20),
        nullable=True,
        comment="Request duration in milliseconds"
    )
    
    # Business context
    business_context = Column(
        JSON,
        nullable=True,
        comment="Additional business-specific context"
    )
    
    # Class methods for creating audit logs
    @classmethod
    def create_log(cls, 
                   action: AuditAction,
                   resource_type: str,
                   user_id: str = None,
                   username: str = None,
                   resource_id: str = None,
                   description: str = None,
                   old_values: dict = None,
                   new_values: dict = None,
                   ip_address: str = None,
                   user_agent: str = None,
                   api_endpoint: str = None,
                   http_method: str = None,
                   **kwargs) -> 'AuditLog':
        """Create a new audit log entry"""
        
        return cls(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description or f"{action.value} {resource_type}",
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            api_endpoint=api_endpoint,
            http_method=http_method,
            business_context=kwargs if kwargs else None
        )
    
    @classmethod
    def log_user_action(cls, user_id: str, username: str, action: AuditAction,
                       resource_type: str, resource_id: str = None,
                       description: str = None, **context) -> 'AuditLog':
        """Log a user action with context"""
        return cls.create_log(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            username=username,
            resource_id=resource_id,
            description=description,
            **context
        )
    
    @classmethod
    def log_data_change(cls, user_id: str, username: str, 
                       resource_type: str, resource_id: str,
                       old_values: dict, new_values: dict,
                       action: AuditAction = AuditAction.UPDATE) -> 'AuditLog':
        """Log data changes with before/after values"""
        return cls.create_log(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            username=username,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            description=f"Updated {resource_type} {resource_id}"
        )
    
    def get_summary(self) -> dict:
        """Get audit log summary for API responses"""
        return {
            "id": str(self.id),
            "username": self.username,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "has_data_changes": bool(self.old_values or self.new_values)
        }
    
    def __repr__(self) -> str:
        return f"<AuditLog(action='{self.action.value}', resource='{self.resource_type}', user='{self.username}')>"