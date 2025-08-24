"""
Base service class with common CRUD operations using SQLAlchemy ORM
"""
from typing import List, Optional, Dict, Any, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from models.base import BaseModel
from models.audit_log import AuditLog
import uuid

ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseService:
    """Base service with common CRUD operations"""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    def get(self, db: Session, id: uuid.UUID) -> Optional[ModelType]:
        """Get single record by ID"""
        return db.query(self.model).filter(
            self.model.id == id,
            self.model.is_active == True
        ).first()
    
    def get_by_field(self, db: Session, field: str, value: Any) -> Optional[ModelType]:
        """Get single record by field"""
        return db.query(self.model).filter(
            getattr(self.model, field) == value,
            self.model.is_active == True
        ).first()
    
    def get_all(self, db: Session, skip: int = 0, limit: int = 100, 
                filters: Dict[str, Any] = None, order_by: str = None) -> List[ModelType]:
        """Get multiple records with filters and pagination"""
        query = db.query(self.model).filter(self.model.is_active == True)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.filter(getattr(self.model, field) == value)
        
        # Apply ordering
        if order_by:
            if order_by.startswith('-'):
                query = query.order_by(desc(getattr(self.model, order_by[1:])))
            else:
                query = query.order_by(asc(getattr(self.model, order_by)))
        else:
            query = query.order_by(desc(self.model.created_at))
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, db: Session, filters: Dict[str, Any] = None) -> int:
        """Count records with filters"""
        query = db.query(self.model).filter(self.model.is_active == True)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.filter(getattr(self.model, field) == value)
        
        return query.count()
    
    def create(self, db: Session, obj_data: Dict[str, Any], 
               user_id: uuid.UUID = None) -> ModelType:
        """Create new record"""
        # Remove None values
        create_data = {k: v for k, v in obj_data.items() if v is not None}
        
        # Create instance
        db_obj = self.model(**create_data)
        db.add(db_obj)
        db.flush()  # Get ID without committing
        
        # Log audit trail
        if user_id:
            AuditLog.log_action(
                db_session=db,
                user_id=user_id,
                action="CREATE",
                resource_type=self.model.__name__,
                resource_id=db_obj.id,
                new_values=create_data
            )
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(self, db: Session, id: uuid.UUID, obj_data: Dict[str, Any], 
               user_id: uuid.UUID = None) -> Optional[ModelType]:
        """Update existing record"""
        db_obj = self.get(db, id)
        if not db_obj:
            return None
        
        # Store old values for audit
        old_values = db_obj.to_dict()
        
        # Update fields
        update_data = {k: v for k, v in obj_data.items() if v is not None}
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.flush()
        
        # Log audit trail
        if user_id:
            AuditLog.log_action(
                db_session=db,
                user_id=user_id,
                action="UPDATE",
                resource_type=self.model.__name__,
                resource_id=db_obj.id,
                old_values=old_values,
                new_values=update_data
            )
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def soft_delete(self, db: Session, id: uuid.UUID, 
                    user_id: uuid.UUID = None) -> Optional[ModelType]:
        """Soft delete record (set is_active=False)"""
        db_obj = self.get(db, id)
        if not db_obj:
            return None
        
        old_values = db_obj.to_dict()
        db_obj.is_active = False
        
        # Log audit trail
        if user_id:
            AuditLog.log_action(
                db_session=db,
                user_id=user_id,
                action="DELETE",
                resource_type=self.model.__name__,
                resource_id=db_obj.id,
                old_values=old_values
            )
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_paginated(self, db: Session, page: int = 1, per_page: int = 20, 
                      filters: Dict[str, Any] = None, order_by: str = None) -> Dict[str, Any]:
        """Get paginated results with metadata"""
        skip = (page - 1) * per_page
        
        items = self.get_all(db, skip=skip, limit=per_page, filters=filters, order_by=order_by)
        total = self.count(db, filters=filters)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
            "has_next": page * per_page < total,
            "has_prev": page > 1
        }