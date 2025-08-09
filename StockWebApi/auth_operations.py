import json
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from fastapi import HTTPException, Depends, Header
from typing import Optional, Dict, Any

# Secret key for JWT tokens (in production, use a secure secret key)
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-here-change-in-production")

def load_users():
    """Load users from user.json file"""
    try:
        with open('user.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_users(users):
    """Save users to user.json file"""
    with open('user.json', 'w') as file:
        json.dump(users, file, indent=2)

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed_password):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_token(username, role, firstname, lastname):
    """Create a JWT token for the user"""
    payload = {
        'username': username,
        'role': role,
        'firstname': firstname,
        'lastname': lastname,
        'exp': datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def login_user(username, password):
    """Authenticate a user and return token if successful"""
    users = load_users()
    
    for user in users:
        if user['username'] == username and verify_password(password, user['password']):
            firstname = user.get('firstname', '')
            lastname = user.get('lastname', '')
            token = create_token(username, user['role'], firstname, lastname)
            return {
                'success': True,
                'token': token,
                'username': username,
                'role': user['role'],
                'firstname': firstname,
                'lastname': lastname
            }
    
    return {
        'success': False,
        'message': 'Invalid username or password'
    }

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Dependency to get current user from token"""
    if not authorization:
        raise HTTPException(status_code=401, detail={'error': 'No token provided'})
    
    # Remove 'Bearer ' prefix if present
    if authorization.startswith('Bearer '):
        token = authorization[7:]
    else:
        token = authorization
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail={'error': 'Invalid or expired token'})
    
    return payload

def require_auth(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency to require authentication"""
    return current_user

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency to require admin role"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail={'error': 'Admin access required'})
    return current_user

def create_default_users():
    """Create default users if user.json doesn't exist"""
    if not os.path.exists('user.json'):
        default_users = [
            {
                "username": "admin",
                "password": hash_password("admin123"),
                "role": "admin",
                "firstname": "Admin",
                "lastname": "User"
            },
            {
                "username": "user",
                "password": hash_password("user123"),
                "role": "user",
                "firstname": "Regular",
                "lastname": "User"
            }
        ]
        save_users(default_users)
        print("Default users created:")
        print("Admin - username: admin, password: admin123")
        print("User - username: user, password: user123") 