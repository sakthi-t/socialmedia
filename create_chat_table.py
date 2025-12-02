import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, ChatHistory

def create_chat_table():
    with app.app_context():
        # Create the chat_history table
        db.create_all()
        print("Chat history table created successfully!")

        # Verify table exists
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        if 'chat_history' in tables:
            print("✓ Chat history table verified in database")
        else:
            print("✗ Table was not created properly")

if __name__ == "__main__":
    create_chat_table()