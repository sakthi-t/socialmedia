# Social Media App

A feature-rich social media application built with Flask, designed to connect friends, share posts, and interact with AI-powered features.

## 🌟 Features

### Authentication & User Management
- **Secure Authentication**: Session-based authentication with GitHub OAuth integration
- **User Registration**: Complete signup flow with email validation and password hashing
- **Admin Dashboard**: Dedicated admin panel for user management and system oversight
- **Profile Management**: Comprehensive user profiles with customizable information

### Social Networking
- **Friend System**: Send, accept, and decline friend requests with real-time notifications
- **Profile Discovery**: Search and view other user profiles with privacy controls
- **Friend Lists**: Visual friend management with status indicators

### Messaging System
- **Real-time Messaging**: Private messaging between friends with instant delivery
- **Message Threads**: Organized conversation management with persistent history
- **Friend-based Access**: Only connected users can exchange messages
- **Mobile Responsive**: Full-screen messaging experience on mobile devices

### Content Creation & Interaction
- **Post Creation**: Share thoughts with personal or professional post categories
- **AI-Powered Analysis**: Intelligent post analysis using GPT-4 with empathetic responses
- **Comment System**: Engage with posts through threaded comments
- **Voting Mechanism**: Upvote/downvote posts and comments for community feedback
- **Content Moderation**: Users can manage their own posts and comments

### Swift AI Assistant
- **Chatbot Integration**: Facebook Messenger-style AI assistant named Swift
- **Contextual Awareness**: Privacy-aware conversations respecting user relationships
- **Chat History**: Persistent conversation storage with Chroma Cloud integration
- **Multi-session Support**: Continue conversations across different sessions
- **News & Updates**: Access to current events and general information

### Activity Monitoring
- **Comprehensive Logging**: Detailed activity tracking for all user interactions
- **Admin Analytics**: System-wide user statistics and engagement metrics
- **Filterable Views**: Activity logs filtered by day, week, month, or year
- **Privacy Preservation**: Activity logs respect user privacy boundaries

## 🛠 Tech Stack

### Backend
- **Framework**: Flask 
- **Database**: PostgreSQL 
- **ORM**: SQLAlchemy 
- **Authentication**: Flask-Login with session management
- **Vector Database**: Chroma Cloud for AI conversations

### Frontend
- **Languages**: HTML5, CSS3, JavaScript
- **Styling**: Bootstrap framework with custom enhancements
- **File Uploads**: Cloudinary integration for profile pictures
- **Responsive Design**: Mobile-first approach with adaptive layouts

### AI & Machine Learning
- **Language Model**: OpenAI GPT-4o
- **AI Framework**: LangChain for advanced AI workflows
- **Embeddings**: Chroma Cloud for conversation persistence
- **Content Analysis**: Automated post classification and sentiment analysis

### Development Tools
- **Environment Management**: Python-dotenv
- **Database Migrations**: Alembic
- **Testing**: Pytest with coverage reporting
- **Deployment**: Gunicorn WSGI server

## 📁 Project Structure

```
socialmedia/
├── app.py                 # Main Flask application
├── models.py             # SQLAlchemy database models
├── requirements.txt      # Python dependencies
├── activity_logger.py    # Activity tracking utilities
├── chroma_integration.py # Chroma Cloud integration
├── templates/           # HTML templates
│   ├── signin.html      # Sign-in page
│   ├── profile.html     # User profile
│   ├── messages.html    # Messaging interface
│   ├── posts.html       # Posts and feed
│   └── admin.html       # Admin dashboard
├── static/              # CSS, JavaScript, and static assets
└── create_*.py          # Database creation scripts
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+
- PostgreSQL database 
- OpenAI API key
- Cloudinary account (for image uploads)
- Chroma Cloud account (for AI conversations)

### Environment Variables
Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://username:password@host:port/database_name

# Flask Configuration
SECRET_KEY=your-secret-key-here
ADMIN_EMAIL=admin@example.com

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# OpenAI API
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o

# Cloudinary (for image uploads)
CLOUDINARY_CLOUD_NAME=your-cloudinary-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret

# Chroma Cloud (for AI conversations)
CHROMA_API_KEY=your-chroma-api-key
CHROMA_TENANT=your-chroma-tenant
CHROMA_DATABASE=your-chroma-database
```

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/socialmedia.git
   cd socialmedia
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create database tables**
   ```bash
   python create_all_tables.py
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

## 🌐 Deployment

### Railway Deployment
1. Connect your GitHub repository to Railway
2. Set all environment variables in Railway dashboard
3. Configure the PostgreSQL database provided by Railway
4. Deploy the application

### Environment Variables for Production
Ensure all variables from the `.env` file are set in your deployment environment, particularly:
- `DATABASE_URL` (Railway PostgreSQL connection string)
- `SECRET_KEY` (generate a secure, unique key)
- All API keys and OAuth credentials

## 📱 Usage

### Getting Started
1. **Sign Up**: Create a new account with email and password or use GitHub OAuth
2. **Create Profile**: Add your profile information and upload a profile picture
3. **Find Friends**: Search for other users and send friend requests
4. **Start Conversations**: Message friends and interact with their posts
5. **Explore AI**: Chat with Swift for assistance and entertainment

### Key Workflows
- **Profile Management**: Update your information, view others' profiles, manage friendships
- **Content Creation**: Create posts, comment on friends' content, engage with the community
- **Communication**: Send private messages, interact with the AI assistant
- **Activity Tracking**: Monitor your social media activity and engagement patterns

## 🔒 Security Features

- **Password Security**: Bcrypt hashing for secure password storage
- **Session Management**: Secure session-based authentication
- **Input Validation**: Email validation and form sanitization
- **Admin Controls**: Role-based access control for administrative functions
- **Privacy Protection**: Activity logs respect user privacy boundaries

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for providing the GPT-4 API that powers our AI features
- Cloudinary for reliable image hosting and processing
- Chroma for the vector database that enables AI conversation persistence
- Flask community for the robust web framework
- Bootstrap for the responsive UI components

## 📞 Support

For support, please email [your-email@example.com] or create an issue in the GitHub repository.

---

**Built with ❤️ for connecting people and fostering meaningful connections**