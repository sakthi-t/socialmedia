from app import app
from models import db, FriendRequest

with app.app_context():
    # Delete all declined friend requests
    declined_requests = FriendRequest.query.filter_by(status='declined').all()

    print(f"Found {len(declined_requests)} declined friend requests")

    for request in declined_requests:
        print(f"Deleting request from {request.sender.username} to {request.receiver.username}")
        db.session.delete(request)

    db.session.commit()
    print("All declined requests have been deleted. You can now send new friend requests!")