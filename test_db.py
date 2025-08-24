import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Adjust this path if your .env is not in the same folder
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

def test_database():
    database_uri = os.getenv('DATABASE_URI')
    
    if not database_uri:
        print("❌ DATABASE_URI is not set in the environment variables.")
        return

    print(f"Testing connection: {database_uri[:50]}...")

    try:
        engine = create_engine(database_uri)
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text('SELECT current_user, current_database()'))
            user, db = result.fetchone()
            print(f"✅ Connected as user: {user}")
            print(f"✅ Connected to database: {db}")

            # Test table creation permissions
            conn.execute(text('CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY)'))
            print("✅ Can create tables")

            # Clean up
            conn.execute(text('DROP TABLE IF EXISTS test_table'))
            print("✅ Can drop tables")

            # Check existing tables
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"✅ Existing tables: {', '.join(tables) if tables else 'No tables found'}")

            # Commit if needed (optional for some DBs)
            conn.commit()

    except Exception as e:
        print(f"❌ Database test failed: {e}")

if __name__ == "__main__":
    test_database()
