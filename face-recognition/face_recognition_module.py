import cv2
import numpy as np
import pickle
import os

# Haarcascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def capture_face_encoding(username, mode='register'):
    """
    Capture face images and create encoding for user
    mode: 'register' for new face, 'login' for verification
    """
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        return None, "Camera not found"
    
    # Set higher resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    face_encodings = []
    frame_count = 0
    required_frames = 5
    
    print(f"\n{'='*50}")
    if mode == 'register':
        print(f"REGISTERING FACE FOR: {username}")
        print("Position your face in the camera and look straight")
    else:
        print(f"VERIFYING FACE FOR: {username}")
        print("Position your face in the camera for verification")
    print(f"{'='*50}")
    print("Press 'q' to quit\n")
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            return None, "Failed to read camera"
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Equalize histogram for better detection
        gray = cv2.equalizeHist(gray)
        
        # Try primary cascade with more sensitive settings
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))
        
        # If no faces found, try alternative cascade
        if len(faces) == 0:
            faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml').detectMultiScale(
                gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))
        
        frame_with_text = frame.copy()
        
        if len(faces) > 0:
            # Get largest face
            faces = sorted(faces, key=lambda x: x[2] * x[3], reverse=True)
            x, y, w, h = faces[0]
            
            cv2.rectangle(frame_with_text, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame_with_text, f"Frames: {frame_count}/{required_frames}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Extract face region with padding and create encoding
            padding = 20
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(frame.shape[1] - x, w + 2 * padding)
            h = min(frame.shape[0] - y, h + 2 * padding)
            
            face_roi = frame[y:y+h, x:x+w]
            face_data = cv2.resize(face_roi, (100, 100))
            encoding = face_data.flatten().tolist()
            face_encodings.append(encoding)
            frame_count += 1
        else:
            cv2.putText(frame_with_text, "No face detected - Move closer or check lighting", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imshow('Face Capture', frame_with_text)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            return None, "Capture cancelled"
        
        if mode == 'register' and frame_count >= required_frames:
            break
        elif mode == 'login' and frame_count >= 3:
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    if len(face_encodings) == 0:
        return None, "No face captured"
    
    # Average the encodings
    average_encoding = np.mean(face_encodings, axis=0).tolist()
    return average_encoding, "Face captured successfully"

def verify_face(stored_encoding, current_encoding):
    """
    Verify if current face matches stored face
    Returns True if match, False otherwise
    """
    if stored_encoding is None or current_encoding is None:
        return False
    
    stored = np.array(stored_encoding)
    current = np.array(current_encoding)
    
    # Calculate Euclidean distance
    distance = np.linalg.norm(stored - current)
    
    # Threshold for face matching (lower is better match)
    threshold = 5000
    
    return distance < threshold

def get_face_encoding_from_camera():
    """Capture face encoding from camera for login verification"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        return None, "Camera not found"
    
    # Set higher resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    face_encodings = []
    frame_count = 0
    
    print("\n" + "="*50)
    print("FACE LOGIN VERIFICATION")
    print("Position your face in the camera")
    print("="*50)
    print("Press 'q' to quit\n")
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            return None, "Failed to read camera"
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Equalize histogram
        gray = cv2.equalizeHist(gray)
        
        # More sensitive face detection
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))
        
        if len(faces) == 0:
            faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml').detectMultiScale(
                gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))
        
        frame_with_text = frame.copy()
        
        if len(faces) > 0:
            # Get largest face
            faces = sorted(faces, key=lambda x: x[2] * x[3], reverse=True)
            x, y, w, h = faces[0]
            
            cv2.rectangle(frame_with_text, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame_with_text, f"Frames: {frame_count}/3", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Extract face region with padding
            padding = 20
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(frame.shape[1] - x, w + 2 * padding)
            h = min(frame.shape[0] - y, h + 2 * padding)
            
            face_roi = frame[y:y+h, x:x+w]
            face_data = cv2.resize(face_roi, (100, 100))
            encoding = face_data.flatten().tolist()
            face_encodings.append(encoding)
            frame_count += 1
        else:
            cv2.putText(frame_with_text, "No face detected - Move closer", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imshow('Face Login', frame_with_text)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            return None, "Verification cancelled"
        
        if frame_count >= 3:
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    if len(face_encodings) == 0:
        return None, "No face captured"
    
    average_encoding = np.mean(face_encodings, axis=0).tolist()
    return average_encoding, "Face captured successfully"
