#!/usr/bin/env python3
"""
Script to create a test user with known credentials for testing
"""

import json
import bcrypt
from auth_operations import load_users, save_users

def create_test_user():
    """Create a test user with username 'admin' and password 'Stock@Friends'"""
    
    # Load existing users
    try:
        users = load_users()
    except FileNotFoundError:
        users = []
    
    # Check if admin already exists
    existing_user = next((user for user in users if user['username'] == 'admin'), None)
    if existing_user:
        print("User 'admin' already exists! Updating password...")
        # Update the existing admin user's password
        existing_user['password'] = bcrypt.hashpw("Stock@Friends".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        save_users(users)
        print("Admin password updated successfully!")
        print("Username: admin")
        print("Password: Stock@Friends")
        print("Role: admin")
        return
    
    # Create new admin user
    admin_password = "Stock@Friends"
    hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    admin_user = {
        "username": "admin",
        "password": hashed_password,
        "role": "admin",
        "firstname": "Admin",
        "lastname": "User"
    }
    
    # Add to users list
    users.append(admin_user)
    
    # Save updated users
    save_users(users)
    
    print("Admin user created successfully!")
    print("Username: admin")
    print("Password: Stock@Friends")
    print("Role: admin")

if __name__ == "__main__":
    create_test_user()
