#!/usr/bin/env python3
"""
Create a test user with a proper JWT token using the existing auth system
"""

import json
import hashlib
import bcrypt
from datetime import datetime, timedelta

def create_jwt_test_user():
    """Create a test user with a proper JWT token"""
    
    # Create test user with bcrypt hashed password
    password = "testpass123"
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    test_user = {
        "username": "testuser",
        "password": hashed_password,
        "role": "user",
        "firstname": "Test",
        "lastname": "User",
        "created_at": datetime.now().isoformat()
    }
    
    # Read existing users
    try:
        with open('user.json', 'r') as f:
            users = json.load(f)
    except FileNotFoundError:
        users = []
    
    # Check if test user already exists
    existing_user = None
    for user in users:
        if user.get('username') == 'testuser':
            existing_user = user
            break
    
    if existing_user:
        # Update existing user
        existing_user.update(test_user)
        print("✅ Updated existing test user")
    else:
        # Add new test user
        users.append(test_user)
        print("✅ Created new test user")
    
    # Save updated users
    with open('user.json', 'w') as f:
        json.dump(users, f, indent=2)
    
    print(f"🔑 Test User Credentials:")
    print(f"   Username: testuser")
    print(f"   Password: testpass123")
    print(f"   Role: user")
    print()
    print("💡 Now you need to login through the API to get a JWT token")
    print()
    
    return test_user

def test_login_and_earnings():
    """Test the login process and then test earnings summary"""
    import requests
    
    print("🧪 Testing login and earnings summary...")
    
    # Step 1: Login to get JWT token
    print("1️⃣ Logging in to get JWT token...")
    try:
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        response = requests.post("http://localhost:8000/api/login", json=login_data)
        print(f"Login Status: {response.status_code}")
        
        if response.status_code == 200:
            login_result = response.json()
            if login_result.get('success'):
                token = login_result['token']
                print(f"✅ Login successful! JWT Token: {token[:50]}...")
                
                # Step 2: Test earnings summary with JWT token
                print("2️⃣ Testing earnings summary with JWT token...")
                headers = {"Authorization": f"Bearer {token}"}
                earnings_response = requests.get("http://localhost:8000/api/earning-summary?page=1&per_page=1000", headers=headers)
                
                print(f"Earnings Status: {earnings_response.status_code}")
                
                if earnings_response.status_code == 200:
                    data = earnings_response.json()
                    print(f"✅ SUCCESS! Found {len(data.get('results', []))} earnings")
                    if data.get('results'):
                        print(f"First result: {data['results'][0]['ticker']}")
                        print(f"Sample data: {data['results'][0]}")
                else:
                    print(f"❌ Earnings failed: {earnings_response.text}")
                    
            else:
                print(f"❌ Login failed: {login_result.get('message')}")
        else:
            print(f"❌ Login request failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    print("🔧 Creating JWT test user...")
    print("=" * 50)
    
    create_jwt_test_user()
    
    print("=" * 50)
    test_login_and_earnings()
    
    print("=" * 50)
    print("🎯 Next steps:")
    print("   1. Use testuser/testpass123 in your frontend login")
    print("   2. The frontend will get a JWT token automatically")
    print("   3. The earnings summary should now display data")
    print("   4. Or use the login API directly to get a token")
