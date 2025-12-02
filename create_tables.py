from app import app
from models import db

def create_tables():
    """Create all database tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Tables created successfully!")
        print("\nModels created:")
        print("- User")
        print("- Profile")
        print("- FriendRequest")
        print("- Friendship")

if __name__ == '__main__':
    create_tables()