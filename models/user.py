"""
User model with role-based access control
"""
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import relationship
from .base import BaseModel
import bcrypt

class User(BaseModel):
    """User model for VO and BO roles"""
    __tablename__ = 'users'
    
    # Authentication fields
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True, index=True)
    password_hash = Column(String(128), nullable=False)
    
    # Profile fields
    full_name = Column(String(200), nullable=False)
    role = Column(String(10), nullable=False, index=True)  # 'VO' or 'BO'
    phone_number = Column(String(20), nullable=True)
    
    # Location fields
    district = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    village = Column(String(100), nullable=True, index=True)
    
    # Activity tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(String(10), default='0', nullable=False)
    
    # Additional info
    address = Column(Text, nullable=True)
    
    # Relationships
    crop_targets = relationship("CropTarget", foreign_keys="CropTarget.submitted_by", back_populates="submitter")
    approved_targets = relationship("CropTarget", foreign_keys="CropTarget.approved_by", back_populates="approver")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def record_login(self):
        """Record successful login"""
        from datetime import datetime
        self.last_login = datetime.utcnow()
        current_count = int(self.login_count) if self.login_count.isdigit() else 0
        self.login_count = str(current_count + 1)
    
    def to_dict(self):
        """Convert to dictionary without sensitive data"""
        data = super().to_dict()
        data.pop('password_hash', None)  # Never include password hash
        return data
    
    def __repr__(self):
        return f"<User(username={self.username}, role={self.role})>"