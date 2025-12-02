# Testing the Social Media App - Step 1

## Setup Instructions

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create database tables:
```bash
python create_tables.py
```

3. Run the application:
```bash
python app.py
```

4. Visit http://localhost:5000 in your browser

## Test Scenarios

### 1. Sign Up Test
- Click on "Sign Up" tab
- Fill in:
  - Username: testuser
  - Email: test@example.com
  - Password: mypassword123
  - Confirm Password: mypassword123
- Click "Sign Up"
- You should be redirected to sign-in page with success message

### 2. Sign In Test
- Use the credentials you just created:
  - Email: test@example.com
  - Password: mypassword123
- Click "Sign In"
- You should be redirected to profile page

### 3. GitHub OAuth Test
- Click "Sign in with GitHub" button
- Authorize the application on GitHub
- You should be redirected back to profile page

### 4. Logout Test
- Click on your username in the navbar
- Click "Logout"
- You should be redirected to sign-in page

### 5. Admin Test
- The admin email is configured as: t.shakthi@gmail.com
- If you sign up or sign in with this email, you should see "Admin Panel" option in the dropdown

## Notes
- The navbar search, messages, friends, and create profile features show alerts for now (will be implemented in later steps)
- The app uses session-based authentication
- All user data is stored in the PostgreSQL database