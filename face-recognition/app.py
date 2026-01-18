from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import database as db
import face_recognition_module as frm
import base64
import cv2
import numpy as np
from io import BytesIO
import os
import json

app = Flask(__name__)
app.secret_key = 'face_recognition_secret_key_12345'

@app.route('/')
def index():
    """Home page - redirect to login if not authenticated"""
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register new user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        register_face = request.form.get('register_face', 'off') == 'on'
        
        # Validation
        if len(username) < 3:
            return render_template('register.html', error='Username must be at least 3 characters')
        
        if db.user_exists(username):
            return render_template('register.html', error='Username already exists!')
        
        if len(password) < 4:
            return render_template('register.html', error='Password must be at least 4 characters')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match!')
        
        face_encoding = None
        if register_face:
            # Face will be captured via AJAX and must be provided
            face_data = request.form.get('face_encoding')
            if not face_data:
                return render_template('register.html', error='Please capture your face before registering')
            try:
                face_encoding = json.loads(face_data)
            except:
                return render_template('register.html', error='Failed to process face data')
        
        # Save user
        success, message = db.add_user(username, password, face_encoding)
        
        if success:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('register.html', error=message)
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template('login.html', error='Please enter username and password')
        
        if not db.user_exists(username):
            return render_template('login.html', error='Username does not exist!')
        
        if db.verify_password(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid password!')
    
    return render_template('login.html')

@app.route('/login-face', methods=['GET', 'POST'])
def login_face():
    """Face recognition login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        face_data = request.form.get('face_encoding')
        
        if not username:
            return render_template('login_face.html', error='Please enter username')
        
        if not db.user_exists(username):
            return render_template('login_face.html', error='Username does not exist!')
        
        if not db.user_has_face(username):
            return render_template('login_face.html', error='This account does not have face recognition enabled')
        
        if face_data:
            try:
                current_encoding = json.loads(face_data)
                stored_encoding = db.get_user_face_encoding(username)

                if frm.verify_face(stored_encoding, current_encoding):
                    session['username'] = username
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('login_face.html', error='Face does not match!', username=username)
            except Exception:
                return render_template('login_face.html', error='Failed to process face data')
        
        return render_template('login_face.html', username=username)
    
    return render_template('login_face.html')

@app.route('/dashboard')
def dashboard():
    """User dashboard - requires login"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    has_face = db.user_has_face(username)
    
    return render_template('dashboard.html', username=username, has_face=has_face)

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change password"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not db.verify_password(username, current_password):
            return render_template('change_password.html', error='Current password is incorrect!')
        
        if len(new_password) < 4:
            return render_template('change_password.html', error='New password must be at least 4 characters')
        
        if new_password == current_password:
            return render_template('change_password.html', error='New password cannot be same as current password!')
        
        if new_password != confirm_password:
            return render_template('change_password.html', error='Passwords do not match!')
        
        if db.update_password(username, new_password):
            return render_template('change_password.html', success='Password changed successfully!')
        else:
            return render_template('change_password.html', error='Error changing password!')
    
    return render_template('change_password.html')

@app.route('/register-face', methods=['GET', 'POST'])
def register_face():
    """Register face for user"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    
    if request.method == 'POST':
        face_data = request.form.get('face_encoding')
        
        if face_data:
            try:
                face_encoding = json.loads(face_data)

                # Check if face is already registered
                existing_user = db.face_exists(face_encoding)
                if existing_user and existing_user != username:
                    return render_template('register_face.html', error=f'This face is already registered to user: {existing_user}', username=username)

                if db.update_face_encoding(username, face_encoding):
                    return render_template('register_face.html', success='Face registered successfully!', username=username)
                else:
                    return render_template('register_face.html', error='Error registering face!', username=username)
            except Exception as e:
                return render_template('register_face.html', error=f'Failed to process face data: {str(e)}', username=username)
        
        return render_template('register_face.html', username=username)
    
    return render_template('register_face.html', username=username)

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/capture-face', methods=['POST'])
def capture_face():
    """API endpoint to capture face via JavaScript"""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data', 'success': False}), 400
        
        # Decode base64 image
        try:
            image_data = data['image'].split(',')[1]
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            return jsonify({'error': f'Failed to decode image: {str(e)}', 'success': False}), 400
        
        if frame is None:
            return jsonify({'error': 'Failed to decode image', 'success': False}), 400
        
        # Detect face and create encoding
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        # Try multiple cascade classifiers for better detection
        cascades = [
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
            cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml',
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml',
        ]
        
        faces = []
        for cascade_path in cascades:
            face_cascade = cv2.CascadeClassifier(cascade_path)
            # Try different parameters
            for scale in [1.1, 1.05, 1.2]:
                for neighbors in [5, 3, 4]:
                    detected = face_cascade.detectMultiScale(
                        gray, 
                        scaleFactor=scale, 
                        minNeighbors=neighbors, 
                        minSize=(60, 60),
                        flags=cv2.CASCADE_SCALE_IMAGE
                    )
                    if len(detected) > 0:
                        faces = detected
                        break
                if len(faces) > 0:
                    break
            if len(faces) > 0:
                break
        
        if len(faces) == 0:
            return jsonify({
                'error': 'No face detected. Please ensure good lighting and face the camera directly.',
                'success': False
            }), 400
        
        # Get largest face (most likely the main subject)
        faces = sorted(faces, key=lambda x: x[2] * x[3], reverse=True)
        x, y, w, h = faces[0]
        
        # Validate face size (must be reasonably large)
        min_face_size = min(frame.shape[0], frame.shape[1]) * 0.1
        if w < min_face_size or h < min_face_size:
            return jsonify({
                'error': 'Face too small. Please move closer to the camera.',
                'success': False
            }), 400
        
        # Add padding to face region
        padding = int(min(w, h) * 0.2)
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(frame.shape[1] - x, w + 2 * padding)
        h = min(frame.shape[0] - y, h + 2 * padding)
        
        face_roi = frame[y:y+h, x:x+w]
        
        if face_roi.size == 0:
            return jsonify({'error': 'Failed to extract face region', 'success': False}), 400
        
        face_data = cv2.resize(face_roi, (100, 100))
        encoding = face_data.flatten().tolist()

        # Create preview image
        try:
            _, jpg = cv2.imencode('.jpg', face_data)
            preview_b64 = base64.b64encode(jpg.tobytes()).decode('utf-8')
            preview_dataurl = f'data:image/jpeg;base64,{preview_b64}'
        except Exception:
            preview_dataurl = None

        return jsonify({
            'success': True, 
            'encoding': encoding, 
            'preview': preview_dataurl,
            'face_bounds': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
        })
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500



@app.route('/admin')
def admin_panel():
    """Admin panel to view all users and manage accounts"""
    # Require login to view admin panel
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = session['username']

    users = db.get_all_users()
    total_users = len(users)
    users_with_face = len([u for u in users if u.get('has_face')])
    
    # Format users for display
    formatted_users = []
    for user in users:
        formatted_users.append({
            'username': user.get('username'),
            'has_face': user.get('has_face', False),
            'face_id': user.get('face_id', 'N/A'),
            'created_at': str(user.get('created_at', 'N/A'))[:19],
            'updated_at': str(user.get('updated_at', 'N/A'))[:19]
        })
    
    return render_template('admin.html', 
                         users=formatted_users,
                         total_users=total_users,
                         users_with_face=users_with_face,
                         current_user=current_user)

@app.route('/admin/delete/<username>', methods=['GET', 'POST'])
def delete_user(username):
    """Delete a user account"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    # Users may only delete their own account via this panel
    requester = session['username']
    if requester != username:
        return jsonify({'success': False, 'message': 'You do not have permission to delete this user'}), 403

    if request.method == 'POST':
        if db.delete_user(username):
            # If a user deletes their own account, clear their session
            session.clear()
            return jsonify({'success': True, 'message': f'User {username} deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete user'})

    return jsonify({'error': 'Invalid request'}), 400

@app.route('/admin/find-duplicates', methods=['GET'])
def find_duplicates():
    """Find all duplicate faces in database"""
    users = db.get_all_users()
    duplicates = []
    checked = set()
    
    for i, user1 in enumerate(users):
        if not user1.get('face_encoding') or user1['username'] in checked:
            continue
        
        similar = db.find_similar_faces(user1.get('face_encoding'))
        if len(similar) > 1:
            duplicates.append({
                'primary_user': user1['username'],
                'face_id': user1.get('face_id', 'N/A'),
                'similar_users': [s for s in similar if s['username'] != user1['username']],
                'total_matches': len(similar)
            })
            for sim in similar:
                checked.add(sim['username'])
    
    return render_template('duplicates.html', duplicates=duplicates, total_duplicates=len(duplicates))


if __name__ == '__main__':
    print("\n" + "="*60)
    print("FACE RECOGNITION LOGIN SYSTEM - WEB VERSION")
    print("="*60)
    print("\nServer is running at: http://localhost:5000")
    print("Admin Panel: http://localhost:5000/admin")
    print("Open your browser and go to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, host='localhost', port=5000, use_reloader=False)
