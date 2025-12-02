from app import app
from models import db

# Create the message table
with app.app_context():
    # Import all models to ensure they are registered with SQLAlchemy
    from models import User, Profile, FriendRequest, Friendship, Message

    # Create all tables that don't exist yet
    db.create_all()

    print("Database tables updated successfully!")