import database as db
import face_recognition_module as frm

def register_user():
    """Register new user with username and password, optionally with face"""
    print("\n" + "="*50)
    print("REGISTER NEW ACCOUNT")
    print("="*50)
    
    while True:
        username = input("\nEnter username: ").strip()
        
        if len(username) < 3:
            print("Username must be at least 3 characters long")
            continue
        
        if db.user_exists(username):
            print("Username already exists! Try another.")
            continue
        
        break
    
    while True:
        password = input("Enter password: ").strip()
        
        if len(password) < 4:
            print("Password must be at least 4 characters long")
            continue
        
        confirm_password = input("Confirm password: ").strip()
        
        if password != confirm_password:
            print("Passwords do not match!")
            continue
        
        break
    
    # Ask if user wants to register face
    print("\n" + "-"*50)
    print("Do you want to register your face for this account?")
    print("This allows you to login with face recognition")
    print("-"*50)
    
    choice = input("Register face? (y/n): ").strip().lower()
    
    face_encoding = None
    if choice == 'y':
        face_encoding, msg = frm.capture_face_encoding(username, mode='register')
        if face_encoding is None:
            print(f"Error: {msg}")
            print("Account will be created without face. You can add face later.")
        else:
            print(f"Success: {msg}")
    
    # Save user to database
    success, message = db.add_user(username, password, face_encoding)
    
    if success:
        print("\n" + "="*50)
        print("Account created successfully!")
        if face_encoding is not None:
            print("You can login with password or face recognition")
        else:
            print("You can login with password only")
        print("="*50)
        return True
    else:
        print(f"Error: {message}")
        return False

def login_user():
    """Login user with username and password or face recognition"""
    print("\n" + "="*50)
    print("LOGIN")
    print("="*50)
    
    username = input("\nEnter username: ").strip()
    
    if not db.user_exists(username):
        print("Username does not exist!")
        return None
    
    # Check if user has face registered
    has_face = db.user_has_face(username)
    
    if has_face:
        print("\n" + "-"*50)
        print("This account supports both password and face login")
        print("-"*50)
        login_choice = input("Login with (1) Face or (2) Password? Enter 1 or 2: ").strip()
        
        if login_choice == '1':
            return face_login(username)
        elif login_choice == '2':
            return password_login(username)
        else:
            print("Invalid choice!")
            return None
    else:
        # No face registered, use password only
        return password_login(username)

def password_login(username):
    """Login with password"""
    password = input("Enter password: ").strip()
    
    if db.verify_password(username, password):
        print("\n" + "="*50)
        print(f"Welcome {username}!")
        print("Login successful with password")
        print("="*50)
        return username
    else:
        print("Invalid password!")
        return None

def face_login(username):
    """Login with face recognition"""
    stored_encoding = db.get_user_face_encoding(username)
    
    if stored_encoding is None:
        print("No face data found for this user!")
        return None
    
    current_encoding, msg = frm.get_face_encoding_from_camera()
    
    if current_encoding is None:
        print(f"Error: {msg}")
        return None
    
    if frm.verify_face(stored_encoding, current_encoding):
        print("\n" + "="*50)
        print(f"Face matched! Welcome {username}!")
        print("Login successful with face recognition")
        print("="*50)
        return username
    else:
        print("\n" + "="*50)
        print("Face does not match!")
        print("Login failed")
        print("="*50)
        return None

def change_password(username):
    """Change password for logged-in user"""
    print("\n" + "="*50)
    print(f"CHANGE PASSWORD FOR {username}")
    print("="*50)
    
    # Verify current password
    current_password = input("\nEnter current password: ").strip()
    
    if not db.verify_password(username, current_password):
        print("Current password is incorrect!")
        return False
    
    while True:
        new_password = input("Enter new password: ").strip()
        
        if len(new_password) < 4:
            print("Password must be at least 4 characters long")
            continue
        
        if new_password == current_password:
            print("New password cannot be same as current password!")
            continue
        
        confirm_password = input("Confirm new password: ").strip()
        
        if new_password != confirm_password:
            print("Passwords do not match!")
            continue
        
        break
    
    if db.update_password(username, new_password):
        print("\n" + "="*50)
        print("Password changed successfully!")
        print("="*50)
        return True
    else:
        print("Error changing password!")
        return False

def add_face_to_account(username):
    """Add or update face encoding for existing account"""
    print("\n" + "="*50)
    print(f"REGISTER FACE FOR {username}")
    print("="*50)
    
    face_encoding, msg = frm.capture_face_encoding(username, mode='register')
    
    if face_encoding is None:
        print(f"Error: {msg}")
        return False
    
    if db.update_face_encoding(username, face_encoding):
        print("\n" + "="*50)
        print("Face registered successfully!")
        print("You can now login with face recognition")
        print("="*50)
        return True
    else:
        print("Error registering face!")
        return False
