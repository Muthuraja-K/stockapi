import json
import logging
from utils import load_users, save_users

def get_users_with_filters(username_param, page, per_page):
    """
    Get users with filtering and pagination
    """
    users = load_users()
    
    # Ensure all users have firstname and lastname fields (backward compatibility)
    for user in users:
        if 'firstname' not in user:
            user['firstname'] = ''
        if 'lastname' not in user:
            user['lastname'] = ''
    
    # Filter users if provided
    filtered_users = users
    if username_param:
        filtered_users = [u for u in users if username_param.lower() in u.get('username', '').lower()]
    
    # Apply pagination
    total = len(filtered_users)
    start = (page - 1) * per_page
    end = start + per_page
    paged_users = filtered_users[start:end]
    
    return {
        'total': total,
        'page': page,
        'per_page': per_page,
        'results': paged_users
    }

def add_user_to_file(username, password, role, firstname, lastname):
    """
    Add a new user to the users file
    """
    users = load_users()
    
    # Check if user already exists
    if any(u.get('username', '').lower() == username.lower() for u in users):
        return False, "User already exists"
    
    # Import bcrypt for password hashing
    import bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    users.append({
        'username': username,
        'password': hashed_password,
        'role': role,
        'firstname': firstname,
        'lastname': lastname
    })
    save_users(users)
    return True, "User added successfully"

def update_user_in_file(old_username, username, password, role, firstname, lastname):
    """
    Update an existing user in the users file
    """
    users = load_users()
    
    # Find and update the user
    found = False
    for u in users:
        if u.get('username', '').lower() == old_username.lower():
            # Check if new username already exists (if username is being changed)
            if username.lower() != old_username.lower() and any(existing.get('username', '').lower() == username.lower() and existing != u for existing in users):
                return False, "New username already exists"
            
            u['username'] = username
            u['role'] = role
            u['firstname'] = firstname
            u['lastname'] = lastname
            
            # Only update password if provided
            if password:
                import bcrypt
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                u['password'] = hashed_password
            
            found = True
            break
    
    if not found:
        return False, "User not found"
    
    save_users(users)
    return True, "User updated successfully"

def delete_user_from_file(username):
    """
    Delete a user from the users file
    """
    users = load_users()
    
    # Remove the user
    new_users = [u for u in users if u.get('username', '').lower() != username.lower()]
    
    if len(new_users) == len(users):
        return False, "User not found"
    
    save_users(new_users)
    return True, "User deleted successfully" 