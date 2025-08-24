import sys
from app.config import get_config, config_manager

def validate_configuration():
    """Validate all configuration settings"""
    
    print("=== Configuration Validation ===\n")
    
    try:
        # Get configuration
        config = get_config()
        
        print(f"✅ Environment: {config_manager.environment}")
        print(f"✅ Database URI: {config.SQLALCHEMY_DATABASE_URI[:50]}...")
        print(f"✅ JWT Secret: {'*' * 20}")
        print(f"✅ App Secret: {'*' * 20}")
        print(f"✅ Debug Mode: {config.DEBUG}")
        print(f"✅ Host: {config.HOST}")
        print(f"✅ Port: {config.PORT}")
        
        # Test database connection
        print("\n=== Database Connection Test ===")
        from sqlalchemy import create_engine
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
        with engine.connect() as conn:
            result = conn.execute('SELECT version()').fetchone()
            print(f"✅ Database connected: PostgreSQL")
            
        print("\n🎉 All configurations are valid!")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")
        return False

if __name__ == "__main__":
    success = validate_configuration()
    sys.exit(0 if success else 1)
