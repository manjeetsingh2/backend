import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load environment variables
load_dotenv()

def check_environment():
    print("=== Environment Configuration Check ===")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Create a .env file in the project root directory")
        return False
    
    print("✅ .env file found")
    
    # Check required variables
    required_vars = {
        'DATABASE_URI': 'Database connection string',
        'JWT_SECRET_KEY': 'JWT secret key',
        'SECRET_KEY': 'Flask secret key'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Show partial value for security
            display_value = value[:10] + '...' if len(value) > 10 else value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set ({description})")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing variables: {', '.join(missing_vars)}")
        return False
    
    # Test database connection
    print("\n=== Database Connection Test ===")
    try:
        database_uri = os.getenv('DATABASE_URI')
        engine = create_engine(database_uri)
        connection = engine.connect()
        result = connection.execute('SELECT 1 as test').fetchone()
        connection.close()
        print("✅ Database connection successful")
        print(f"✅ Test query result: {result[0]}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nCommon solutions:")
        print("1. Check if PostgreSQL is running")
        print("2. Verify database credentials in .env file")
        print("3. Ensure database exists")
        print("4. Check if psycopg2-binary is installed")
        return False

if __name__ == "__main__":
    print("Starting configuration check...\n")
    success = check_environment()
    if success:
        print("\n🎉 Configuration is valid! Ready to run the app.")
    else:
        print("\n💥 Configuration has issues. Please fix them before running the app.")
