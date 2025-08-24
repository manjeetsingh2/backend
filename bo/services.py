from datetime import datetime
from app.database import db
from models.crop_target import CropTarget

class BOService:
    
    def get_pending_query(self, filters):
        query = CropTarget.query.filter(CropTarget.status == "submitted")
        
        for field, value in filters.items():
            if value:
                if hasattr(CropTarget, field):
                    column = getattr(CropTarget, field)
                    if isinstance(value, str) and field in ['crop', 'village', 'season', 'variety']:
                        query = query.filter(column.ilike(f"%{value}%"))
                    else:
                        query = query.filter(column == value)
        
        return query.order_by(CropTarget.created_at.desc())
    
    def approve_crop_target(self, crop_target_id, data, approver_id):
        crop_target = CropTarget.query.get(crop_target_id)
        
        if not crop_target:
            raise ValueError("Crop target not found")
        
        if crop_target.status != "submitted":
            raise ValueError("Only submitted targets can be approved/rejected")
        
        status = data['status']
        comments = data.get('rejection_comments')
        
        if status == 'rejected' and not comments:
            raise ValueError("Rejection comments required when rejecting")
        
        crop_target.status = status
        crop_target.approved_by = approver_id
        crop_target.approved_at = datetime.utcnow()
        crop_target.rejection_comments = comments if status == 'rejected' else None
        
        db.session.commit()
        
        return {"id": str(crop_target.id), "status": status}
    
    def get_summary(self, filters=None):
        query = CropTarget.query
        
        if filters:
            for field, value in filters.items():
                if value:
                    if hasattr(CropTarget, field):
                        column = getattr(CropTarget, field)
                        query = query.filter(column == value)
        
        # Status counts
        status_counts = query.with_entities(
            CropTarget.status,
            db.func.count(CropTarget.id)
        ).group_by(CropTarget.status).all()
        
        status_summary = {status: count for status, count in status_counts}
        
        # Total area by status
        total_areas = query.with_entities(
            CropTarget.status,
            db.func.sum(CropTarget.target_area)
        ).group_by(CropTarget.status).all()
        
        area_summary = {status: float(area or 0) for status, area in total_areas}
        
        return {
            "status_counts": status_summary,
            "area_by_status": area_summary
        }
