"""
Base service class with common functionality
Implements DRY patterns for service layer operations
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type, Union
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from core.database import get_db_context
from core.exceptions import (
    DatabaseException, 
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException
)
from models.base import BaseModel

T = TypeVar('T', bound=BaseModel)


@dataclass
class ServiceResult:
    """Standardized service operation result"""
    success: bool
    data: Any = None
    message: str = ""
    errors: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    def success_result(cls, data: Any = None, message: str = "", **metadata) -> 'ServiceResult':
        """Create successful result"""
        return cls(
            success=True,
            data=data,
            message=message,
            metadata=metadata
        )
    
    @classmethod
    def error_result(cls, message: str, errors: List[str] = None, **metadata) -> 'ServiceResult':
        """Create error result"""
        return cls(
            success=False,
            message=message,
            errors=errors or [],
            metadata=metadata
        )


class BaseService(Generic[T], ABC):
    """Base service class with common CRUD operations"""
    
    def __init__(self, model_class: Type[T], db_session: Session = None):
        self.model_class = model_class
        self._db_session = db_session
    
    @property
    def db(self) -> Session:
        """Get database session"""
        if self._db_session:
            return self._db_session
        # If no session provided, this should be handled by dependency injection
        raise RuntimeError("Database session not provided")
    
    # CRUD Operations (DRY Implementation)
    def create(self, data: Dict[str, Any], created_by: str = None) -> ServiceResult:
        """Create a new record"""
        try:
            # Validate required fields
            validation_result = self._validate_create_data(data)
            if not validation_result.success:
                return validation_result
            
            # Create instance
            instance = self.model_class(**data)
            
            # Set metadata if model supports it
            if hasattr(instance, 'created_by') and created_by:
                instance.created_by = created_by
            
            # Pre-create hook
            self._before_create(instance, data)
            
            # Save to database
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            
            # Post-create hook
            self._after_create(instance, data)
            
            return ServiceResult.success_result(
                data=instance.to_dict(),
                message=f"{self.model_class.__name__} created successfully"
            )
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Database error during create: {str(e)}")
        except Exception as e:
            self.db.rollback()
            raise BusinessLogicException(f"Error creating {self.model_class.__name__}: {str(e)}")
    
    def get_by_id(self, record_id: Union[str, uuid.UUID]) -> ServiceResult:
        """Get record by ID"""
        try:
            instance = self.db.query(self.model_class).filter(
                self.model_class.id == str(record_id)
            ).first()
            
            if not instance:
                return ServiceResult.error_result(
                    message=f"{self.model_class.__name__} not found"
                )
            
            return ServiceResult.success_result(data=instance.to_dict())
            
        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error during get: {str(e)}")
    
    def update(self, record_id: Union[str, uuid.UUID], 
               data: Dict[str, Any], updated_by: str = None) -> ServiceResult:
        """Update existing record"""
        try:
            # Get existing record
            instance = self.db.query(self.model_class).filter(
                self.model_class.id == str(record_id)
            ).first()
            
            if not instance:
                return ServiceResult.error_result(
                    message=f"{self.model_class.__name__} not found"
                )
            
            # Validate update data
            validation_result = self._validate_update_data(instance, data)
            if not validation_result.success:
                return validation_result
            
            # Store old values for audit
            old_values = instance.to_dict()
            
            # Pre-update hook
            self._before_update(instance, data)
            
            # Update fields
            instance.update_from_dict(data)
            
            # Set metadata
            if hasattr(instance, 'updated_by') and updated_by:
                instance.updated_by = updated_by
            
            # Save changes
            self.db.commit()
            self.db.refresh(instance)
            
            # Post-update hook
            self._after_update(instance, old_values, data)
            
            return ServiceResult.success_result(
                data=instance.to_dict(),
                message=f"{self.model_class.__name__} updated successfully"
            )
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Database error during update: {str(e)}")
    
    def delete(self, record_id: Union[str, uuid.UUID], 
               deleted_by: str = None, soft_delete: bool = True) -> ServiceResult:
        """Delete record (soft or hard delete)"""
        try:
            instance = self.db.query(self.model_class).filter(
                self.model_class.id == str(record_id)
            ).first()
            
            if not instance:
                return ServiceResult.error_result(
                    message=f"{self.model_class.__name__} not found"
                )
            
            # Pre-delete hook
            self._before_delete(instance)
            
            if soft_delete and hasattr(instance, 'soft_delete'):
                instance.soft_delete()
                if hasattr(instance, 'updated_by') and deleted_by:
                    instance.updated_by = deleted_by
            else:
                self.db.delete(instance)
            
            self.db.commit()
            
            # Post-delete hook
            self._after_delete(instance, soft_delete)
            
            return ServiceResult.success_result(
                message=f"{self.model_class.__name__} deleted successfully"
            )
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Database error during delete: {str(e)}")
    
    def list(self, filters: Dict[str, Any] = None, 
             page: int = 1, per_page: int = 10,
             order_by: str = None) -> ServiceResult:
        """List records with filtering and pagination"""
        try:
            query = self.db.query(self.model_class)
            
            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)
            
            # Apply ordering
            if order_by:
                query = self._apply_ordering(query, order_by)
            else:
                # Default ordering by created_at desc
                if hasattr(self.model_class, 'created_at'):
                    query = query.order_by(self.model_class.created_at.desc())
            
            # Get total count before pagination
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            items = query.offset(offset).limit(per_page).all()
            
            # Convert to dictionaries
            item_data = [item.to_dict() for item in items]
            
            return ServiceResult.success_result(
                data={
                    "items": item_data,
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "pages": (total + per_page - 1) // per_page
                }
            )
            
        except SQLAlchemyError as e:
            raise DatabaseException(f"Database error during list: {str(e)}")
    
    # Hook methods for customization (Template Method Pattern)
    def _validate_create_data(self, data: Dict[str, Any]) -> ServiceResult:
        """Override to add create validation logic"""
        return ServiceResult.success_result()
    
    def _validate_update_data(self, instance: T, data: Dict[str, Any]) -> ServiceResult:
        """Override to add update validation logic"""
        return ServiceResult.success_result()
    
    def _before_create(self, instance: T, data: Dict[str, Any]) -> None:
        """Override to add pre-create logic"""
        pass
    
    def _after_create(self, instance: T, data: Dict[str, Any]) -> None:
        """Override to add post-create logic"""
        pass
    
    def _before_update(self, instance: T, data: Dict[str, Any]) -> None:
        """Override to add pre-update logic"""
        pass
    
    def _after_update(self, instance: T, old_values: Dict[str, Any], 
                     new_data: Dict[str, Any]) -> None:
        """Override to add post-update logic"""
        pass
    
    def _before_delete(self, instance: T) -> None:
        """Override to add pre-delete logic"""
        pass
    
    def _after_delete(self, instance: T, soft_delete: bool) -> None:
        """Override to add post-delete logic"""
        pass
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Override to add custom filtering logic"""
        for key, value in filters.items():
            if hasattr(self.model_class, key) and value is not None:
                query = query.filter(getattr(self.model_class, key) == value)
        return query
    
    def _apply_ordering(self, query, order_by: str):
        """Override to add custom ordering logic"""
        if hasattr(self.model_class, order_by):
            query = query.order_by(getattr(self.model_class, order_by))
        return query


class TransactionalService(BaseService[T]):
    """Service with transaction management"""
    
    def execute_in_transaction(self, operation_func, *args, **kwargs) -> ServiceResult:
        """Execute operation within a database transaction"""
        try:
            result = operation_func(*args, **kwargs)
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            if isinstance(e, (ValidationException, BusinessLogicException)):
                return ServiceResult.error_result(message=str(e))
            raise


class CacheableService(BaseService[T]):
    """Service with caching capabilities"""
    
    def __init__(self, model_class: Type[T], db_session: Session = None, 
                 cache_ttl: int = 300):
        super().__init__(model_class, db_session)
        self.cache = {}
        self.cache_ttl = cache_ttl
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key"""
        key_parts = [method, self.model_class.__name__]
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        return ":".join(str(part) for part in key_parts)
    
    def _is_cache_valid(self, cache_entry: dict) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        
        timestamp = cache_entry.get('timestamp', 0)
        return (datetime.utcnow().timestamp() - timestamp) < self.cache_ttl
    
    def _set_cache(self, key: str, data: Any) -> None:
        """Set cache entry"""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.utcnow().timestamp()
        }
    
    def _get_cache(self, key: str) -> Any:
        """Get cache entry if valid"""
        cache_entry = self.cache.get(key)
        if self._is_cache_valid(cache_entry):
            return cache_entry['data']
        return None
    
    def clear_cache(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()