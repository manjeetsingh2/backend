"""
Crop Target service with workflow management using SQLAlchemy ORM
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, extract
from models.crop_target import CropTarget
from models.user import User
from models.audit_log import AuditLog
from .base_service import BaseService
import uuid
from datetime import datetime, date

class CropTargetService(BaseService):
    """Crop target service with approval workflow"""
    
    def __init__(self):
        super().__init__(CropTarget)
    
    def get_with_users(self, db: Session, id: uuid.UUID) -> Optional[CropTarget]:
        """Get crop target with user relationships loaded"""
        return db.query(CropTarget).options(
            joinedload(CropTarget.submitter),
            joinedload(CropTarget.approver)
        ).filter(
            CropTarget.id == id,
            CropTarget.is_active == True
        ).first()
    
    def get_by_submitter(self, db: Session, submitter_id: uuid.UUID, 
                        skip: int = 0, limit: int = 100, 
                        filters: Dict[str, Any] = None) -> List[CropTarget]:
        """Get crop targets by submitter with filters"""
        query = db.query(CropTarget).options(
            joinedload(CropTarget.approver)
        ).filter(
            CropTarget.submitted_by == submitter_id,
            CropTarget.is_active == True
        )
        
        # Apply filters
        if filters:
            if filters.get('status'):
                query = query.filter(CropTarget.status == filters['status'])
            if filters.get('year'):
                query = query.filter(CropTarget.year == filters['year'])
            if filters.get('season'):
                query = query.filter(CropTarget.season == filters['season'])
            if filters.get('crop_name'):
                query = query.filter(CropTarget.crop_name.ilike(f"%{filters['crop_name']}%"))
        
        return query.order_by(CropTarget.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_pending_approvals(self, db: Session, skip: int = 0, limit: int = 100,
                             filters: Dict[str, Any] = None) -> List[CropTarget]:
        """Get crop targets pending approval"""
        query = db.query(CropTarget).options(
            joinedload(CropTarget.submitter)
        ).filter(
            CropTarget.status.in_(['submitted', 'pending']),
            CropTarget.is_active == True
        )
        
        # Apply filters
        if filters:
            if filters.get('year'):
                query = query.filter(CropTarget.year == filters['year'])
            if filters.get('season'):
                query = query.filter(CropTarget.season == filters['season'])
            if filters.get('district'):
                query = query.filter(CropTarget.district.ilike(f"%{filters['district']}%"))
            if filters.get('village'):
                query = query.filter(CropTarget.village.ilike(f"%{filters['village']}%"))
            if filters.get('crop_name'):
                query = query.filter(CropTarget.crop_name.ilike(f"%{filters['crop_name']}%"))
        
        return query.order_by(CropTarget.submitted_at.desc()).offset(skip).limit(limit).all()
    
    def create_crop_target(self, db: Session, target_data: Dict[str, Any], 
                          submitter_id: uuid.UUID) -> CropTarget:
        """Create new crop target"""
        # Set submitter
        target_data['submitted_by'] = submitter_id
        
        # Create target
        target = CropTarget(**target_data)
        target.calculate_metrics()
        
        db.add(target)
        db.flush()
        
        # Log creation
        AuditLog.log_action(
            db_session=db,
            user_id=submitter_id,
            action="CREATE",
            resource_type="CropTarget",
            resource_id=target.id,
            new_values=target_data,
            description=f"Created crop target for {target.crop_name}"
        )
        
        db.commit()
        db.refresh(target)
        return target
    
    def submit_for_approval(self, db: Session, target_id: uuid.UUID, 
                           submitter_id: uuid.UUID) -> Optional[CropTarget]:
        """Submit crop target for approval"""
        target = self.get(db, target_id)
        if not target or target.submitted_by != submitter_id:
            return None
        
        if target.status != 'draft':
            return None
        
        old_status = target.status
        target.submit_for_approval()
        
        # Log submission
        AuditLog.log_action(
            db_session=db,
            user_id=submitter_id,
            action="SUBMIT",
            resource_type="CropTarget",
            resource_id=target.id,
            old_values={"status": old_status},
            new_values={"status": target.status, "submitted_at": target.submitted_at},
            description=f"Submitted crop target {target.crop_name} for approval"
        )
        
        db.commit()
        db.refresh(target)
        return target
    
    def approve_target(self, db: Session, target_id: uuid.UUID, 
                      approver_id: uuid.UUID, remarks: str = None) -> Optional[CropTarget]:
        """Approve crop target"""
        target = self.get(db, target_id)
        if not target or not target.is_pending_approval:
            return None
        
        old_status = target.status
        target.approve(approver_id, remarks)
        
        # Log approval
        AuditLog.log_action(
            db_session=db,
            user_id=approver_id,
            action="APPROVE",
            resource_type="CropTarget", 
            resource_id=target.id,
            old_values={"status": old_status},
            new_values={"status": "approved", "approved_by": approver_id, "approved_at": target.approved_at},
            description=f"Approved crop target {target.crop_name}"
        )
        
        db.commit()
        db.refresh(target)
        return target
    
    def reject_target(self, db: Session, target_id: uuid.UUID, 
                     approver_id: uuid.UUID, reason: str) -> Optional[CropTarget]:
        """Reject crop target with reason"""
        target = self.get(db, target_id)
        if not target or not target.is_pending_approval:
            return None
        
        old_status = target.status
        target.reject(approver_id, reason)
        
        # Log rejection
        AuditLog.log_action(
            db_session=db,
            user_id=approver_id,
            action="REJECT",
            resource_type="CropTarget",
            resource_id=target.id,
            old_values={"status": old_status},
            new_values={"status": "rejected", "rejection_reason": reason},
            description=f"Rejected crop target {target.crop_name}: {reason}"
        )
        
        db.commit()
        db.refresh(target)
        return target
    
    def get_dashboard_summary(self, db: Session, user_id: uuid.UUID = None, 
                             year: int = None, season: str = None) -> Dict[str, Any]:
        """Get dashboard summary statistics"""
        base_query = db.query(CropTarget).filter(CropTarget.is_active == True)
        
        # Filter by user if provided (for VO dashboard)
        if user_id:
            base_query = base_query.filter(CropTarget.submitted_by == user_id)
        
        # Filter by year and season
        if year:
            base_query = base_query.filter(CropTarget.year == year)
        if season:
            base_query = base_query.filter(CropTarget.season == season)
        
        # Calculate statistics
        total_targets = base_query.count()
        pending_count = base_query.filter(CropTarget.status.in_(['submitted', 'pending'])).count()
        approved_count = base_query.filter(CropTarget.status == 'approved').count()
        rejected_count = base_query.filter(CropTarget.status == 'rejected').count()
        draft_count = base_query.filter(CropTarget.status == 'draft').count()
        
        # Area calculations
        total_cultivable_area = base_query.with_entities(
            func.sum(CropTarget.cultivable_area)
        ).scalar() or 0
        
        total_target_area = base_query.filter(
            CropTarget.status.in_(['approved', 'submitted', 'pending'])
        ).with_entities(
            func.sum(CropTarget.target_area)
        ).scalar() or 0
        
        expected_production = base_query.filter(
            CropTarget.status == 'approved'
        ).with_entities(
            func.sum(CropTarget.expected_production)
        ).scalar() or 0
        
        return {
            "total_targets": total_targets,
            "pending_approvals": pending_count,
            "approved_targets": approved_count,
            "rejected_targets": rejected_count,
            "draft_targets": draft_count,
            "total_cultivable_area": float(total_cultivable_area),
            "total_target_area": float(total_target_area),
            "expected_production": float(expected_production),
            "approval_rate": (approved_count / total_targets * 100) if total_targets > 0 else 0
        }
    
    def get_recent_submissions(self, db: Session, user_id: uuid.UUID = None, 
                              limit: int = 5) -> List[CropTarget]:
        """Get recent crop target submissions"""
        query = db.query(CropTarget).options(
            joinedload(CropTarget.approver)
        ).filter(CropTarget.is_active == True)
        
        if user_id:
            query = query.filter(CropTarget.submitted_by == user_id)
        
        return query.order_by(CropTarget.created_at.desc()).limit(limit).all()

# Global service instance
crop_target_service = CropTargetService()