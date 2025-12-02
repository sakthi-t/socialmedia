from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import secrets

# This will be initialized in app.py
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # This is the display name
    username = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='User')

    # Relationships
    profile = db.relationship('Profile', backref='user', uselist=False, cascade='all, delete-orphan')
    sent_requests = db.relationship('FriendRequest', foreign_keys='FriendRequest.sender_id', backref='sender', lazy='dynamic')
    received_requests = db.relationship('FriendRequest', foreign_keys='FriendRequest.receiver_id', backref='receiver', lazy='dynamic')
    friendships1 = db.relationship('Friendship', foreign_keys='Friendship.user1_id', backref='user1', lazy='dynamic')
    friendships2 = db.relationship('Friendship', foreign_keys='Friendship.user2_id', backref='user2', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def get_id(self):
        return str(self.id)

class Profile(db.Model):
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    phone = db.Column(db.String(20))
    education = db.Column(db.String(100))
    work = db.Column(db.String(100))
    website = db.Column(db.String(200))
    github = db.Column(db.String(100))
    linkedin = db.Column(db.String(100))
    profile_picture = db.Column(db.String(500))  # Cloudinary URL
    secret_key = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Profile {self.user.username}>'

class FriendRequest(db.Model):
    __tablename__ = 'friend_requests'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('sender_id', 'receiver_id'),)

    def __repr__(self):
        return f'<FriendRequest {self.sender.username} -> {self.receiver.username}>'

class Friendship(db.Model):
    __tablename__ = 'friendships'

    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user1_id', 'user2_id'),)

    def __repr__(self):
        return f'<Friendship {self.user1.username} <-> {self.user2.username}>'

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

    def __repr__(self):
        return f'<Message {self.sender.username} -> {self.receiver.username}: {self.content[:20]}...>'

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 'personal' or 'professional'
    ai_comment = db.Column(db.Text)  # AI's first comment
    ai_analysis = db.Column(db.Text)  # AI's analysis of the post
    is_ai_generated = db.Column(db.Boolean, default=False)  # Whether AI helped generate the post
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = db.relationship('User', backref='posts')
    comments = db.relationship('Comment', backref='post', cascade='all, delete-orphan')
    likes = db.relationship('PostLike', backref='post', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Post {self.id} by {self.author.username}: {self.content[:30]}...>'

class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)  # Can be null for AI comments
    content = db.Column(db.Text, nullable=False)
    is_ai_comment = db.Column(db.Boolean, default=False)  # To identify AI comments
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = db.relationship('User', backref='comments')
    likes = db.relationship('CommentLike', backref='comment', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Comment {self.id} by {self.author.username}: {self.content[:30]}...>'

class PostLike(db.Model):
    __tablename__ = 'post_likes'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vote_type = db.Column(db.Integer, default=1)  # 1 for like, -1 for dislike
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('post_id', 'user_id'),)

    def __repr__(self):
        return f'<PostLike {self.user.username} {"likes" if self.vote_type == 1 else "dislikes"} post {self.post_id}>'

class CommentLike(db.Model):
    __tablename__ = 'comment_likes'

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vote_type = db.Column(db.Integer, default=1)  # 1 for like, -1 for dislike
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('comment_id', 'user_id'),)

    def __repr__(self):
        return f'<CommentLike {self.user.username} {"likes" if self.vote_type == 1 else "dislikes"} comment {self.comment_id}>'

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)  # To group conversations
    user_message = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    chroma_id = db.Column(db.String(100))  # ID for Chroma Cloud document

    # Relationships
    user = db.relationship('User', backref='chat_history')

    def __repr__(self):
        return f'<ChatHistory {self.user.username}: {self.user_message[:30]}...>'

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # Type of activity
    description = db.Column(db.Text, nullable=False)  # Human-readable description
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # For friend-related activities
    activity_data = db.Column(db.JSON)  # Additional details like post_id, count, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='activities', passive_deletes=True)
    target_user = db.relationship('User', foreign_keys=[target_user_id], backref='targeted_activities', passive_deletes=True)

    def __repr__(self):
        return f'<ActivityLog {self.user.username}: {self.description[:50]}...>'