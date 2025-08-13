import json
import os
import bcrypt
from typing import List, Dict, Any, Optional, Tuple

def load_users() -> List[Dict[str, Any]]:
    """Load users from the JSON file"""
    try:
        if os.path.exists('user.json'):
            with open('user.json', 'r') as file:
                return json.load(file)
        else:
            return []
    except Exception as e:
        print(f"Error loading users: {e}")
        return []

def save_users(users: List[Dict[str, Any]]) -> bool:
    """Save users to the JSON file"""
    try:
        with open('user.json', 'w') as file:
            json.dump(users, file, indent=2)
        return True
    except Exception as e:
        print(f"Error saving users: {e}")
        return False

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        print(f"Error hashing password: {e}")
        return ""

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def get_users_with_filters(username_filter: str = "", page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """Get users with filtering and pagination"""
    users = load_users()
    
    # Apply filters
    filtered_users = users
    
    if username_filter:
        filtered_users = [u for u in users if username_filter.lower() in u.get('username', '').lower()]
    
    # Apply pagination
    total = len(filtered_users)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_users = filtered_users[start_index:end_index]
    
    return {
        'results': paginated_users,
        'total': total,
        'page': page,
        'per_page': per_page
    }

def add_user_to_file(username: str, password: str, role: str = "user", firstname: str = "", lastname: str = "") -> Tuple[bool, str]:
    """Add a new user to the file"""
    try:
        users = load_users()
        
        # Check if username already exists
        if any(u.get('username', '').lower() == username.lower() for u in users):
            return False, f"User with username '{username}' already exists"
        
        # Hash the password
        hashed_password = hash_password(password)
        if not hashed_password:
            return False, "Failed to hash password"
        
        new_user = {
            'username': username.lower(),
            'password': hashed_password,
            'role': role,
            'firstname': firstname,
            'lastname': lastname
        }
        
        users.append(new_user)
        
        if save_users(users):
            return True, f"User '{username}' added successfully"
        else:
            return False, "Failed to save users"
            
    except Exception as e:
        return False, f"Error adding user: {str(e)}"

def update_user_in_file(old_username: str, new_username: str, password: str = "", role: str = "user", firstname: str = "", lastname: str = "") -> Tuple[bool, str]:
    """Update a user in the file"""
    try:
        users = load_users()
        
        # Find the user to update
        user_index = None
        for i, u in enumerate(users):
            if u.get('username', '').lower() == old_username.lower():
                user_index = i
                break
        
        if user_index is None:
            return False, f"User with username '{old_username}' not found"
        
        # Check if new username already exists (if changing username)
        if new_username.lower() != old_username.lower():
            if any(u.get('username', '').lower() == new_username.lower() for u in users):
                return False, f"User with username '{new_username}' already exists"
        
        # Prepare update data
        update_data = {
            'username': new_username.lower(),
            'role': role,
            'firstname': firstname,
            'lastname': lastname
        }
        
        # Only update password if provided
        if password:
            hashed_password = hash_password(password)
            if not hashed_password:
                return False, "Failed to hash password"
            update_data['password'] = hashed_password
        else:
            # Keep existing password
            update_data['password'] = users[user_index]['password']
        
        # Update the user
        users[user_index] = update_data
        
        if save_users(users):
            return True, f"User '{old_username}' updated successfully to '{new_username}'"
        else:
            return False, "Failed to save users"
            
    except Exception as e:
        return False, f"Error updating user: {str(e)}"

def delete_user_from_file(username: str) -> Tuple[bool, str]:
    """Delete a user from the file"""
    try:
        users = load_users()
        
        # Find and remove the user
        original_count = len(users)
        users = [u for u in users if u.get('username', '').lower() != username.lower()]
        
        if len(users) == original_count:
            return False, f"User with username '{username}' not found"
        
        if save_users(users):
            return True, f"User '{username}' deleted successfully"
        else:
            return False, "Failed to save users"
            
    except Exception as e:
        return False, f"Error deleting user: {str(e)}"
