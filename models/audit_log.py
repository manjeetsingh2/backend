"""
Audit logging model for tracking all system activities
"""
from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from .base import BaseModel

class AuditLog(BaseModel):
    """Audit trail for all system activities"""
    __tablename__ = 'audit_logs'
    
    # User and session info
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    
    # Action details
    action = Column(String(100), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    resource_type = Column(String(50), nullable=False, index=True)  # User, CropTarget, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Change tracking
    old_values = Column(JSON, nullable=True)  # Previous state
    new_values = Column(JSON, nullable=True)  # New state
    
    # Request context
    ip_address = Column(INET, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    request_path = Column(String(500), nullable=True)
    
    # Additional context
    description = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)  # Additional contextual data
    
    # Outcome
    success = Column(String(10), default='true', nullable=False, index=True)  # true, false
    error_message = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    @classmethod
    def log_action(cls, db_session, user_id=None, action=None, resource_type=None, 
                   resource_id=None, old_values=None, new_values=None, 
                   ip_address=None, user_agent=None, description=None, success=True):
        """Create audit log entry"""
        audit_log = cls(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            success='true' if success else 'false'
        )
        db_session.add(audit_log)
        return audit_log
    
    def __repr__(self):
        return f"<AuditLog(action={self.action}, resource={self.resource_type}, user_id={self.user_id})>"