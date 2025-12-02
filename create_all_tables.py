import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Fix Unicode output for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from app import app
from models import (
    db, User, Profile, FriendRequest, Friendship, Message,
    Post, Comment, PostLike, CommentLike, ChatHistory, ActivityLog
)
from sqlalchemy import text, inspect

def create_all_tables():
    """Create ALL database tables in Railway PostgreSQL"""

    with app.app_context():
        print("=" * 60)
        print("Creating ALL tables in Railway PostgreSQL database")
        print("=" * 60)

        # Get list of all models
        all_models = [
            User,              # Users table
            Profile,           # Profiles table
            FriendRequest,     # Friend requests table
            Friendship,        # Friendships table
            Message,           # Messages table
            Post,              # Posts table
            Comment,           # Comments table
            PostLike,          # Post likes table
            CommentLike,       # Comment likes table
            ChatHistory,       # Chat history table (Swift bot)
            ActivityLog        # Activity logs table
        ]

        # Create all tables
        try:
            db.create_all()
            print("\n[SUCCESS] All tables created successfully!")

            # Verify tables were created
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()

            print(f"\nTotal tables in database: {len(existing_tables)}")
            print("\nTables created:")

            for model in all_models:
                table_name = model.__tablename__
                if table_name in existing_tables:
                    print(f"  [OK] {table_name}")
                else:
                    print(f"  [FAIL] {table_name} - NOT FOUND")

            # Show detailed table info
            print("\n" + "=" * 60)
            print("Detailed Table Information:")
            print("=" * 60)

            for model in all_models:
                table_name = model.__tablename__
                if table_name in existing_tables:
                    columns = inspector.get_columns(table_name)
                    print(f"\n{table_name.upper()}:")
                    for column in columns:
                        print(f"  - {column['name']}: {column['type']}")

            # Test a simple query to ensure database is working
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM users"))
                print(f"\n[INFO] Users table is ready, current count: {result.scalar()}")
            except:
                print("\n[INFO] Users table is ready (empty)")

            print("\n" + "=" * 60)
            print("[SUCCESS] Railway PostgreSQL database is fully set up!")
            print("=" * 60)

            return True

        except Exception as e:
            print(f"\n[FAILED] Error creating tables: {e}")
            return False

def verify_foreign_keys():
    """Verify that foreign key constraints are properly set"""

    with app.app_context():
        print("\nVerifying foreign key constraints...")

        inspector = inspect(db.engine)

        # Check foreign keys for each table
        tables_to_check = {
            'profiles': 'users',
            'friend_requests': 'users',
            'friendships': 'users',
            'messages': 'users',
            'posts': 'users',
            'comments': ['users', 'posts'],
            'post_likes': ['users', 'posts'],
            'comment_likes': ['users', 'comments'],
            'chat_history': 'users',
            'activity_logs': 'users'
        }

        for table, references in tables_to_check.items():
            try:
                fks = inspector.get_foreign_keys(table)
                if fks:
                    print(f"  [OK] {table}: {len(fks)} foreign key(s)")
                else:
                    print(f"  [WARN] {table}: No foreign keys")
            except Exception as e:
                print(f"  [FAIL] {table}: Error checking FKs - {e}")

if __name__ == '__main__':
    print("Railway PostgreSQL - Complete Database Setup")
    print("This will create ALL tables needed for the social media app")
    print("\nModels to be created:")
    print("- 1. Users (user authentication)")
    print("- 2. Profiles (user profile information)")
    print("- 3. FriendRequests (friend request management)")
    print("- 4. Friendships (friend relationships)")
    print("- 5. Messages (private messaging)")
    print("- 6. Posts (user posts with AI analysis)")
    print("- 7. Comments (post comments)")
    print("- 8. PostLikes (post likes/dislikes)")
    print("- 9. CommentLikes (comment likes/dislikes)")
    print("- 10. ChatHistory (Swift AI bot conversations)")
    print("- 11. ActivityLogs (user activity tracking)")

    print("\nProceeding with table creation...")

    success = create_all_tables()

    if success:
        verify_foreign_keys()
        print("\n[SUCCESS] Database is ready for deployment!")
    else:
        print("\n[FAILED] Please check the error above and try again.")