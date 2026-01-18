import hashlib
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import os
from datetime import datetime
import numpy as np
import uuid
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# MongoDB Connection (read from MONGODB_URI in environment/.env)
MONGODB_URL = os.getenv('MONGODB_URI') or os.getenv('MONGODB_URL')
DB_NAME = 'face_recognition_db'
USERS_COLLECTION = 'users'
FACE_INDEX_COLLECTION = 'face_index'

if not MONGODB_URL:
    print("❌ No MongoDB URI found. Please set MONGODB_URI in a .env file or environment variables.")
    db = None
    users_collection = None
    face_index_collection = None
else:
    try:
        client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        # Test connection
        client.server_info()
        db = client[DB_NAME]
        users_collection = db[USERS_COLLECTION]
        face_index_collection = db[FACE_INDEX_COLLECTION]
        
        # Create indexes
        users_collection.create_index('username', unique=True)
        users_collection.create_index('face_id')
        face_index_collection.create_index('face_hash', unique=True)
        
        print("✅ MongoDB connected successfully!")
    except (ConnectionFailure, Exception) as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("Make sure MongoDB is running or provide MONGODB_URI environment variable")
        db = None
        users_collection = None
        face_index_collection = None

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def hash_face_encoding(face_encoding):
    """Create hash of face encoding to prevent duplicates"""
    if face_encoding is None:
        return None
    encoding_str = str(face_encoding)
    return hashlib.md5(encoding_str.encode()).hexdigest()
def generate_face_id():
    """Generate unique face ID"""
    return f"face_{str(uuid.uuid4())[:8]}"

def compare_faces(encoding1, encoding2, threshold=5000):
    """Compare two face encodings using Euclidean distance"""
    if encoding1 is None or encoding2 is None:
        return False
    try:
        face1 = np.array(encoding1)
        face2 = np.array(encoding2)
        distance = np.linalg.norm(face1 - face2)
        return distance < threshold
    except:
        return False

def find_similar_faces(face_encoding, threshold=5000):
    """Find all similar faces in database"""
    if users_collection is None or face_encoding is None:
        return []
    try:
        all_users = users_collection.find({'face_encoding': {'$exists': True, '$ne': None}})
        similar_faces = []
        for user in all_users:
            if compare_faces(face_encoding, user.get('face_encoding'), threshold):
                similar_faces.append({
                    'username': user['username'],
                    'face_id': user.get('face_id', 'N/A'),
                    'created_at': user.get('created_at', 'N/A')
                })
        return similar_faces
    except Exception as e:
        print(f"Error finding similar faces: {e}")
        return []

def user_exists(username):
    """Check if username already exists"""
    if users_collection is None:
        return False
    try:
        return users_collection.find_one({'username': username}) is not None
    except Exception as e:
        print(f"Error checking user: {e}")
        return False

def face_exists(face_encoding):
    """Check if face is already registered by another user"""
    if users_collection is None or face_encoding is None:
        return None
    try:
        face_hash = hash_face_encoding(face_encoding)
        result = users_collection.find_one({'face_hash': face_hash})
        return result['username'] if result else None
    except Exception as e:
        print(f"Error checking face: {e}")
        return None

def add_user(username, password, face_encoding=None):
    """Add new user to database"""
    if users_collection is None:
        return False, "Database connection failed"
    
    if user_exists(username):
        return False, "Username already exists"
    
    # Check if face is already registered
    if face_encoding is not None:
        existing_user = face_exists(face_encoding)
        if existing_user:
            return False, f"This face is already registered with username: {existing_user}"
        
        # Check for similar faces
        similar_faces = find_similar_faces(face_encoding)
        if similar_faces:
            usernames = ', '.join([f.get('username') for f in similar_faces])
            return False, f"Similar face found! Already registered to: {usernames}"
    
    try:
        face_hash = hash_face_encoding(face_encoding) if face_encoding else None
        face_id = generate_face_id() if face_encoding else None
        
        user_data = {
            'username': username,
            'password': hash_password(password),
            'face_encoding': face_encoding,
            'face_hash': face_hash,
            'face_id': face_id,
            'has_face': face_encoding is not None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = users_collection.insert_one(user_data)
        return True, "User created successfully"
    except DuplicateKeyError:
        return False, "Username already exists"
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

def verify_password(username, password):
    """Verify password for user"""
    if users_collection is None:
        return False
    try:
        user = users_collection.find_one({'username': username})
        if user is None:
            return False
        return user['password'] == hash_password(password)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def get_user_face_encoding(username):
    """Get face encoding for user"""
    if users_collection is None:
        return None
    try:
        user = users_collection.find_one({'username': username})
        if user is None:
            return None
        return user.get('face_encoding')
    except Exception as e:
        print(f"Error getting face encoding: {e}")
        return None

def update_face_encoding(username, face_encoding):
    """Update face encoding for user"""
    if users_collection is None:
        return False
    
    # Check if this face is already registered by another user
    existing_user = face_exists(face_encoding)
    if existing_user and existing_user != username:
        print(f"Face already registered to {existing_user}")
        return False
    
    try:
        face_hash = hash_face_encoding(face_encoding)
        
        result = users_collection.update_one(
            {'username': username},
            {
                '$set': {
                    'face_encoding': face_encoding,
                    'face_hash': face_hash,
                    'has_face': True,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating face encoding: {e}")
        return False

def update_password(username, new_password):
    """Update password for user"""
    if users_collection is None:
        return False
    
    try:
        result = users_collection.update_one(
            {'username': username},
            {
                '$set': {
                    'password': hash_password(new_password),
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating password: {e}")
        return False

def user_has_face(username):
    """Check if user has face data registered"""
    if users_collection is None:
        return False
    try:
        user = users_collection.find_one({'username': username})
        if user is None:
            return False
        return user.get('has_face', False)
    except Exception as e:
        print(f"Error checking face: {e}")
        return False

def get_all_users():
    """Get all users (for debugging)"""
    if users_collection is None:
        return []
    try:
        return list(users_collection.find({}, {'password': 0, 'face_encoding': 0}))
    except Exception as e:
        print(f"Error getting users: {e}")
        return []

def delete_user(username):
    """Delete a user (for testing)"""
    if users_collection is None:
        return False
    try:
        result = users_collection.delete_one({'username': username})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False
