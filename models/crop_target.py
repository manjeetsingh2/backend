"""
Crop Target model for agricultural planning and approval workflow
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class CropTarget(BaseModel):
    """Crop target submissions with approval workflow"""
    __tablename__ = 'crop_targets'
    
    # Basic information
    year = Column(Integer, nullable=False, index=True)
    season = Column(String(50), nullable=False, index=True)  # Kharif, Rabi, Summer
    
    # Location information
    district = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    village = Column(String(100), nullable=False, index=True)
    
    # Crop information
    crop_name = Column(String(100), nullable=False, index=True)
    crop_variety = Column(String(100), nullable=True)
    crop_category = Column(String(50), nullable=True, index=True)  # Agriculture, Horticulture
    
    # Target metrics
    cultivable_area = Column(Numeric(10, 3), nullable=False)  # in hectares
    target_area = Column(Numeric(10, 3), nullable=False)     # in hectares
    target_yield = Column(Numeric(10, 3), nullable=True)     # in tons/hectare
    expected_production = Column(Numeric(12, 3), nullable=True)  # in tons
    
    # Workflow fields
    status = Column(String(20), default='draft', nullable=False, index=True)
    # Status options: draft, submitted, pending, approved, rejected, cancelled
    
    # Submission tracking
    submitted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Approval tracking  
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Comments and remarks
    remarks = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)  # For BO internal use
    
    # Priority and categorization
    priority = Column(String(10), default='medium', nullable=False)  # low, medium, high
    
    # Relationships
    submitter = relationship("User", foreign_keys=[submitted_by], back_populates="crop_targets")
    approver = relationship("User", foreign_keys=[approved_by], back_populates="approved_targets")
    
    def submit_for_approval(self):
        """Change status from draft to submitted/pending"""
        if self.status == 'draft':
            from datetime import datetime
            self.status = 'submitted'
            self.submitted_at = datetime.utcnow()
    
    def approve(self, approver_id, remarks=None):
        """Approve the crop target"""
        from datetime import datetime
        self.status = 'approved'
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()
        if remarks:
            self.remarks = remarks
    
    def reject(self, approver_id, reason):
        """Reject the crop target with reason"""
        from datetime import datetime
        self.status = 'rejected'
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason
    
    @property
    def is_editable(self):
        """Check if target can be edited (only drafts)"""
        return self.status == 'draft'
    
    @property
    def is_pending_approval(self):
        """Check if target is pending approval"""
        return self.status in ['submitted', 'pending']
    
    def calculate_metrics(self):
        """Calculate derived metrics"""
        if self.target_area and self.target_yield:
            self.expected_production = float(self.target_area) * float(self.target_yield)
    
    def __repr__(self):
        return f"<CropTarget(crop={self.crop_name}, village={self.village}, status={self.status})>"