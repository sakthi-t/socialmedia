import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db
from sqlalchemy import text

def update_comment_table():
    with app.app_context():
        # Check if the column needs to be made nullable
        try:
            # Try to alter the column to make it nullable
            db.session.execute(text("""
                ALTER TABLE comments
                ALTER COLUMN author_id DROP NOT NULL
            """))
            db.session.commit()
            print("Successfully updated comments table to allow NULL author_id for AI comments")
        except Exception as e:
            print(f"Error updating table (might already be updated): {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    update_comment_table()