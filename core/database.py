"""
PostgreSQL Database configuration and session management using SQLAlchemy ORM
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://agri_user:agri_secure_pass_2024@localhost:5432/agri_development"
        )
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # Engine configuration
        self.engine_config = {
            "poolclass": QueuePool,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "echo": self.environment == "development"  # Log SQL in development
        }
        
        # Create engine
        self.engine = create_engine(self.database_url, **self.engine_config)
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
    
    def get_database_info(self):
        """Get database connection information"""
        return {
            "database_url": self.database_url.replace(self.get_password(), "***"),
            "environment": self.environment,
            "pool_size": self.engine_config["pool_size"],
            "max_overflow": self.engine_config["max_overflow"]
        }
    
    def get_password(self):
        """Extract password from database URL for masking"""
        try:
            if "://" in self.database_url and "@" in self.database_url:
                auth_part = self.database_url.split("://")[1].split("@")[0]
                if ":" in auth_part:
                    return auth_part.split(":")[1]
        except:
            pass
        return ""

# Global database instance
db_config = DatabaseConfig()

# Dependency for FastAPI
def get_db():
    """Database session dependency for FastAPI"""
    db = db_config.SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_db_session():
    """Context manager for database sessions"""
    db = db_config.SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database transaction error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    from models import Base
    try:
        Base.metadata.create_all(bind=db_config.engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def drop_tables():
    """Drop all database tables (use with caution!)"""
    from models import Base
    try:
        Base.metadata.drop_all(bind=db_config.engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise

def init_database():
    """Initialize database with tables and seed data"""
    from models import User, CropTarget
    
    create_tables()
    
    # Create seed data
    with get_db_session() as db:
        # Check if users already exist
        existing_users = db.query(User).count()
        
        if existing_users == 0:
            logger.info("Creating seed users...")
            
            # Create VO user
            vo_user = User(
                username="vo_user",
                email="vo@agri.com",
                full_name="Village Officer User",
                role="VO",
                district="Sample District",
                state="Sample State",
                village="Sample Village"
            )
            vo_user.set_password("password123")
            
            # Create BO user
            bo_user = User(
                username="bo_user", 
                email="bo@agri.com",
                full_name="Block Officer User",
                role="BO",
                district="Sample District",
                state="Sample State"
            )
            bo_user.set_password("password123")
            
            db.add(vo_user)
            db.add(bo_user)
            db.commit()
            
            logger.info("Seed users created successfully")
            
            # Create sample crop targets
            sample_targets = [
                {
                    "year": 2025,
                    "season": "Kharif",
                    "district": "Sample District",
                    "state": "Sample State", 
                    "village": "Sample Village",
                    "crop_name": "Rice",
                    "crop_variety": "Basmati",
                    "cultivable_area": 100.0,
                    "target_area": 80.0,
                    "target_yield": 5.5,
                    "status": "approved",
                    "submitted_by": vo_user.id,
                    "approved_by": bo_user.id
                },
                {
                    "year": 2025,
                    "season": "Rabi",
                    "district": "Sample District",
                    "state": "Sample State",
                    "village": "Sample Village",
                    "crop_name": "Wheat", 
                    "crop_variety": "HD-2967",
                    "cultivable_area": 75.0,
                    "target_area": 70.0,
                    "target_yield": 4.2,
                    "status": "pending",
                    "submitted_by": vo_user.id
                }
            ]
            
            for target_data in sample_targets:
                target = CropTarget(**target_data)
                target.calculate_metrics()
                db.add(target)
            
            db.commit()
            logger.info("Sample crop targets created successfully")
        else:
            logger.info("Database already contains data, skipping seed data creation")

# Initialize database on module import
if __name__ != "__main__":
    try:
        init_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")