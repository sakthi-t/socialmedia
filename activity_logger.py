"""
Activity logger helper functions for tracking user actions
"""

from datetime import datetime
from flask import request
from models import db, ActivityLog

def log_activity(user_id, activity_type, description, target_user_id=None, activity_data=None):
    """
    Log a user activity to the database

    Args:
        user_id: ID of the user performing the action
        activity_type: Type of activity (e.g., 'login', 'create_post', 'send_message')
        description: Human-readable description of the activity
        target_user_id: ID of the target user (if applicable)
        activity_data: Dictionary with additional activity details
    """
    try:
        activity = ActivityLog(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            target_user_id=target_user_id,
            activity_data=activity_data or {}
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error logging activity: {e}")

# Specific logging functions for common activities

def log_login(user_id):
    """Log user login"""
    log_activity(user_id, 'login', 'User logged in')

def log_logout(user_id):
    """Log user logout"""
    log_activity(user_id, 'logout', 'User logged out')

def log_signup(user_id):
    """Log user signup"""
    log_activity(user_id, 'signup', 'User created an account')

def log_profile_creation(user_id):
    """Log profile creation"""
    log_activity(user_id, 'create_profile', 'User created their profile')

def log_friend_request_sent(sender_id, receiver_id):
    """Log friend request sent"""
    from models import User
    receiver = User.query.get(receiver_id)
    description = f"Sent friend request to {receiver.name if receiver else 'Unknown user'}"
    log_activity(sender_id, 'friend_request_sent', description, target_user_id=receiver_id)

def log_friend_request_received(sender_id, receiver_id):
    """Log friend request received"""
    from models import User
    sender = User.query.get(sender_id)
    description = f"Received friend request from {sender.name if sender else 'Unknown user'}"
    log_activity(receiver_id, 'friend_request_received', description, target_user_id=sender_id)

def log_friend_request_accepted(sender_id, receiver_id):
    """Log friend request accepted"""
    from models import User
    sender = User.query.get(sender_id)
    description = f"Accepted friend request from {sender.name if sender else 'Unknown user'}"
    log_activity(receiver_id, 'friend_request_accepted', description, target_user_id=sender_id)

def log_friend_request_declined(sender_id, receiver_id):
    """Log friend request declined"""
    from models import User
    sender = User.query.get(sender_id)
    description = f"Declined friend request from {sender.name if sender else 'Unknown user'}"
    log_activity(receiver_id, 'friend_request_declined', description, target_user_id=sender_id)

def log_message_sent(sender_id, receiver_id):
    """Log message sent"""
    from models import User
    receiver = User.query.get(receiver_id)
    description = f"Sent message to {receiver.name if receiver else 'Unknown user'}"
    log_activity(sender_id, 'send_message', description, target_user_id=receiver_id)

def log_message_received(sender_id, receiver_id):
    """Log message received"""
    from models import User
    sender = User.query.get(sender_id)
    description = f"Received message from {sender.name if sender else 'Unknown user'}"
    log_activity(receiver_id, 'receive_message', description, target_user_id=sender_id)

def log_post_created(user_id, post_id, category):
    """Log post creation"""
    description = f"Created a {category} post"
    log_activity(user_id, 'create_post', description, activity_data={'post_id': post_id, 'category': category})

def log_post_liked(user_id, post_id):
    """Log post like"""
    description = "Liked a post"
    log_activity(user_id, 'like_post', description, activity_data={'post_id': post_id})

def log_post_disliked(user_id, post_id):
    """Log post dislike"""
    description = "Disliked a post"
    log_activity(user_id, 'dislike_post', description, activity_data={'post_id': post_id})

def log_comment_created(user_id, post_id, comment_id, is_ai=False):
    """Log comment creation"""
    if is_ai:
        description = "AI commented on a post"
    else:
        description = "Commented on a post"
    log_activity(user_id, 'create_comment', description,
                activity_data={'post_id': post_id, 'comment_id': comment_id, 'is_ai': is_ai})

def log_comment_liked(user_id, comment_id):
    """Log comment like"""
    description = "Liked a comment"
    log_activity(user_id, 'like_comment', description, activity_data={'comment_id': comment_id})

def log_comment_disliked(user_id, comment_id):
    """Log comment dislike"""
    description = "Disliked a comment"
    log_activity(user_id, 'dislike_comment', description, activity_data={'comment_id': comment_id})

def log_post_deleted(user_id, post_id):
    """Log post deletion"""
    description = "Deleted a post"
    log_activity(user_id, 'delete_post', description, activity_data={'post_id': post_id})

def log_comment_deleted(user_id, comment_id):
    """Log comment deletion"""
    description = "Deleted a comment"
    log_activity(user_id, 'delete_comment', description, activity_data={'comment_id': comment_id})

def log_chatbot_interaction(user_id, session_id):
    """Log chatbot interaction"""
    description = "Interacted with Swift chatbot"
    log_activity(user_id, 'chatbot_interaction', description,
                activity_data={'session_id': session_id})