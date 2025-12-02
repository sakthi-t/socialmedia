import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Post, Comment, PostLike, CommentLike
from sqlalchemy import text

def create_new_tables():
    with app.app_context():
        # Create new tables
        db.create_all()
        print("New tables for Posts and Comments created successfully!")

        # Verify tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        if 'posts' in tables and 'comments' in tables and 'post_likes' in tables and 'comment_likes' in tables:
            print("✓ All new tables verified in database")
        else:
            print("✗ Some tables may not have been created properly")

if __name__ == "__main__":
    create_new_tables()