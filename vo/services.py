from datetime import datetime
from app.database import db
from models.crop_target import CropTarget

class VOService:
    
    def create_crop_target(self, data, user_id):
        status = data.pop('status', 'draft')
        
        crop_target = CropTarget(
            **data,
            submitted_by=user_id,
            status=status,
            submitted_at=datetime.utcnow() if status == 'submitted' else None
        )
        
        db.session.add(crop_target)
        db.session.commit()
        
        return {"id": str(crop_target.id), "status": crop_target.status}
    
    def get_my_submissions_query(self, user_id, filters):
        query = CropTarget.query.filter(CropTarget.submitted_by == user_id)
        
        # Apply filters
        for field, value in filters.items():
            if value:
                if hasattr(CropTarget, field):
                    column = getattr(CropTarget, field)
                    if isinstance(value, str) and field in ['crop', 'village', 'season', 'variety']:
                        query = query.filter(column.ilike(f"%{value}%"))
                    else:
                        query = query.filter(column == value)
        
        return query.order_by(CropTarget.created_at.desc())
    
    def get_crop_target_by_id(self, crop_target_id, user_id):
        crop_target = CropTarget.query.filter_by(
            id=crop_target_id, 
            submitted_by=user_id
        ).first()
        
        if not crop_target:
            raise ValueError("Crop target not found")
        
        return crop_target
    
    def update_crop_target(self, crop_target_id, data, user_id):
        crop_target = self.get_crop_target_by_id(crop_target_id, user_id)
        
        if not crop_target.can_edit:
            raise ValueError("Cannot edit this crop target")
        
        for key, value in data.items():
            if hasattr(crop_target, key):
                setattr(crop_target, key, value)
        
        if crop_target.status == "rejected":
            crop_target.rejection_comments = None
        
        db.session.commit()
        return {"id": str(crop_target.id)}
    
    def resubmit_crop_target(self, crop_target_id, user_id):
        crop_target = self.get_crop_target_by_id(crop_target_id, user_id)
        
        if crop_target.status not in ["draft", "rejected"]:
            raise ValueError("Cannot resubmit this crop target")
        
        crop_target.status = "submitted"
        crop_target.submitted_at = datetime.utcnow()
        crop_target.rejection_comments = None
        
        db.session.commit()
        return {"id": str(crop_target.id)}
    
    def delete_crop_target(self, crop_target_id, user_id):
        crop_target = self.get_crop_target_by_id(crop_target_id, user_id)
        
        if not crop_target.can_delete:
            raise ValueError("Cannot delete this crop target")
        
        db.session.delete(crop_target)
        db.session.commit()
    
    def get_summary(self, user_id, year=None, season=None):
        query = CropTarget.query.filter(CropTarget.submitted_by == user_id)
        
        if year:
            query = query.filter(CropTarget.year == year)
        if season:
            query = query.filter(CropTarget.season == season)
        
        total_area = db.session.query(
            db.func.coalesce(db.func.sum(CropTarget.target_area), 0)
        ).filter(query.whereclause).scalar() or 0
        
        return {"total_target_area_entered": float(total_area)}
