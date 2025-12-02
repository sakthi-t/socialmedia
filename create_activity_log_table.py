#!/usr/bin/env python3
"""
Script to create the activity_logs table in the database
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, ActivityLog

def create_activity_log_table():
    """Create the activity_logs table"""
    with app.app_context():
        try:
            # Check if table already exists
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            if 'activity_logs' in tables:
                print("Table 'activity_logs' already exists!")
                return

            # Create the table
            ActivityLog.__table__.create(db.engine)
            print("Successfully created 'activity_logs' table!")

        except Exception as e:
            print(f"Error creating table: {e}")
            raise

if __name__ == "__main__":
    create_activity_log_table()