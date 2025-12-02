#!/usr/bin/env python3
"""
Database migration script to add CASCADE delete to foreign key constraints
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Comment, Post, User, ActivityLog

def migrate_foreign_keys():
    """Update foreign key constraints with CASCADE delete"""

    with app.app_context():
        print("Starting database migration...")

        try:
            # Drop existing foreign key constraints and recreate with CASCADE
            with db.engine.connect() as conn:
                # For comments table
                conn.execute(db.text("""
                    ALTER TABLE comments
                    DROP CONSTRAINT IF EXISTS comments_post_id_fkey,
                    ALTER COLUMN post_id DROP DEFAULT,
                    ALTER COLUMN post_id SET NOT NULL;
                """))

                conn.execute(db.text("""
                    ALTER TABLE comments
                    ADD CONSTRAINT comments_post_id_fkey
                    FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE;
                """))

                conn.execute(db.text("""
                    ALTER TABLE comments
                    DROP CONSTRAINT IF EXISTS comments_author_id_fkey,
                    ALTER COLUMN author_id DROP DEFAULT;
                """))

                conn.execute(db.text("""
                    ALTER TABLE comments
                    ADD CONSTRAINT comments_author_id_fkey
                    FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE SET NULL;
                """))

                conn.commit()

            print("Successfully updated foreign key constraints with CASCADE delete")

        except Exception as e:
            print(f"Migration error: {e}")
            conn.rollback()
            return False

        return True

if __name__ == "__main__":
    if migrate_foreign_keys():
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)