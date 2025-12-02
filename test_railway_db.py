import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import psycopg2
from psycopg2 import OperationalError

# Fix Unicode output for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Load environment variables
load_dotenv()

def test_connection_psycopg2():
    """Test connection using psycopg2 directly"""
    print("\n=== Testing connection with psycopg2 ===")

    db_url = os.getenv('DATABASE_URL')
    print(f"Attempting to connect to: {db_url.split('@')[1] if '@' in db_url else 'Unable to parse URL'}")

    try:
        # Parse the DATABASE_URL
        db_url = os.getenv('DATABASE_URL')

        # Connect to PostgreSQL
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Test query
        cursor.execute('SELECT version();')
        db_version = cursor.fetchone()
        print(f"[SUCCESS] Connection successful!")
        print(f"PostgreSQL version: {db_version[0]}")

        # Check existing tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"\nExisting tables in database ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")

        cursor.close()
        conn.close()
        return True

    except OperationalError as e:
        print(f"[FAILED] Connection failed with psycopg2: {e}")
        print("\nPossible reasons:")
        print("1. Railway might not allow external connections")
        print("2. SSL/TLS might be required")
        print("3. Credentials might be incorrect")
        return False
    except Exception as e:
        print(f"[FAILED] Unexpected error: {e}")
        return False

def test_connection_sqlalchemy():
    """Test connection using SQLAlchemy"""
    print("\n=== Testing connection with SQLAlchemy ===")

    try:
        from app import app, db

        with app.app_context():
            # Test database connection
            db.engine.execute(text("SELECT 1"))
            print("[SUCCESS] SQLAlchemy connection successful!")

            # Check if we can get table info
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            print(f"Existing tables found by SQLAlchemy: {len(existing_tables)}")
            for table in existing_tables:
                print(f"  - {table}")

            return True

    except Exception as e:
        print(f"[FAILED] SQLAlchemy connection failed: {e}")
        return False

def test_modified_connection():
    """Test with modified connection parameters"""
    print("\n=== Testing with SSL enabled ===")

    # Try with SSL mode
    db_url = os.getenv('DATABASE_URL')

    # Add SSL parameters if not present
    if '?sslmode=' not in db_url:
        modified_url = db_url + '?sslmode=require'
    else:
        modified_url = db_url

    try:
        conn = psycopg2.connect(modified_url)
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        db_version = cursor.fetchone()
        print(f"[SUCCESS] Connection successful with SSL!")
        print(f"PostgreSQL version: {db_version[0]}")
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"[FAILED] Connection with SSL failed: {e}")
        return False

if __name__ == '__main__':
    print("Testing Railway PostgreSQL Connection")
    print("=" * 50)

    # Check if DATABASE_URL is set
    if not os.getenv('DATABASE_URL'):
        print("[FAILED] DATABASE_URL not found in .env file")
        sys.exit(1)

    # Test different connection methods
    success = False

    # Test 1: Direct psycopg2
    success = test_connection_psycopg2() or success

    # Test 2: Try with SSL
    if not success:
        success = test_modified_connection() or success

    # Test 3: SQLAlchemy
    if not success:
        success = test_connection_sqlalchemy() or success

    print("\n" + "=" * 50)
    if success:
        print("[SUCCESS] At least one connection method was successful!")
        print("You can proceed with creating tables.")
    else:
        print("[FAILED] All connection attempts failed.")
        print("\nNext steps:")
        print("1. Deploy to Railway and test there (Railway's internal network might work)")
        print("2. Check Railway documentation for external access settings")
        print("3. Consider Railway's proxy settings for database access")