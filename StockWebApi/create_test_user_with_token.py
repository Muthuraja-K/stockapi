#!/usr/bin/env python3
"""
Create a test user with a valid token for testing the earnings summary endpoint
"""

import json
import hashlib
import secrets
from datetime import datetime, timedelta

def create_test_user():
    """Create a test user with a valid token"""
    
    # Generate a secure token
    token = secrets.token_urlsafe(32)
    
    # Create test user
    test_user = {
        "username": "testuser",
        "password": hashlib.sha256("testpass123".encode()).hexdigest(),
        "role": "user",
        "token": token,
        "token_expiry": (datetime.now() + timedelta(days=30)).isoformat(),
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
        # Update existing user with new token
        existing_user['token'] = token
        existing_user['token_expiry'] = test_user['token_expiry']
        print("✅ Updated existing test user with new token")
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
    print(f"   Token: {token}")
    print()
    print("💡 You can now:")
    print("   1. Login with these credentials in the frontend")
    print("   2. Or use the token directly in API calls")
    print()
    
    return token

def test_earnings_summary_with_token(token):
    """Test the earnings summary endpoint with the new token"""
    import requests
    
    print("🧪 Testing earnings summary endpoint with new token...")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("http://localhost:8000/api/earning-summary?page=1&per_page=1000", headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS! Found {len(data.get('results', []))} earnings")
            if data.get('results'):
                print(f"First result: {data['results'][0]['ticker']}")
        else:
            print(f"❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")

if __name__ == "__main__":
    print("🔧 Creating test user with valid token...")
    print("=" * 50)
    
    token = create_test_user()
    
    print("=" * 50)
    test_earnings_summary_with_token(token)
    
    print("=" * 50)
    print("🎯 Next steps:")
    print("   1. Use these credentials in your frontend login")
    print("   2. The earnings summary should now display data")
    print("   3. Or test the API directly with the token above")
