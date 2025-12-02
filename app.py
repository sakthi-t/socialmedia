from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import requests
from requests_oauthlib import OAuth2Session
from email_validator import validate_email, EmailNotValidError
from datetime import datetime
import secrets
import cloudinary
import cloudinary.uploader
from werkzeug.utils import secure_filename
import openai
from sqlalchemy import or_, and_
import uuid
from chroma_integration import chroma_manager
from activity_logger import (
    log_login, log_logout, log_signup, log_profile_creation,
    log_friend_request_sent, log_friend_request_received,
    log_friend_request_accepted, log_friend_request_declined,
    log_message_sent, log_message_received, log_post_created,
    log_post_liked, log_post_disliked, log_comment_created,
    log_comment_liked, log_comment_disliked, log_post_deleted,
    log_comment_deleted, log_chatbot_interaction, log_activity
)

# Load environment variables
load_dotenv()

# Allow HTTP for OAuth in development
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/socialmedia')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['GITHUB_CLIENT_ID'] = os.getenv('GITHUB_CLIENT_ID')
app.config['GITHUB_CLIENT_SECRET'] = os.getenv('GITHUB_CLIENT_SECRET')
app.config['ADMIN_EMAIL'] = os.getenv('ADMIN_EMAIL', '')

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'driiwvbs9'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Import db from models
from models import db

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'signin'
login_manager.login_message = 'Please sign in to access this page.'

# GitHub OAuth configuration
GITHUB_AUTH_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_URL = 'https://api.github.com/user'

if not app.config.get('GITHUB_CLIENT_ID') or not app.config.get('GITHUB_CLIENT_SECRET'):
    print("Warning: GitHub OAuth credentials not found in environment variables")

# Import models - at the bottom to avoid circular import

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    return redirect(url_for('signin'))

@app.route('/signin')
def signin():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Import User model here to avoid circular import
        from models import User

        # Validation
        errors = []

        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long')

        # Simple email validation - more permissive for test emails
        if '@' not in email or '.' not in email.split('@')[-1]:
            errors.append('Please enter a valid email address')

        if len(password) < 8:
            errors.append('Password must be at least 8 characters long')

        if password != confirm_password:
            errors.append('Passwords do not match')

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken')

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('signin.html', signup_active=True)

        # Create new user
        is_admin = email.lower() == app.config['ADMIN_EMAIL'].lower()

        user = User(
            username=username,
            email=email,
            name=username,  # Use username as display name initially
            password_hash=generate_password_hash(password),
            is_admin=is_admin,
            role='Admin' if is_admin else 'User',
            created_at=datetime.utcnow()
        )

        db.session.add(user)
        db.session.commit()

        # Log signup activity
        log_signup(user.id)

        flash('Account created successfully! Please sign in.', 'success')
        return redirect(url_for('signin'))

    return redirect(url_for('signin'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    from models import User
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        # Log login activity
        log_login(user.id)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('profile'))
    else:
        flash('Invalid email or password', 'error')
        return redirect(url_for('signin'))

@app.route('/auth/github')
def github_auth():
    # For debugging - print the redirect URI
    redirect_uri = url_for('github_callback', _external=True)
    print(f"Using redirect URI: {redirect_uri}")

    github = OAuth2Session(
        app.config['GITHUB_CLIENT_ID'],
        redirect_uri=redirect_uri
    )
    authorization_url, state = github.authorization_url(GITHUB_AUTH_URL)
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/auth/github/callback')
def github_callback():
    if request.args.get('state') != session.get('oauth_state'):
        flash('Invalid state parameter', 'error')
        return redirect(url_for('signin'))

    github = OAuth2Session(
        app.config['GITHUB_CLIENT_ID'],
        state=session.get('oauth_state'),
        redirect_uri=url_for('github_callback', _external=True)
    )

    try:
        token = github.fetch_token(
            GITHUB_TOKEN_URL,
            client_secret=app.config['GITHUB_CLIENT_SECRET'],
            authorization_response=request.url
        )

        # Get user info from GitHub
        github_user = github.get(GITHUB_USER_URL).json()

        # Import User model here to avoid circular import
        from models import User

        # Check if user exists
        user = User.query.filter_by(email=github_user.get('email')).first()

        if not user:
            # Create new user from GitHub
            username = github_user.get('login')
            base_username = username

            # Ensure username is unique
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1

            is_admin = github_user.get('email', '').lower() == app.config['ADMIN_EMAIL'].lower()

            # Use display name from GitHub, fallback to username
            display_name = github_user.get('name') or github_user.get('login')

            user = User(
                username=username,
                email=github_user.get('email') or f"{github_user.get('login')}@github.local",
                name=display_name,
                password_hash=generate_password_hash(secrets.token_urlsafe(16)),  # Random password
                is_admin=is_admin,
                role='Admin' if is_admin else 'User',
                created_at=datetime.utcnow()
            )

            db.session.add(user)
            db.session.commit()
            # Log signup for GitHub users
            log_signup(user.id)
        else:
            # Log login for existing GitHub users
            log_login(user.id)

        login_user(user)
        return redirect(url_for('profile'))

    except Exception as e:
        flash(f'GitHub authentication failed: {str(e)}', 'error')
        return redirect(url_for('signin'))

@app.route('/profile')
@login_required
def profile():
    # Check if user has a profile
    if not current_user.profile:
        return render_template('profile.html', has_profile=False)

    # Get friend counts for current user
    from models import Friendship, FriendRequest, User
    friends_count = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).count()

    # Get actual friends list
    friends = []
    friendships = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).all()

    for friendship in friendships:
        friend_id = friendship.user2_id if friendship.user1_id == current_user.id else friendship.user1_id
        friend = User.query.get(friend_id)
        if friend:
            friends.append(friend)

    pending_requests_count = FriendRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).count()

    pending_requests = FriendRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).all()

    # Check if viewing own profile or someone else's
    user_id = request.args.get('user_id')
    if user_id:
        from models import User
        profile_user = User.query.get_or_404(user_id)
        is_own_profile = profile_user.id == current_user.id
        is_friend = are_friends(current_user.id, profile_user.id)
        has_pending_request = has_friend_request(current_user.id, profile_user.id)
        received_request = has_friend_request(profile_user.id, current_user.id)
    else:
        profile_user = current_user
        is_own_profile = True
        is_friend = False
        has_pending_request = False
        received_request = False

    return render_template('profile.html',
                         has_profile=True,
                         profile_user=profile_user,
                         is_own_profile=is_own_profile,
                         is_friend=is_friend,
                         has_pending_request=has_pending_request,
                         received_request=received_request,
                         friends_count=friends_count,
                         pending_requests_count=pending_requests_count,
                         pending_requests=pending_requests,
                         friends=friends)

@app.route('/create-profile', methods=['GET', 'POST'])
@login_required
def create_profile():
    if current_user.profile:
        flash('You already have a profile', 'error')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        try:
            phone = request.form.get('phone')
            education = request.form.get('education')
            work = request.form.get('work')
            website = request.form.get('website')
            github = request.form.get('github')
            linkedin = request.form.get('linkedin')

            print(f"Creating profile for user {current_user.id}")
            print(f"Form data: phone={phone}, education={education}, work={work}")

            # Handle profile picture upload
            profile_picture = None
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename != '':
                    # Upload to Cloudinary
                    try:
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder='profile_pictures',
                            width=300,
                            height=300,
                            crop='fill',
                            gravity='face'
                        )
                        profile_picture = upload_result['secure_url']
                        print(f"Uploaded picture to Cloudinary: {profile_picture}")
                    except Exception as e:
                        print(f"Cloudinary upload error: {str(e)}")
                        flash(f'Error uploading profile picture: {str(e)}', 'error')

            # Generate random profile picture if none uploaded
            if not profile_picture:
                import random
                seed = current_user.username + str(random.randint(1000, 9999))
                profile_picture = f'https://picsum.photos/seed/{seed}/300/300.jpg'
                print(f"Generated random picture: {profile_picture}")

            # Generate secret key
            secret_key = secrets.token_urlsafe(32)

            # Create profile
            from models import Profile
            profile = Profile(
                user_id=current_user.id,
                phone=phone or None,
                education=education or None,
                work=work or None,
                website=website or None,
                github=github or None,
                linkedin=linkedin or None,
                profile_picture=profile_picture,
                secret_key=secret_key
            )

            db.session.add(profile)
            db.session.commit()

            # Log profile creation
            log_profile_creation(current_user.id)

            print("Profile created successfully!")
            flash('Profile created successfully!', 'success')
            return redirect(url_for('profile'))

        except Exception as e:
            print(f"Error creating profile: {str(e)}")
            db.session.rollback()
            flash(f'Error creating profile: {str(e)}', 'error')
            return render_template('create_profile.html')

    return render_template('create_profile.html')

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if not current_user.profile:
        flash('Please create a profile first', 'error')
        return redirect(url_for('create_profile'))

    if request.method == 'POST':
        try:
            phone = request.form.get('phone')
            education = request.form.get('education')
            work = request.form.get('work')
            website = request.form.get('website')
            github = request.form.get('github')
            linkedin = request.form.get('linkedin')
            remove_picture = request.form.get('remove_picture') == 'on'

            print(f"Updating profile for user {current_user.id}")

            # Handle profile picture update
            profile_picture = current_user.profile.profile_picture
            new_picture_uploaded = False

            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename != '':
                    # Upload new picture to Cloudinary
                    try:
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder='profile_pictures',
                            width=300,
                            height=300,
                            crop='fill',
                            gravity='face'
                        )
                        profile_picture = upload_result['secure_url']
                        new_picture_uploaded = True
                        print(f"Uploaded new picture to Cloudinary: {profile_picture}")
                    except Exception as e:
                        print(f"Cloudinary upload error: {str(e)}")
                        flash(f'Error uploading profile picture: {str(e)}', 'error')

            # Generate random profile picture if removed or none exists
            if remove_picture or (not profile_picture and not new_picture_uploaded):
                if remove_picture and profile_picture and 'picsum.photos' not in profile_picture:
                    # Try to delete from Cloudinary if it's a Cloudinary URL
                    try:
                        public_id = profile_picture.split('/')[-1].split('.')[0]
                        cloudinary.uploader.destroy(f'profile_pictures/{public_id}')
                    except:
                        pass  # Ignore deletion errors

                import random
                seed = current_user.username + str(random.randint(1000, 9999))
                profile_picture = f'https://picsum.photos/seed/{seed}/300/300.jpg'
                print(f"Generated new random picture: {profile_picture}")

            # Update profile
            profile = current_user.profile
            profile.phone = phone or None
            profile.education = education or None
            profile.work = work or None
            profile.website = website or None
            profile.github = github or None
            profile.linkedin = linkedin or None
            profile.profile_picture = profile_picture
            profile.updated_at = datetime.utcnow()

            db.session.commit()

            # Log profile update
            from activity_logger import log_activity
            log_activity(
                user_id=current_user.id,
                activity_type='profile_updated',
                description='Profile information was updated',
                activity_data={'updated_fields': ['phone', 'education', 'work', 'website', 'github', 'linkedin', 'profile_picture']}
            )

            print("Profile updated successfully!")
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))

        except Exception as e:
            print(f"Error updating profile: {str(e)}")
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')

    # GET request - show edit form with current data
    return render_template('edit_profile.html')

@app.route('/send-friend-request/<int:user_id>', methods=['POST'])
@login_required
def send_friend_request(user_id):
    if user_id == current_user.id:
        flash('You cannot send a friend request to yourself', 'error')
        return redirect(url_for('profile', user_id=user_id))

    from models import User, FriendRequest
    receiver = User.query.get_or_404(user_id)

    # Check if pending request already exists
    existing_request = FriendRequest.query.filter_by(
        sender_id=current_user.id,
        receiver_id=user_id,
        status='pending'
    ).first()

    if existing_request:
        flash('Friend request already sent', 'error')
        return redirect(url_for('profile', user_id=user_id))

    # Check if already friends
    if are_friends(current_user.id, user_id):
        flash('You are already friends', 'error')
        return redirect(url_for('profile', user_id=user_id))

    # Create friend request
    friend_request = FriendRequest(
        sender_id=current_user.id,
        receiver_id=user_id
    )

    db.session.add(friend_request)
    db.session.commit()

    # Log friend request activities
    log_friend_request_sent(current_user.id, user_id)
    log_friend_request_received(current_user.id, user_id)

    flash(f'Friend request sent to {receiver.username}', 'success')
    return redirect(url_for('profile', user_id=user_id))

@app.route('/respond-friend-request/<int:request_id>/<string:response>')
@login_required
def respond_friend_request(request_id, response):
    from models import FriendRequest, Friendship

    friend_request = FriendRequest.query.get_or_404(request_id)

    if friend_request.receiver_id != current_user.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('profile'))

    if response == 'accept':
        # Create friendship
        friendship = Friendship(
            user1_id=min(friend_request.sender_id, friend_request.receiver_id),
            user2_id=max(friend_request.sender_id, friend_request.receiver_id)
        )
        db.session.add(friendship)
        friend_request.status = 'accepted'

        # Log friend request acceptance
        log_friend_request_accepted(friend_request.sender_id, friend_request.receiver_id)

        flash(f'You are now friends with {friend_request.sender.username}', 'success')
    elif response == 'decline':
        # Log friend request decline before deleting
        log_friend_request_declined(friend_request.sender_id, friend_request.receiver_id)

        # Delete the declined request to allow resending later
        db.session.delete(friend_request)
        flash('Friend request declined', 'info')

    db.session.commit()
    return redirect(url_for('profile'))

@app.route('/search')
@login_required
def search_users():
    query = request.args.get('q', '')
    from models import User, Friendship, FriendRequest

    # Get friend counts for current user
    friends_count = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).count()

    # Get actual friends list
    friends = []
    friendships = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).all()

    for friendship in friendships:
        friend_id = friendship.user2_id if friendship.user1_id == current_user.id else friendship.user1_id
        friend = User.query.get(friend_id)
        if friend:
            friends.append(friend)

    pending_requests_count = FriendRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).count()

    if query:
        # Search for users by username or name
        users = User.query.filter(
            (User.username.ilike(f'%{query}%') | User.name.ilike(f'%{query}%')) &
            (User.id != current_user.id)
        ).limit(10).all()
    else:
        users = []

    return render_template('search.html', users=users, query=query,
                         are_friends=are_friends, has_friend_request=has_friend_request,
                         friends_count=friends_count, pending_requests_count=pending_requests_count,
                         friends=friends)

@app.route('/friends')
@login_required
def friends_list():
    from models import Friendship, User, FriendRequest

    # Get all friends
    friends = []
    friendships = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).all()

    for friendship in friendships:
        friend_id = friendship.user2_id if friendship.user1_id == current_user.id else friendship.user1_id
        friend = User.query.get(friend_id)
        friends.append(friend)

    # Get pending requests
    pending_requests = FriendRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).all()

    return render_template('friends.html', friends=friends, pending_requests=pending_requests,
                         friends_count=len(friends), pending_requests_count=len(pending_requests))

@app.route('/show-secret-key')
@login_required
def show_secret_key():
    if not current_user.profile:
        flash('Create a profile first', 'error')
        return redirect(url_for('create_profile'))

    return render_template('secret_key.html', secret_key=current_user.profile.secret_key)

@app.route('/regenerate-secret-key', methods=['POST'])
@login_required
def regenerate_secret_key():
    if not current_user.profile:
        return jsonify({'success': False, 'message': 'Create a profile first'}), 400

    # Generate new secret key
    new_secret_key = secrets.token_urlsafe(32)
    current_user.profile.secret_key = new_secret_key
    db.session.commit()

    return jsonify({'success': True, 'new_key': new_secret_key})

# Helper functions
def are_friends(user1_id, user2_id):
    from models import Friendship
    return Friendship.query.filter(
        ((Friendship.user1_id == user1_id) & (Friendship.user2_id == user2_id)) |
        ((Friendship.user1_id == user2_id) & (Friendship.user2_id == user1_id))
    ).first() is not None

def has_friend_request(sender_id, receiver_id):
    from models import FriendRequest
    return FriendRequest.query.filter_by(
        sender_id=sender_id,
        receiver_id=receiver_id,
        status='pending'
    ).first() is not None

# Messaging routes
@app.route('/messages')
@login_required
def messages():
    from models import User, Friendship, Message, FriendRequest

    # Get friend counts for current user
    friends_count = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).count()

    # Get actual friends list
    friends = []
    friendships = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).all()

    for friendship in friendships:
        friend_id = friendship.user2_id if friendship.user1_id == current_user.id else friendship.user1_id
        friend = User.query.get(friend_id)
        if friend:
            friends.append(friend)

    pending_requests_count = FriendRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).count()

    # Get search query
    query = request.args.get('q', '')

    if query:
        # Search friends by name
        search_friends = [f for f in friends if query.lower() in f.name.lower() or query.lower() in f.username.lower()]
    else:
        search_friends = friends

    # Get unread message count for notification
    unread_count = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=False
    ).count() if hasattr(Message, 'is_read') else 0

    return render_template('messages.html',
                         friends=search_friends,
                         query=query,
                         friends_count=friends_count,
                         pending_requests_count=pending_requests_count,
                         unread_count=unread_count)

@app.route('/messages/<int:user_id>')
@login_required
def chat_with_user(user_id):
    from models import User, Friendship, Message, FriendRequest

    # Check if users are friends
    if not are_friends(current_user.id, user_id):
        flash('You can only message your friends', 'warning')
        return redirect(url_for('messages'))

    other_user = User.query.get_or_404(user_id)

    # Get friend counts
    friends_count = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).count()

    # Get friends list
    friends = []
    friendships = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).all()

    for friendship in friendships:
        friend_id = friendship.user2_id if friendship.user1_id == current_user.id else friendship.user1_id
        friend = User.query.get(friend_id)
        if friend:
            friends.append(friend)

    pending_requests_count = FriendRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).count()

    # Get message history
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

    # Mark messages as read (if is_read column exists)
    for msg in messages:
        if msg.receiver_id == current_user.id and hasattr(msg, 'is_read'):
            msg.is_read = True

    try:
        db.session.commit()
    except:
        pass  # Ignore if is_read column doesn't exist

    return render_template('chat.html',
                         other_user=other_user,
                         messages=messages,
                         friends=friends,
                         friends_count=friends_count,
                         pending_requests_count=pending_requests_count)

@app.route('/send-message/<int:user_id>', methods=['POST'])
@login_required
def send_message(user_id):
    from models import User, Message

    # Check if users are friends
    if not are_friends(current_user.id, user_id):
        if request.is_json:
            return jsonify({'success': False, 'message': 'You can only message your friends'})
        flash('You can only message your friends', 'warning')
        return redirect(url_for('messages'))

    receiver = User.query.get_or_404(user_id)
    content = request.form.get('message') or request.json.get('message')

    if not content or not content.strip():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Message cannot be empty'})
        flash('Message cannot be empty', 'error')
        return redirect(url_for('chat_with_user', user_id=user_id))

    # Create message
    message = Message(
        sender_id=current_user.id,
        receiver_id=user_id,
        content=content.strip()
    )

    db.session.add(message)
    db.session.commit()

    # Log message activities
    log_message_sent(current_user.id, user_id)
    log_message_received(current_user.id, user_id)

    if request.is_json:
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'sender_name': current_user.name
            }
        })

    flash('Message sent', 'success')
    return redirect(url_for('chat_with_user', user_id=user_id))

@app.route('/api/messages/<int:user_id>/latest')
@login_required
def get_latest_messages(user_id):
    from models import Message

    # Check if users are friends
    if not are_friends(current_user.id, user_id):
        return jsonify({'error': 'Unauthorized'}), 403

    last_id = request.args.get('last_id', 0, type=int)

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).filter(Message.id > last_id).order_by(Message.timestamp.asc()).all()

    return jsonify({
        'messages': [{
            'id': msg.id,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'sender_id': msg.sender_id,
            'sender_name': msg.sender.name
        } for msg in messages]
    })

@app.route('/api/unread-count')
@login_required
def get_unread_count():
    from models import Message

    count = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=False
    ).count() if hasattr(Message, 'is_read') else 0

    return jsonify({'count': count})

# Posts routes
@app.route('/posts')
@login_required
def posts():
    from models import Post, Comment, User, Friendship, PostLike, CommentLike

    # Get all friends' IDs
    friends_ids = []
    friendships = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) |
        (Friendship.user2_id == current_user.id)
    ).all()

    for friendship in friendships:
        friend_id = friendship.user2_id if friendship.user1_id == current_user.id else friendship.user1_id
        friends_ids.append(friend_id)

    # Include current user's posts
    friends_ids.append(current_user.id)

    # Get posts from friends and current user
    posts_query = Post.query.filter(
        Post.author_id.in_(friends_ids)
    ).order_by(Post.created_at.desc()).all()

    posts_data = []
    for post in posts_query:
        # Get like counts
        likes = PostLike.query.filter_by(post_id=post.id, vote_type=1).count()
        dislikes = PostLike.query.filter_by(post_id=post.id, vote_type=-1).count()
        user_like = PostLike.query.filter_by(post_id=post.id, user_id=current_user.id).first()

        # Get comments count
        comments_count = Comment.query.filter_by(post_id=post.id).count()

        # Get recent comments (first 3 for preview)
        recent_comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.created_at.asc()).limit(3).all()

        posts_data.append({
            'post': post,
            'author': post.author,
            'likes': likes,
            'dislikes': dislikes,
            'user_vote_type': user_like.vote_type if user_like else 0,
            'comments_count': comments_count,
            'recent_comments': recent_comments
        })

    return render_template('posts.html', posts_data=posts_data)

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'GET':
        return render_template('create_post.html')

    content = request.form.get('content')
    category = request.form.get('category')  # 'personal' or 'professional'
    ai_generate = request.form.get('ai_generate') == 'on'

    if not content:
        flash('Post content cannot be empty', 'error')
        return render_template('create_post.html')

    if category not in ['personal', 'professional']:
        flash('Invalid category selected', 'error')
        return render_template('create_post.html')

    # If AI generation is requested
    if ai_generate:
        try:
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

            prompt = f"""
            Generate a {category} post for a social media platform.
            The user's input is: "{content}"

            Please rewrite this as an engaging {category} post. Keep it concise and appropriate for social media.
            Just return the post content, no additional text.
            """

            response = client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4o'),
                messages=[
                    {"role": "system", "content": "You are a helpful social media content generator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )

            generated_content = response.choices[0].message.content.strip()
            content = generated_content

        except Exception as e:
            flash(f'AI generation failed: {str(e)}. Using your original content.', 'warning')

    # Create the post
    from models import Post
    post = Post(
        author_id=current_user.id,
        content=content,
        category=category,
        is_ai_generated=ai_generate
    )

    db.session.add(post)
    db.session.commit()

    # Analyze with AI and create AI comment
    try:
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Analyze the post
        analysis_prompt = f"""
        Analyze this {category} social media post:

        "{content}"

        Provide a brief analysis of:
        1. Does the content match the {category} category?
        2. What kind of sentiment does it convey?
        3. Any notable aspects?
        Keep it concise.
        """

        analysis_response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o'),
            messages=[
                {"role": "system", "content": "You are analyzing a social media post."},
                {"role": "user", "content": analysis_prompt}
            ],
            max_tokens=100,
            temperature=0.3
        )

        post.ai_analysis = analysis_response.choices[0].message.content.strip()

        # Generate AI comment
        comment_prompt = f"""
        As Swift (an AI assistant), write a brief, helpful comment on this {category} post:

        "{content}"

        Guidelines:
        - If it's a personal post about struggles (job loss, bad day, etc.), be empathetic
        - If it's a professional post, be supportive and possibly add value
        - If the content doesn't match the category, gently point it out
        - Be friendly and concise
        - Write as if you're a helpful AI assistant named Swift
        """

        comment_response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o'),
            messages=[
                {"role": "system", "content": "You are Swift, an AI assistant commenting on social media posts."},
                {"role": "user", "content": comment_prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )

        ai_comment_content = comment_response.choices[0].message.content.strip()

        # Create AI comment
        from models import Comment
        ai_comment = Comment(
            post_id=post.id,
            author_id=None,  # AI doesn't have a user ID
            content=ai_comment_content,
            is_ai_comment=True
        )

        db.session.add(ai_comment)

    except Exception as e:
        print(f"AI analysis failed: {str(e)}")
        # Post is still created even if AI analysis fails

    db.session.commit()

    # Log post creation
    log_post_created(current_user.id, post.id, category)
    flash('Post created successfully!', 'success')
    return redirect(url_for('posts'))

@app.route('/post/<int:post_id>')
@login_required
def view_post(post_id):
    from models import Post, Comment, User, Friendship, PostLike, CommentLike

    post = Post.query.get_or_404(post_id)

    # Check if user can view this post (only friends and post author)
    if post.author_id != current_user.id:
        if not are_friends(current_user.id, post.author_id):
            flash('You can only view posts from friends', 'error')
            return redirect(url_for('posts'))

    # Get post details
    likes = PostLike.query.filter_by(post_id=post.id, vote_type=1).count()
    dislikes = PostLike.query.filter_by(post_id=post.id, vote_type=-1).count()
    user_like = PostLike.query.filter_by(post_id=post.id, user_id=current_user.id).first()

    # Get all comments
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.created_at.asc()).all()

    # Process comments with like info
    comments_data = []
    for comment in comments:
        if comment.is_ai_comment:
            comment_author = None
            comment_likes = 0
            comment_dislikes = 0
            user_comment_like = 0
        else:
            comment_author = comment.author
            comment_likes = CommentLike.query.filter_by(comment_id=comment.id, vote_type=1).count()
            comment_dislikes = CommentLike.query.filter_by(comment_id=comment.id, vote_type=-1).count()
            user_comment_like = CommentLike.query.filter_by(comment_id=comment.id, user_id=current_user.id).first()
            user_comment_like = user_comment_like.vote_type if user_comment_like else 0

        comments_data.append({
            'comment': comment,
            'author': comment_author,
            'likes': comment_likes,
            'dislikes': comment_dislikes,
            'user_vote_type': user_comment_like
        })

    return render_template('view_post.html',
                         post=post,
                         author=post.author,
                         likes=likes,
                         dislikes=dislikes,
                         user_vote_type=user_like.vote_type if user_like else 0,
                         comments_data=comments_data)

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    from models import Post, Comment

    post = Post.query.get_or_404(post_id)

    # Check if user can comment (only friends and post author)
    if post.author_id != current_user.id:
        if not are_friends(current_user.id, post.author_id):
            flash('You can only comment on posts from friends', 'error')
            return redirect(url_for('posts'))

    content = request.form.get('content')
    if not content:
        flash('Comment cannot be empty', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    comment = Comment(
        post_id=post_id,
        author_id=current_user.id,
        content=content,
        is_ai_comment=False
    )

    db.session.add(comment)
    db.session.commit()

    # Log comment creation
    log_comment_created(current_user.id, post_id, comment.id, is_ai=False)

    flash('Comment added successfully', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_post_like(post_id):
    from models import Post, PostLike

    post = Post.query.get_or_404(post_id)

    # Check if user can like (only friends and post author)
    if post.author_id != current_user.id:
        if not are_friends(current_user.id, post.author_id):
            return jsonify({'error': 'Unauthorized'}), 403

    vote_type = request.json.get('vote_type', 1)  # 1 for like, -1 for dislike

    existing_like = PostLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()

    if existing_like:
        if existing_like.vote_type == vote_type:
            # Remove like/dislike if same vote type
            db.session.delete(existing_like)
            action = 'removed'
        else:
            # Change vote type
            existing_like.vote_type = vote_type
            action = 'changed'
    else:
        # Add new like/dislike
        new_like = PostLike(post_id=post_id, user_id=current_user.id, vote_type=vote_type)
        db.session.add(new_like)
        action = 'added'
        # Log like/dislike
        if vote_type == 1:
            log_post_liked(current_user.id, post_id)
        else:
            log_post_disliked(current_user.id, post_id)

    db.session.commit()

    # Get updated counts
    likes = PostLike.query.filter_by(post_id=post_id, vote_type=1).count()
    dislikes = PostLike.query.filter_by(post_id=post_id, vote_type=-1).count()

    return jsonify({
        'action': action,
        'likes': likes,
        'dislikes': dislikes,
        'user_vote_type': vote_type if action != 'removed' else 0
    })

@app.route('/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def toggle_comment_like(comment_id):
    from models import Comment, CommentLike

    comment = Comment.query.get_or_404(comment_id)

    # Check if user can like comment
    post = comment.post
    if post.author_id != current_user.id and not are_friends(current_user.id, post.author_id):
        return jsonify({'error': 'Unauthorized'}), 403

    vote_type = request.json.get('vote_type', 1)  # 1 for like, -1 for dislike

    existing_like = CommentLike.query.filter_by(comment_id=comment_id, user_id=current_user.id).first()

    if existing_like:
        if existing_like.vote_type == vote_type:
            # Remove like/dislike if same vote type
            db.session.delete(existing_like)
        else:
            # Change vote type
            existing_like.vote_type = vote_type
    else:
        # Add new like/dislike
        new_like = CommentLike(comment_id=comment_id, user_id=current_user.id, vote_type=vote_type)
        db.session.add(new_like)

    db.session.commit()

    # Get updated counts
    likes = CommentLike.query.filter_by(comment_id=comment_id, vote_type=1).count()
    dislikes = CommentLike.query.filter_by(comment_id=comment_id, vote_type=-1).count()

    return jsonify({
        'likes': likes,
        'dislikes': dislikes
    })

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    from models import Comment

    comment = Comment.query.get_or_404(comment_id)

    # Only comment author can delete
    if comment.author_id != current_user.id:
        flash('You can only delete your own comments', 'error')
        return redirect(url_for('view_post', post_id=comment.post_id))

    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()

    flash('Comment deleted successfully', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    from models import Post

    post = Post.query.get_or_404(post_id)

    # Only post author can delete
    if post.author_id != current_user.id:
        flash('You can only delete your own posts', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    db.session.delete(post)  # This will cascade delete comments due to the relationship
    db.session.commit()

    flash('Post deleted successfully', 'success')
    return redirect(url_for('posts'))

# Swift Chatbot API Routes
@app.route('/api/swift/chat', methods=['POST'])
@login_required
def swift_chat():
    from models import ChatHistory, User, Friendship, Post

    data = request.json
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', str(uuid.uuid4()))

    if not user_message:
        return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400

    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Build context based on user type
        if current_user.is_admin:
            # Admin context - can access site-wide information
            context_prompt = f"""
            You are Swift, an AI assistant for a social media platform. The current user is an admin.

            User query: "{user_message}"

            You can provide information about:
            - Website statistics (ask for specific data if needed)
            - User management (general info, not personal data)
            - Platform features and help
            - General news and information

            Do NOT share specific user personal information unless explicitly requested by the admin.
            Be helpful, professional, and concise.
            """
        else:
            # Regular user context - privacy-focused
            # Get user's friends and their posts
            friends_ids = []
            friendships = Friendship.query.filter(
                (Friendship.user1_id == current_user.id) |
                (Friendship.user2_id == current_user.id)
            ).all()

            for friendship in friendships:
                friend_id = friendship.user2_id if friendship.user1_id == current_user.id else friendship.user1_id
                friends_ids.append(friend_id)

            # Get recent posts from friends
            recent_posts = []
            if friends_ids:
                posts = Post.query.filter(
                    Post.author_id.in_(friends_ids)
                ).order_by(Post.created_at.desc()).limit(5).all()

                for post in posts:
                    recent_posts.append({
                        'author': post.author.name,
                        'content': post.content[:100] + '...' if len(post.content) > 100 else post.content,
                        'category': post.category
                    })

            context_prompt = f"""
            You are Swift, an AI assistant for a social media platform. The current user is a regular user named {current_user.name}.

            User query: "{user_message}"

            You can help with:
            - Information about their friends' posts (only from friends they are connected to)
            - Post curation and ideas
            - General conversation and news
            - Platform features and help

            Recent friend activities:
            {format_posts_for_context(recent_posts) if recent_posts else "No recent friend activities to show."}

            IMPORTANT PRIVACY RULES:
            - Only mention posts from users who are friends with {current_user.name}
            - Do NOT share information about users who are not friends
            - Do NOT reveal any personal or private information
            - Keep responses friendly but professional
            - Be helpful and engaging
            """

        # Get chat history from Chroma for context
        try:
            history_results = chroma_manager.search_conversations(
                str(current_user.id),
                user_message,
                limit=3
            )

            if history_results and history_results.get('documents') and history_results['documents'][0]:
                context_prompt += "\n\nRecent conversation context:\n"
                for doc in history_results['documents'][0][:3]:  # Last 3 messages
                    import json
                    conv = json.loads(doc)
                    context_prompt += f"User: {conv['user']}\nAssistant: {conv['assistant']}\n"
        except Exception as e:
            print(f"Error fetching chat history from Chroma: {e}")

        # Generate response
        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o'),
            messages=[
                {"role": "system", "content": context_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )

        ai_response = response.choices[0].message.content.strip()

        # Save to database
        chat_entry = ChatHistory(
            user_id=current_user.id,
            session_id=session_id,
            user_message=user_message,
            ai_response=ai_response
        )
        db.session.add(chat_entry)
        db.session.commit()

        # Log chatbot interaction
        log_chatbot_interaction(current_user.id, session_id)

        # Save to Chroma Cloud
        try:
            chroma_id = chroma_manager.add_conversation(
                str(current_user.id),
                session_id,
                user_message,
                ai_response
            )
            # Update database with Chroma ID
            chat_entry.chroma_id = chroma_id
            db.session.commit()
        except Exception as e:
            print(f"Error saving to Chroma Cloud: {e}")
            # Continue even if Chroma fails

        return jsonify({
            'success': True,
            'response': ai_response
        })

    except Exception as e:
        print(f"Error in Swift chat: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Sorry, I encountered an error processing your request.'
        }), 500

@app.route('/api/swift/chat/session/<session_id>')
@login_required
def get_chat_session(session_id):
    """Get all messages for a specific session"""
    from models import ChatHistory

    try:
        messages = ChatHistory.query.filter_by(
            user_id=current_user.id,
            session_id=session_id
        ).order_by(ChatHistory.created_at.asc()).all()

        return jsonify({
            'success': True,
            'messages': [{
                'user_message': msg.user_message,
                'ai_response': msg.ai_response,
                'created_at': msg.created_at.isoformat()
            } for msg in messages]
        })
    except Exception as e:
        print(f"Error fetching chat session: {e}")
        return jsonify({
            'success': False,
            'error': 'Error loading chat session'
        }), 500

@app.route('/api/swift/chat/history')
@login_required
def get_chat_history():
    """Get all chat sessions for the user"""
    from models import ChatHistory
    from sqlalchemy import func

    try:
        # Get unique sessions with last message
        sessions = db.session.query(
            ChatHistory.session_id,
            func.max(ChatHistory.created_at).label('last_message_time'),
            func.max(ChatHistory.user_message).label('last_message')
        ).filter_by(
            user_id=current_user.id
        ).group_by(
            ChatHistory.session_id
        ).order_by(
            func.max(ChatHistory.created_at).desc()
        ).all()

        return jsonify({
            'success': True,
            'sessions': [{
                'session_id': session.session_id,
                'created_at': session.last_message_time.isoformat(),
                'last_message': session.last_message[:50] + '...' if len(session.last_message) > 50 else session.last_message
            } for session in sessions]
        })
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return jsonify({
            'success': False,
            'error': 'Error loading chat history'
        }), 500

@app.route('/api/swift/chat/session/<session_id>', methods=['DELETE'])
@login_required
def delete_chat_session(session_id):
    """Delete a specific chat session"""
    from models import ChatHistory

    try:
        # Get all messages in the session
        chat_entries = ChatHistory.query.filter_by(
            user_id=current_user.id,
            session_id=session_id
        ).all()

        # Delete from Chroma Cloud
        for entry in chat_entries:
            if entry.chroma_id:
                chroma_manager.delete_conversation(entry.chroma_id)

        # Delete from database
        ChatHistory.query.filter_by(
            user_id=current_user.id,
            session_id=session_id
        ).delete()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Chat session deleted successfully'
        })
    except Exception as e:
        print(f"Error deleting chat session: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Error deleting chat session'
        }), 500

@app.route('/api/swift/chat/history', methods=['DELETE'])
@login_required
def delete_chat_history():
    """Delete all chat history for the user"""
    from models import ChatHistory

    try:
        # Get all user's chat entries
        chat_entries = ChatHistory.query.filter_by(user_id=current_user.id).all()

        # Delete from Chroma Cloud
        for entry in chat_entries:
            if entry.chroma_id:
                chroma_manager.delete_conversation(entry.chroma_id)

        # Delete from database
        ChatHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Chat history deleted successfully'
        })
    except Exception as e:
        print(f"Error deleting chat history: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Error deleting chat history'
        }), 500

def format_posts_for_context(posts):
    """Format posts for AI context"""
    if not posts:
        return "No recent posts from friends."

    formatted = []
    for post in posts[:3]:  # Limit to 3 most recent
        formatted.append(f"- {post['author']} shared a {post['category']} post: {post['content']}")
    return "\n".join(formatted)

@app.route('/logout')
@login_required
def logout():
    user_id = current_user.id
    logout_user()
    # Log logout activity
    log_logout(user_id)
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('signin'))

@app.route('/activity-log')
@login_required
def activity_log():
    from models import ActivityLog, User
    from datetime import datetime, timedelta

    # Get filter parameters
    filter_type = request.args.get('filter', 'all')  # all, days, weeks, months, years
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Calculate date range based on filter
    end_date = datetime.utcnow()
    if filter_type == 'days':
        start_date = end_date - timedelta(days=7)
    elif filter_type == 'weeks':
        start_date = end_date - timedelta(weeks=4)
    elif filter_type == 'months':
        start_date = end_date - timedelta(days=30)
    elif filter_type == 'years':
        start_date = end_date - timedelta(days=365)
    else:  # all
        start_date = None

    # Build query
    query = ActivityLog.query.filter_by(user_id=current_user.id)

    if start_date:
        query = query.filter(ActivityLog.created_at >= start_date)

    # Order by most recent first
    query = query.order_by(ActivityLog.created_at.desc())

    # Paginate results
    activities = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Get total user count for admin
    total_users = 0
    if current_user.is_admin:
        total_users = User.query.count()

    return render_template(
        'activity_log.html',
        activities=activities,
        filter_type=filter_type,
        total_users=total_users
    )

@app.route('/admin')
@login_required
def admin_panel():
    # Check if user is admin
    if not current_user.is_admin:
        flash('You are not authorized to access the admin panel', 'error')
        return redirect(url_for('profile'))

    from models import User, Post, Message, Comment, FriendRequest, Friendship, ChatHistory

    # Get all users except current admin
    users = User.query.filter(User.id != current_user.id).order_by(User.created_at.desc()).all()

    # Add statistics for each user
    users_with_stats = []
    for user in users:
        # Get user statistics
        posts_count = Post.query.filter_by(author_id=user.id).count()
        comments_count = Comment.query.filter_by(author_id=user.id).count()
        messages_sent = Message.query.filter_by(sender_id=user.id).count()
        messages_received = Message.query.filter_by(receiver_id=user.id).count()
        friends_count = Friendship.query.filter(
            (Friendship.user1_id == user.id) | (Friendship.user2_id == user.id)
        ).count()
        chat_sessions = ChatHistory.query.filter_by(user_id=user.id).distinct(ChatHistory.session_id).count()

        users_with_stats.append({
            'user': user,
            'posts_count': posts_count,
            'comments_count': comments_count,
            'messages_sent': messages_sent,
            'messages_received': messages_received,
            'friends_count': friends_count,
            'chat_sessions': chat_sessions
        })

    return render_template('admin.html', users_with_stats=users_with_stats)

@app.route('/admin/user/<int:user_id>')
@login_required
def admin_view_user(user_id):
    # Check if user is admin
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    from models import User, Post, Message, Comment, FriendRequest, Friendship, ChatHistory, Profile

    # Get user details
    user = User.query.get_or_404(user_id)
    profile = Profile.query.filter_by(user_id=user_id).first()

    # Get user statistics
    stats = {
        'posts_count': Post.query.filter_by(author_id=user_id).count(),
        'comments_count': Comment.query.filter_by(author_id=user_id).count(),
        'messages_sent': Message.query.filter_by(sender_id=user_id).count(),
        'messages_received': Message.query.filter_by(receiver_id=user_id).count(),
        'friends_count': Friendship.query.filter(
            (Friendship.user1_id == user_id) | (Friendship.user2_id == user_id)
        ).count(),
        'pending_requests_sent': FriendRequest.query.filter_by(sender_id=user_id, status='pending').count(),
        'pending_requests_received': FriendRequest.query.filter_by(receiver_id=user_id, status='pending').count(),
        'chat_sessions': ChatHistory.query.filter_by(user_id=user_id).distinct(ChatHistory.session_id).count()
    }

    return render_template('admin_user_details.html', user=user, profile=profile, stats=stats)

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    # Check if user is admin
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_panel'))

    from models import User, Post, Message, Comment, FriendRequest, Friendship, ChatHistory, Profile, PostLike, CommentLike, ActivityLog

    try:
        # Get user before deletion
        user_to_delete = User.query.get_or_404(user_id)
        user_email = user_to_delete.email
        user_name = user_to_delete.name

        # Log the deletion
        log_activity(current_user.id, 'delete_user', f'Deleted user {user_name} ({user_email})', target_user_id=user_id)

        # Delete from Chroma Cloud first (chat history)
        try:
            chroma_deleted = chroma_manager.delete_all_user_conversations(str(user_id))
            if chroma_deleted:
                print(f"Successfully deleted Chroma conversations for user {user_id}")
        except Exception as e:
            print(f"Error deleting from Chroma: {e}")

        # Delete friendships (both sides)
        friendships = Friendship.query.filter(
            (Friendship.user1_id == user_id) | (Friendship.user2_id == user_id)
        ).all()
        for friendship in friendships:
            db.session.delete(friendship)

        # Delete friend requests (both sent and received)
        friend_requests = FriendRequest.query.filter(
            (FriendRequest.sender_id == user_id) | (FriendRequest.receiver_id == user_id)
        ).all()
        for req in friend_requests:
            db.session.delete(req)

        # Delete all posts (comments will be deleted automatically due to CASCADE)
        Post.query.filter_by(author_id=user_id).delete()

        # Delete comments and likes made BY the user on other posts
        Comment.query.filter_by(author_id=user_id).delete()
        CommentLike.query.filter_by(user_id=user_id).delete()
        PostLike.query.filter_by(user_id=user_id).delete()

        # Delete messages (both sent and received)
        Message.query.filter(
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        ).delete()

        # Delete chat history
        ChatHistory.query.filter_by(user_id=user_id).delete()

        # Delete activity logs (both as user and as target_user)
        ActivityLog.query.filter_by(user_id=user_id).delete()
        ActivityLog.query.filter_by(target_user_id=user_id).delete()

        # Delete profile
        Profile.query.filter_by(user_id=user_id).delete()

        # Finally delete the user
        db.session.delete(user_to_delete)
        db.session.commit()

        flash(f'Successfully deleted user {user_name} ({user_email}) and all associated data', 'success')

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user: {e}")
        flash(f'Error deleting user: {str(e)}', 'error')

    return redirect(url_for('admin_panel'))

# Template filters
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to <br> tags"""
    if text is None:
        return ''
    from markupsafe import Markup
    return Markup(str(text).replace('\n', '<br>\n'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='localhost', port=5000)