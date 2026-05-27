"""
EPHI Training Management System - Backend API
Python Flask REST API with SQLite/PostgreSQL database
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import sqlite3
import hashlib
import jwt
import datetime
import secrets
import string
from functools import wraps
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import bcrypt
from werkzeug.utils import secure_filename
import uuid
import mimetypes

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# ===== CORS CONFIGURATION (SECURITY FIX #2) =====
# Restrict CORS to your domain instead of allowing all origins
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://localhost:3000').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": CORS_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ===== RATE LIMITING (SECURITY FIX #5) =====
# Prevent brute force attacks on login
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ephi-training-secret-key-change-in-production')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'ephi_training.db')
app.config['DATABASE'] = DATABASE_PATH

# SMTP Configuration (Email)
app.config['SMTP_SERVER'] = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
app.config['SMTP_PORT'] = int(os.getenv('SMTP_PORT', '587'))
app.config['SMTP_EMAIL'] = os.getenv('SMTP_EMAIL', '')
app.config['SMTP_PASSWORD'] = os.getenv('SMTP_PASSWORD', '')

# Upload configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_DOCUMENTS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt'}
ALLOWED_IMAGES = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
os.makedirs(os.path.join(UPLOAD_FOLDER, 'materials'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'images'), exist_ok=True)

# ============ DATABASE HELPERS ============

def get_db():
    if not os.path.exists(app.config['DATABASE']):
        return None
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def migrate_db():
    db = get_db()
    if not db:
        return
    db.executescript('''
        CREATE TABLE IF NOT EXISTS training_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER,
            description TEXT,
            uploaded_by INTEGER NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS training_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            caption TEXT,
            uploaded_by INTEGER NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()

migrate_db()

# ============ AUTH DECORATORS ============

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user = data
        except:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.user['role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# ============ EMAIL HELPER ============

def send_email(to_email, subject, body):
    """Send email; logs success/failure. Returns (success, error_msg)."""
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['SMTP_EMAIL']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT'])
        server.starttls()
        server.login(app.config['SMTP_EMAIL'], app.config['SMTP_PASSWORD'])
        server.send_message(msg)
        server.quit()

        db = get_db()
        db.execute(
            'INSERT INTO email_logs (recipient_email, subject, body, status) VALUES (?, ?, ?, ?)',
            (to_email, subject, body, 'sent')
        )
        db.commit()
        return True, None
    except Exception as e:
        db = get_db()
        if db:
            db.execute(
                'INSERT INTO email_logs (recipient_email, subject, body, status, error_message) VALUES (?, ?, ?, ?, ?)',
                (to_email, subject, body, 'failed', str(e))
            )
            db.commit()
        return False, str(e)

def generate_token(length=8):
    """Generate a random uppercase+digit token."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ===== PASSWORD HASHING (SECURITY FIX #3) =====
# Upgraded from SHA-256 to bcrypt for much better security

def hash_password(password):
    """Hash password using bcrypt (secure)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, password_hash):
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except:
        return False

def hash_password_legacy(password):
    """SHA-256 hashing (LEGACY - only for existing passwords during migration)."""
    return hashlib.sha256(password.encode()).hexdigest()

# ============ AUTHENTICATION ENDPOINTS ============

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")  # Max 5 login attempts per minute per IP
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'Database not available'}), 500

    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Support both bcrypt (new) and SHA-256 (legacy) password hashes
    password_valid = False
    if user['password_hash'].startswith('$2b$'):
        # Bcrypt hash (new, secure)
        password_valid = verify_password(password, user['password_hash'])
    else:
        # SHA-256 hash (legacy, for migration)
        password_hash_legacy = hash_password_legacy(password)
        password_valid = user['password_hash'] == password_hash_legacy

        # Auto-upgrade legacy passwords to bcrypt on successful login
        if password_valid:
            new_hash = hash_password(password)
            db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user['id']))
            db.commit()

    if not password_valid:
        return jsonify({'error': 'Invalid email or password'}), 401

    if not user['is_active']:
        return jsonify({'error': 'Account is deactivated. Contact admin.'}), 403

    token = jwt.encode({
        'id': user['id'],
        'email': user['email'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, app.config['SECRET_KEY'])

    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'full_name': user['full_name'],
            'role': user['role'],
            'is_verified': bool(user['is_verified'])
        }
    })

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Generate a reset token and (attempt to) email it."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

    # Always return success to prevent email enumeration
    if not user:
        return jsonify({'message': 'If that email is registered, a reset code has been sent.'})

    # Invalidate old tokens for this user
    db.execute(
        "UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND token_type = 'reset'",
        (user['id'],)
    )

    token = generate_token(8)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()

    db.execute(
        "INSERT INTO password_reset_tokens (user_id, token, token_type, expires_at) VALUES (?, ?, 'reset', ?)",
        (user['id'], token, expires_at)
    )
    db.commit()

    email_body = f"""
    <h2>EPHI Training System – Password Reset</h2>
    <p>You requested a password reset. Use the code below:</p>
    <h1 style="letter-spacing:4px;color:#1a5f3d;font-size:36px">{token}</h1>
    <p>This code expires in <strong>1 hour</strong>.</p>
    <p>If you did not request this, ignore this email.</p>
    """
    sent, error = send_email(email, 'Password Reset Code – EPHI Training System', email_body)

    response = {'message': 'Reset code generated. Check your email.'}
    # In demo mode (email not configured), return token so user can still reset
    if not sent:
        response['demo_token'] = token
        response['demo_note'] = 'Email sending is not configured. Use this token directly.'

    return jsonify(response)

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Verify reset token and set new password."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    token = data.get('token', '').strip().upper()
    new_password = data.get('new_password', '')

    if not all([email, token, new_password]):
        return jsonify({'error': 'Email, token, and new password are required'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    if not user:
        return jsonify({'error': 'Invalid email or token'}), 400

    record = db.execute('''
        SELECT * FROM password_reset_tokens
        WHERE user_id = ? AND token = ? AND token_type = 'reset'
          AND used = 0 AND datetime(expires_at) > datetime('now')
        ORDER BY created_at DESC LIMIT 1
    ''', (user['id'], token)).fetchone()

    if not record:
        return jsonify({'error': 'Invalid or expired reset code'}), 400

    # Use bcrypt for new password hash (secure)
    new_hash = hash_password(new_password)
    db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user['id']))
    db.execute('UPDATE password_reset_tokens SET used = 1 WHERE id = ?', (record['id'],))
    db.commit()

    return jsonify({'message': 'Password reset successfully. You can now log in.'})

@app.route('/api/auth/send-verification', methods=['POST'])
@token_required
def send_verification():
    """Send (or show) an email verification token for the current user."""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (request.user['id'],)).fetchone()

    if user['is_verified']:
        return jsonify({'message': 'Email is already verified.'})

    # Invalidate old verify tokens
    db.execute(
        "UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND token_type = 'verify'",
        (user['id'],)
    )

    token = generate_token(8)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=24)).isoformat()
    db.execute(
        "INSERT INTO password_reset_tokens (user_id, token, token_type, expires_at) VALUES (?, ?, 'verify', ?)",
        (user['id'], token, expires_at)
    )
    db.commit()

    email_body = f"""
    <h2>EPHI Training System – Verify Your Email</h2>
    <p>Use the verification code below to verify your email address:</p>
    <h1 style="letter-spacing:4px;color:#1a5f3d;font-size:36px">{token}</h1>
    <p>This code expires in <strong>24 hours</strong>.</p>
    """
    sent, _ = send_email(user['email'], 'Email Verification – EPHI Training System', email_body)

    response = {'message': 'Verification code sent.'}
    if not sent:
        response['demo_token'] = token
        response['demo_note'] = 'Email sending is not configured. Use this token to verify.'

    return jsonify(response)

@app.route('/api/auth/verify-email', methods=['POST'])
@token_required
def verify_email():
    """Verify email using the token."""
    data = request.get_json()
    token = data.get('token', '').strip().upper()

    if not token:
        return jsonify({'error': 'Verification token is required'}), 400

    db = get_db()
    record = db.execute('''
        SELECT * FROM password_reset_tokens
        WHERE user_id = ? AND token = ? AND token_type = 'verify'
          AND used = 0 AND datetime(expires_at) > datetime('now')
        ORDER BY created_at DESC LIMIT 1
    ''', (request.user['id'], token)).fetchone()

    if not record:
        return jsonify({'error': 'Invalid or expired verification code'}), 400

    db.execute('UPDATE users SET is_verified = 1 WHERE id = ?', (request.user['id'],))
    db.execute('UPDATE password_reset_tokens SET used = 1 WHERE id = ?', (record['id'],))
    db.commit()

    return jsonify({'message': 'Email verified successfully!'})

# ============ DASHBOARD ENDPOINTS ============

@app.route('/api/dashboard/stats', methods=['GET'])
@token_required
def get_dashboard_stats():
    db = get_db()
    role = request.user['role']

    if role == 'admin':
        stats = {
            'total_trainings': db.execute('SELECT COUNT(*) as c FROM training_sessions').fetchone()['c'],
            'active_trainers': db.execute('SELECT COUNT(*) as c FROM users WHERE role="trainer" AND is_active=1').fetchone()['c'],
            'total_trainees': db.execute('SELECT COUNT(DISTINCT trainee_id) as c FROM training_registrations').fetchone()['c'],
            'completion_rate': 85
        }
    elif role == 'trainer':
        tid = request.user['id']
        stats = {
            'my_trainings': db.execute('SELECT COUNT(*) as c FROM training_sessions WHERE trainer_id=?', (tid,)).fetchone()['c'],
            'total_participants': db.execute(
                'SELECT COUNT(*) as c FROM training_registrations r JOIN training_sessions s ON r.session_id=s.id WHERE s.trainer_id=?', (tid,)
            ).fetchone()['c'],
            'upcoming_sessions': db.execute(
                'SELECT COUNT(*) as c FROM training_sessions WHERE trainer_id=? AND status="scheduled"', (tid,)
            ).fetchone()['c'],
            'rating': 4.8
        }
    elif role == 'trainee':
        uid = request.user['id']
        stats = {
            'completed_trainings': db.execute(
                'SELECT COUNT(*) as c FROM training_registrations WHERE trainee_id=? AND completion_status="completed"', (uid,)
            ).fetchone()['c'],
            'certificates': db.execute(
                'SELECT COUNT(*) as c FROM certificates c JOIN training_registrations r ON c.registration_id=r.id WHERE r.trainee_id=?', (uid,)
            ).fetchone()['c'],
            'upcoming': db.execute(
                'SELECT COUNT(*) as c FROM training_registrations r JOIN training_sessions s ON r.session_id=s.id WHERE r.trainee_id=? AND s.status="scheduled"', (uid,)
            ).fetchone()['c']
        }
    else:  # external
        stats = {
            'total_trainings_2026': db.execute(
                'SELECT COUNT(*) as c FROM training_sessions WHERE strftime("%Y",start_date)="2026"'
            ).fetchone()['c'],
            'healthcare_workers_trained': db.execute(
                'SELECT COUNT(DISTINCT trainee_id) as c FROM training_registrations'
            ).fetchone()['c'],
            'health_facilities': db.execute('SELECT COUNT(*) as c FROM health_facilities').fetchone()['c']
        }

    return jsonify(stats)

# ============ USERS / TRAINERS ENDPOINTS ============

@app.route('/api/trainers', methods=['GET'])
@token_required
def get_trainers():
    db = get_db()
    trainers = db.execute(
        'SELECT id, email, full_name, phone, position, region, is_active FROM users WHERE role="trainer"'
    ).fetchall()
    return jsonify([dict(t) for t in trainers])

@app.route('/api/users', methods=['POST'])
@token_required
@role_required(['admin'])
def create_user():
    data = request.get_json()
    required = ['email', 'password', 'full_name']
    if not all(data.get(k) for k in required):
        return jsonify({'error': 'email, password, and full_name are required'}), 400

    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE email = ?', (data['email'].lower(),)).fetchone()
    if existing:
        return jsonify({'error': 'Email is already registered'}), 400

    # Use bcrypt for new password hashes (secure)
    password_hash = hash_password(data['password'])

    cursor = db.execute(
        '''INSERT INTO users (email, password_hash, full_name, role, phone, position, region, health_facility_id, is_verified)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)''',
        (data['email'].lower(), password_hash, data['full_name'],
         data.get('role', 'trainer'), data.get('phone', ''),
         data.get('position', ''), data.get('region', ''),
         data.get('health_facility_id') or None)
    )
    db.commit()
    new_id = cursor.lastrowid

    # Generate email verification token
    verify_token = generate_token(8)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=24)).isoformat()
    db.execute(
        "INSERT INTO password_reset_tokens (user_id, token, token_type, expires_at) VALUES (?, ?, 'verify', ?)",
        (new_id, verify_token, expires_at)
    )
    db.commit()

    email_body = f"""
    <h2>Welcome to EPHI Training System</h2>
    <p>Your account has been created. Use the code below to verify your email:</p>
    <h1 style="letter-spacing:4px;color:#1a5f3d;font-size:36px">{verify_token}</h1>
    <p>Login with: <strong>{data['email']}</strong></p>
    """
    sent, _ = send_email(data['email'], 'Welcome to EPHI Training System', email_body)

    response = {
        'id': new_id,
        'message': f'{data.get("role","trainer").title()} registered successfully',
        'demo_verify_token': verify_token,
        'demo_note': 'Email not configured. Share this verification token with the new user.'
    }
    if sent:
        response.pop('demo_verify_token', None)
        response.pop('demo_note', None)

    return jsonify(response), 201

@app.route('/api/users/me', methods=['GET'])
@token_required
def get_current_user():
    db = get_db()
    user = db.execute('''
        SELECT id, email, full_name, phone, position, health_facility_id, region,
               years_experience, education_level, profile_image, role, is_verified
        FROM users WHERE id=?
    ''', (request.user['id'],)).fetchone()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(dict(user))

@app.route('/api/users/me', methods=['PUT'])
@token_required
def update_current_user():
    data = request.get_json()
    db = get_db()

    fields = []
    values = []

    if 'full_name' in data:
        fields.append('full_name=?')
        values.append(data['full_name'].strip())
    if 'phone' in data:
        fields.append('phone=?')
        values.append(data['phone'].strip() or None)
    if 'position' in data:
        fields.append('position=?')
        values.append(data['position'].strip() or None)
    if 'region' in data:
        fields.append('region=?')
        values.append(data['region'].strip() or None)
    if 'health_facility_id' in data:
        facility_id = data['health_facility_id']
        fields.append('health_facility_id=?')
        values.append(facility_id if facility_id else None)
    if 'years_experience' in data:
        try:
            yrs = int(data['years_experience'])
            if 0 <= yrs <= 100:
                fields.append('years_experience=?')
                values.append(yrs)
        except (ValueError, TypeError):
            pass
    if 'education_level' in data:
        fields.append('education_level=?')
        values.append(data['education_level'].strip() or None)

    if not fields:
        return jsonify({'error': 'No fields to update'}), 400

    fields.append('updated_at=CURRENT_TIMESTAMP')
    values.append(request.user['id'])

    query = f"UPDATE users SET {', '.join(fields)} WHERE id=?"
    db.execute(query, tuple(values))
    db.commit()

    return jsonify({'message': 'Profile updated successfully'})

@app.route('/api/users', methods=['GET'])
@token_required
@role_required(['admin'])
def get_all_users():
    db = get_db()
    users = db.execute('''
        SELECT id, email, full_name, role, phone, position, region, health_facility_id, is_active, is_verified, created_at
        FROM users ORDER BY created_at DESC
    ''').fetchall()
    return jsonify([dict(u) for u in users])

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@token_required
@role_required(['admin'])
def update_user(user_id):
    data = request.get_json()
    db = get_db()

    user = db.execute('SELECT id FROM users WHERE id=?', (user_id,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    fields = []
    values = []

    if 'role' in data and data['role'] in ['admin', 'trainer', 'trainee', 'external']:
        fields.append('role=?')
        values.append(data['role'])
    if 'is_active' in data:
        fields.append('is_active=?')
        values.append(1 if data['is_active'] else 0)
    if 'health_facility_id' in data:
        facility_id = data['health_facility_id']
        fields.append('health_facility_id=?')
        values.append(facility_id if facility_id else None)

    if not fields:
        return jsonify({'error': 'No fields to update'}), 400

    fields.append('updated_at=CURRENT_TIMESTAMP')
    values.append(user_id)

    query = f"UPDATE users SET {', '.join(fields)} WHERE id=?"
    db.execute(query, tuple(values))
    db.commit()

    return jsonify({'message': 'User updated successfully'})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@token_required
@role_required(['admin'])
def delete_user(user_id):
    if user_id == request.user['id']:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    db = get_db()
    user = db.execute('SELECT id FROM users WHERE id=?', (user_id,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    db.execute('UPDATE users SET is_active=0, updated_at=CURRENT_TIMESTAMP WHERE id=?', (user_id,))
    db.commit()

    return jsonify({'message': 'User deleted successfully'})

# ============ TRAINING TOPICS ENDPOINTS ============

@app.route('/api/topics', methods=['GET'])
@token_required
def get_topics():
    db = get_db()
    topics = db.execute('SELECT * FROM training_topics WHERE is_active=1').fetchall()
    return jsonify([dict(t) for t in topics])

@app.route('/api/topics', methods=['POST'])
@token_required
@role_required(['admin'])
def create_topic():
    data = request.get_json()
    db = get_db()
    cursor = db.execute(
        'INSERT INTO training_topics (title, description, duration_days, category, created_by) VALUES (?,?,?,?,?)',
        (data['title'], data.get('description',''), data['duration_days'], data['category'], request.user['id'])
    )
    db.commit()
    return jsonify({'id': cursor.lastrowid, 'message': 'Topic created successfully'}), 201

# ============ TRAINING SESSIONS ENDPOINTS ============

@app.route('/api/sessions', methods=['GET'])
@token_required
def get_sessions():
    db = get_db()
    role = request.user['role']

    query = '''
        SELECT s.*, t.title as topic_title, u.full_name as trainer_name,
               f.name as facility_name, f.region,
               (SELECT COUNT(*) FROM training_registrations WHERE session_id=s.id) as registered_count
        FROM training_sessions s
        JOIN training_topics t ON s.topic_id=t.id
        JOIN users u ON s.trainer_id=u.id
        JOIN health_facilities f ON s.health_facility_id=f.id
    '''
    if role == 'trainer':
        query += ' WHERE s.trainer_id=?'
        sessions = db.execute(query, (request.user['id'],)).fetchall()
    else:
        sessions = db.execute(query).fetchall()

    return jsonify([dict(s) for s in sessions])

@app.route('/api/sessions', methods=['POST'])
@token_required
@role_required(['admin', 'trainer'])
def create_session():
    data = request.get_json()
    db = get_db()

    cursor = db.execute(
        '''INSERT INTO training_sessions
           (topic_id, trainer_id, health_facility_id, start_date, end_date, max_participants, location_details)
           VALUES (?,?,?,?,?,?,?)''',
        (data['topic_id'], request.user['id'], data['health_facility_id'],
         data['start_date'], data['end_date'], data.get('max_participants', 50),
         data.get('location_details', ''))
    )
    db.commit()

    topic = db.execute('SELECT title FROM training_topics WHERE id=?', (data['topic_id'],)).fetchone()
    facility = db.execute('SELECT name FROM health_facilities WHERE id=?', (data['health_facility_id'],)).fetchone()

    email_body = f"""
    <h2>New Training Session Created</h2>
    <p><strong>Topic:</strong> {topic['title']}</p>
    <p><strong>Location:</strong> {facility['name']}</p>
    <p><strong>Dates:</strong> {data['start_date']} to {data['end_date']}</p>
    """
    for admin in db.execute('SELECT email FROM users WHERE role="admin"').fetchall():
        send_email(admin['email'], 'New Training Session Created', email_body)

    return jsonify({'id': cursor.lastrowid, 'message': 'Session created successfully'}), 201

@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
@token_required
def update_session(session_id):
    data = request.get_json()
    db = get_db()

    session = db.execute('SELECT trainer_id FROM training_sessions WHERE id=?', (session_id,)).fetchone()
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    if request.user['role'] != 'admin' and request.user['id'] != session['trainer_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    if 'start_date' in data and 'end_date' in data:
        if data['start_date'] >= data['end_date']:
            return jsonify({'error': 'Start date must be before end date'}), 400

    fields_to_update = []
    values = []
    if 'topic_id' in data:
        fields_to_update.append('topic_id=?')
        values.append(data['topic_id'])
    if 'start_date' in data:
        fields_to_update.append('start_date=?')
        values.append(data['start_date'])
    if 'end_date' in data:
        fields_to_update.append('end_date=?')
        values.append(data['end_date'])
    if 'location_details' in data:
        fields_to_update.append('location_details=?')
        values.append(data['location_details'])
    if 'max_participants' in data:
        fields_to_update.append('max_participants=?')
        values.append(data['max_participants'])
    if 'health_facility_id' in data:
        fields_to_update.append('health_facility_id=?')
        values.append(data['health_facility_id'])

    if not fields_to_update:
        return jsonify({'error': 'No fields to update'}), 400

    values.append(session_id)
    query = f"UPDATE training_sessions SET {', '.join(fields_to_update)}, updated_at=CURRENT_TIMESTAMP WHERE id=?"
    db.execute(query, tuple(values))
    db.commit()

    return jsonify({'message': 'Session updated successfully'})

# ============ TRAINEE REGISTRATION FORM ENDPOINTS ============

@app.route('/api/registration-forms', methods=['GET'])
@token_required
@role_required(['trainer', 'admin'])
def get_registration_forms():
    db = get_db()
    if request.user['role'] == 'trainer':
        forms = db.execute('''
            SELECT rf.*, t.title as session_title
            FROM registration_forms rf
            JOIN training_sessions ts ON rf.session_id = ts.id
            JOIN training_topics t ON ts.topic_id = t.id
            WHERE rf.trainer_id = ? ORDER BY rf.created_at DESC
        ''', (request.user['id'],)).fetchall()
    else:
        forms = db.execute('''
            SELECT rf.*, t.title as session_title
            FROM registration_forms rf
            JOIN training_sessions ts ON rf.session_id = ts.id
            JOIN training_topics t ON ts.topic_id = t.id
            ORDER BY rf.created_at DESC
        ''').fetchall()
    return jsonify([dict(f) for f in forms])

@app.route('/api/registration-forms', methods=['POST'])
@token_required
@role_required(['trainer'])
def create_registration_form():
    data = request.get_json()
    required = ['session_id', 'form_name']
    if not all(data.get(k) for k in required):
        return jsonify({'error': 'session_id and form_name are required'}), 400

    db = get_db()
    session = db.execute('SELECT id, trainer_id FROM training_sessions WHERE id=?', (data['session_id'],)).fetchone()
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    if session['trainer_id'] != request.user['id']:
        return jsonify({'error': 'Unauthorized'}), 403

    share_link = generate_token(16).lower()
    cursor = db.execute('''
        INSERT INTO registration_forms (trainer_id, session_id, form_name, form_description, share_link)
        VALUES (?, ?, ?, ?, ?)
    ''', (request.user['id'], data['session_id'], data['form_name'].strip(),
          data.get('form_description', '').strip() or None, share_link))
    db.commit()

    return jsonify({
        'id': cursor.lastrowid,
        'share_link': share_link,
        'form_url': f'/form/{share_link}',
        'message': 'Registration form created successfully'
    }), 201

@app.route('/api/registration-forms/<int:form_id>/submissions', methods=['POST'])
def submit_registration_form(form_id):
    data = request.get_json()
    required = ['full_name', 'job_title', 'health_facility', 'region', 'phone', 'email']
    if not all(data.get(k) for k in required):
        return jsonify({'error': 'All fields are required'}), 400

    db = get_db()
    form = db.execute('SELECT id, form_status FROM registration_forms WHERE id=?', (form_id,)).fetchone()
    if not form:
        return jsonify({'error': 'Form not found'}), 404
    if form['form_status'] != 'active':
        return jsonify({'error': 'This form is no longer accepting submissions'}), 400

    cursor = db.execute('''
        INSERT INTO registration_form_submissions (form_id, full_name, job_title, health_facility, region, phone, email)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (form_id, data['full_name'].strip(), data['job_title'].strip(),
          data['health_facility'].strip(), data['region'].strip(),
          data['phone'].strip(), data['email'].strip()))
    db.commit()

    return jsonify({
        'id': cursor.lastrowid,
        'message': 'Registration submitted successfully. Awaiting trainer approval.'
    }), 201

@app.route('/api/registration-forms/<int:form_id>/submissions', methods=['GET'])
@token_required
def get_form_submissions(form_id):
    db = get_db()
    form = db.execute('SELECT trainer_id FROM registration_forms WHERE id=?', (form_id,)).fetchone()
    if not form:
        return jsonify({'error': 'Form not found'}), 404

    if request.user['role'] != 'admin' and request.user['id'] != form['trainer_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    submissions = db.execute('''
        SELECT rfs.*, u.full_name as reviewed_by_name
        FROM registration_form_submissions rfs
        LEFT JOIN users u ON rfs.reviewed_by = u.id
        WHERE rfs.form_id = ? ORDER BY rfs.submitted_at DESC
    ''', (form_id,)).fetchall()

    return jsonify([dict(s) for s in submissions])

@app.route('/api/registration-forms/<int:form_id>/submissions/<int:sub_id>', methods=['PATCH'])
@token_required
@role_required(['trainer', 'admin'])
def review_form_submission(form_id, sub_id):
    data = request.get_json()
    if data.get('approval_status') not in ['approved', 'rejected']:
        return jsonify({'error': 'approval_status must be "approved" or "rejected"'}), 400

    db = get_db()
    form = db.execute(
        'SELECT trainer_id, session_id FROM registration_forms WHERE id=?', (form_id,)
    ).fetchone()
    if not form:
        return jsonify({'error': 'Form not found'}), 404

    if request.user['role'] != 'admin' and request.user['id'] != form['trainer_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    sub = db.execute(
        'SELECT * FROM registration_form_submissions WHERE id=? AND form_id=?',
        (sub_id, form_id)
    ).fetchone()
    if not sub:
        return jsonify({'error': 'Submission not found'}), 404

    db.execute('''
        UPDATE registration_form_submissions
        SET approval_status=?, rejection_reason=?, reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP
        WHERE id=?
    ''', (data['approval_status'], data.get('rejection_reason'), request.user['id'], sub_id))
    db.commit()

    response = {'message': f'Submission {data["approval_status"]} successfully'}

    if data['approval_status'] == 'approved':
        email = sub['email'].strip().lower()

        # Create user account if they don't already exist
        existing = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        if existing:
            user_id = existing['id']
            account_created = False
        else:
            temp_password = generate_token(10)
            password_hash = hash_password(temp_password)
            cursor = db.execute(
                '''INSERT INTO users (email, password_hash, full_name, role, phone, position, region, is_verified)
                   VALUES (?, ?, ?, 'trainee', ?, ?, ?, 1)''',
                (email, password_hash, sub['full_name'], sub['phone'],
                 sub['job_title'], sub['region'])
            )
            db.commit()
            user_id = cursor.lastrowid
            account_created = True

            welcome_body = f"""
            <h2>Welcome to EPHI Training System</h2>
            <p>Dear {sub['full_name']},</p>
            <p>Your training registration has been approved. An account has been created for you.</p>
            <p><strong>Login Email:</strong> {email}</p>
            <p><strong>Temporary Password:</strong> <code style="font-size:18px;letter-spacing:2px">{temp_password}</code></p>
            <p>Please log in and change your password after your first sign-in.</p>
            """
            sent, _ = send_email(email, 'Your EPHI Training Account & Approval', welcome_body)
            response['account_created'] = True
            if not sent:
                response['demo_password'] = temp_password
                response['demo_note'] = 'Email not configured. Share this temporary password with the trainee.'

        # Register for the session (skip if already registered)
        existing_reg = db.execute(
            'SELECT id FROM training_registrations WHERE session_id=? AND trainee_id=?',
            (form['session_id'], user_id)
        ).fetchone()
        if not existing_reg:
            db.execute(
                'INSERT INTO training_registrations (session_id, trainee_id) VALUES (?,?)',
                (form['session_id'], user_id)
            )
            db.commit()
            response['registered_for_session'] = True

    return jsonify(response)

@app.route('/api/registration-forms/<form_link>/public', methods=['GET'])
def get_public_form(form_link):
    db = get_db()
    form = db.execute('''
        SELECT rf.*, t.title as session_title, u.full_name as trainer_name
        FROM registration_forms rf
        JOIN training_sessions ts ON rf.session_id = ts.id
        JOIN training_topics t ON ts.topic_id = t.id
        JOIN users u ON rf.trainer_id = u.id
        WHERE rf.share_link = ? AND rf.form_status = 'active'
    ''', (form_link,)).fetchone()

    if not form:
        return jsonify({'error': 'Form not found or no longer accepting submissions'}), 404

    return jsonify(dict(form))

# ============ REGISTRATION ENDPOINTS ============

@app.route('/api/registrations', methods=['POST'])
@token_required
@role_required(['trainee'])
def register_for_training():
    data = request.get_json()
    db = get_db()

    existing = db.execute(
        'SELECT id FROM training_registrations WHERE session_id=? AND trainee_id=?',
        (data['session_id'], request.user['id'])
    ).fetchone()
    if existing:
        return jsonify({'error': 'Already registered for this session'}), 400

    session = db.execute(
        '''SELECT s.max_participants,
           (SELECT COUNT(*) FROM training_registrations WHERE session_id=s.id) as registered
           FROM training_sessions s WHERE s.id=?''',
        (data['session_id'],)
    ).fetchone()
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    if session['registered'] >= session['max_participants']:
        return jsonify({'error': 'Session is full'}), 400

    cursor = db.execute(
        'INSERT INTO training_registrations (session_id, trainee_id) VALUES (?,?)',
        (data['session_id'], request.user['id'])
    )
    db.commit()

    user = db.execute('SELECT email, full_name FROM users WHERE id=?', (request.user['id'],)).fetchone()
    session_info = db.execute(
        '''SELECT t.title, s.start_date, s.end_date, f.name as facility
           FROM training_sessions s
           JOIN training_topics t ON s.topic_id=t.id
           JOIN health_facilities f ON s.health_facility_id=f.id
           WHERE s.id=?''',
        (data['session_id'],)
    ).fetchone()

    email_body = f"""
    <h2>Training Registration Confirmed</h2>
    <p>Dear {user['full_name']},</p>
    <p>You are registered for: <strong>{session_info['title']}</strong></p>
    <p><strong>Location:</strong> {session_info['facility']}</p>
    <p><strong>Dates:</strong> {session_info['start_date']} to {session_info['end_date']}</p>
    <p>Please arrive 30 minutes early on the first day.</p>
    """
    send_email(user['email'], 'Training Registration Confirmed', email_body)

    return jsonify({'id': cursor.lastrowid, 'message': 'Registration successful'}), 201

@app.route('/api/my-registrations', methods=['GET'])
@token_required
@role_required(['trainee'])
def get_my_registrations():
    db = get_db()
    regs = db.execute('''
        SELECT r.id as registration_id, r.session_id, r.trainee_id,
               r.completion_status, r.certificate_number,
               s.start_date, s.end_date, s.status as session_status,
               t.title as topic_title, f.name as facility_name, f.region,
               u.full_name as trainer_name
        FROM training_registrations r
        JOIN training_sessions s ON r.session_id=s.id
        JOIN training_topics t ON s.topic_id=t.id
        JOIN health_facilities f ON s.health_facility_id=f.id
        JOIN users u ON s.trainer_id=u.id
        WHERE r.trainee_id=?
        ORDER BY s.start_date DESC
    ''', (request.user['id'],)).fetchall()
    return jsonify([dict(r) for r in regs])

# ============ FUNDING REQUEST ENDPOINTS ============

@app.route('/api/funding-requests', methods=['GET'])
@token_required
@role_required(['admin', 'trainer'])
def get_funding_requests():
    db = get_db()
    query = '''
        SELECT f.*, u.full_name as trainer_name, t.title as topic_title
        FROM funding_requests f
        JOIN users u ON f.trainer_id=u.id
        JOIN training_topics t ON f.topic_id=t.id
    '''
    if request.user['role'] == 'trainer':
        query += ' WHERE f.trainer_id=?'
        requests = db.execute(query, (request.user['id'],)).fetchall()
    else:
        requests = db.execute(query).fetchall()
    return jsonify([dict(r) for r in requests])

@app.route('/api/funding-requests', methods=['POST'])
@token_required
@role_required(['trainer'])
def create_funding_request():
    data = request.get_json()
    db = get_db()
    cursor = db.execute(
        '''INSERT INTO funding_requests
           (trainer_id, topic_id, requested_amount, num_participants, duration_days, justification)
           VALUES (?,?,?,?,?,?)''',
        (request.user['id'], data['topic_id'], data['requested_amount'],
         data['num_participants'], data['duration_days'], data['justification'])
    )
    db.commit()
    return jsonify({'id': cursor.lastrowid, 'message': 'Funding request submitted'}), 201

@app.route('/api/funding-requests/<int:req_id>', methods=['PATCH'])
@token_required
@role_required(['admin'])
def update_funding_request(req_id):
    data = request.get_json()
    status = data.get('status')
    notes = data.get('notes', '')

    if status not in ('approved', 'rejected'):
        return jsonify({'error': 'status must be approved or rejected'}), 400

    db = get_db()
    req = db.execute('SELECT * FROM funding_requests WHERE id=?', (req_id,)).fetchone()
    if not req:
        return jsonify({'error': 'Request not found'}), 404

    approved_amount = data.get('approved_amount', req['requested_amount'])
    db.execute(
        '''UPDATE funding_requests
           SET status=?, notes=?, approved_by=?, approved_amount=?, approval_date=CURRENT_TIMESTAMP
           WHERE id=?''',
        (status, notes, request.user['id'], approved_amount, req_id)
    )
    db.commit()

    # Notify trainer
    trainer = db.execute('SELECT email, full_name FROM users WHERE id=?', (req['trainer_id'],)).fetchone()
    topic = db.execute('SELECT title FROM training_topics WHERE id=?', (req['topic_id'],)).fetchone()
    email_body = f"""
    <h2>Funding Request {status.title()}</h2>
    <p>Dear {trainer['full_name']},</p>
    <p>Your funding request for <strong>{topic['title']}</strong> has been <strong>{status}</strong>.</p>
    {'<p><strong>Approved amount:</strong> ' + str(approved_amount) + ' ETB</p>' if status == 'approved' else ''}
    {('<p><strong>Notes:</strong> ' + notes + '</p>') if notes else ''}
    """
    send_email(trainer['email'], f'Funding Request {status.title()}', email_body)

    return jsonify({'message': f'Request {status}'})

# ============ ANALYTICS ENDPOINTS ============

@app.route('/api/analytics/by-region', methods=['GET'])
@token_required
def get_analytics_by_region():
    db = get_db()
    analytics = db.execute('''
        SELECT f.region,
               COUNT(DISTINCT s.id) as trainings,
               COUNT(DISTINCT r.trainee_id) as participants,
               COUNT(DISTINCT s.health_facility_id) as facilities
        FROM training_sessions s
        JOIN health_facilities f ON s.health_facility_id=f.id
        LEFT JOIN training_registrations r ON s.id=r.session_id
        GROUP BY f.region
        ORDER BY trainings DESC
    ''').fetchall()
    return jsonify([dict(row) for row in analytics])

@app.route('/api/analytics/by-topic', methods=['GET'])
@token_required
def get_analytics_by_topic():
    db = get_db()
    analytics = db.execute('''
        SELECT t.title, COUNT(s.id) as sessions, COUNT(r.id) as total_participants
        FROM training_topics t
        LEFT JOIN training_sessions s ON t.id=s.topic_id
        LEFT JOIN training_registrations r ON s.id=r.session_id
        GROUP BY t.id
        ORDER BY sessions DESC
        LIMIT 10
    ''').fetchall()
    return jsonify([dict(row) for row in analytics])

# ============ HEALTH FACILITIES ENDPOINTS ============

@app.route('/api/facilities', methods=['GET'])
@token_required
def get_facilities():
    db = get_db()
    region = request.args.get('region')
    if region:
        facilities = db.execute('SELECT * FROM health_facilities WHERE region=?', (region,)).fetchall()
    else:
        facilities = db.execute('SELECT * FROM health_facilities').fetchall()
    return jsonify([dict(f) for f in facilities])

# ============ REGIONS ENDPOINTS ============

@app.route('/api/regions', methods=['GET'])
@token_required
def get_regions():
    db = get_db()
    regions = db.execute('SELECT * FROM regions WHERE is_active=1 ORDER BY name').fetchall()
    return jsonify([dict(r) for r in regions])

@app.route('/api/regions', methods=['POST'])
@token_required
@role_required(['admin'])
def create_region():
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'error': 'Region name is required'}), 400

    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO regions (name, code, description) VALUES (?, ?, ?)',
            (data['name'].strip(), data.get('code', '').strip() or None, data.get('description', '').strip() or None)
        )
        db.commit()
        return jsonify({'id': cursor.lastrowid, 'message': 'Region created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/regions/<int:region_id>', methods=['DELETE'])
@token_required
@role_required(['admin'])
def delete_region(region_id):
    db = get_db()
    region = db.execute('SELECT id FROM regions WHERE id=?', (region_id,)).fetchone()
    if not region:
        return jsonify({'error': 'Region not found'}), 404

    db.execute('UPDATE regions SET is_active=0, updated_at=CURRENT_TIMESTAMP WHERE id=?', (region_id,))
    db.commit()
    return jsonify({'message': 'Region deleted successfully'})

@app.route('/api/regions/<int:region_id>', methods=['PUT'])
@token_required
@role_required(['admin'])
def update_region(region_id):
    data = request.get_json()
    db = get_db()
    region = db.execute('SELECT id FROM regions WHERE id=?', (region_id,)).fetchone()
    if not region:
        return jsonify({'error': 'Region not found'}), 404

    fields = []
    values = []
    if 'name' in data:
        fields.append('name=?')
        values.append(data['name'].strip())
    if 'code' in data:
        fields.append('code=?')
        values.append(data['code'].strip() or None)
    if 'description' in data:
        fields.append('description=?')
        values.append(data['description'].strip() or None)

    if not fields:
        return jsonify({'error': 'No fields to update'}), 400

    fields.append('updated_at=CURRENT_TIMESTAMP')
    values.append(region_id)
    query = f"UPDATE regions SET {', '.join(fields)} WHERE id=?"
    db.execute(query, tuple(values))
    db.commit()
    return jsonify({'message': 'Region updated successfully'})

# ===== HTTPS & SECURITY HEADERS (SECURITY FIX #4) =====
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses."""
    # HTTPS enforcement (production only)
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # Prevent clickjacking attacks
    response.headers['X-Frame-Options'] = 'DENY'

    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Content Security Policy (CSP) - restrict resource loading
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src fonts.gstatic.com"

    # Prevent referrer leakage
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    return response

# ============ TRAINING MATERIALS ENDPOINTS ============

def _token_from_request():
    token = request.headers.get('Authorization', '') or request.args.get('token', '')
    return token.replace('Bearer ', '')

def _decode_token(token_str):
    return jwt.decode(token_str, app.config['SECRET_KEY'], algorithms=['HS256'])

@app.route('/api/sessions/<int:session_id>/materials', methods=['GET'])
@token_required
def list_materials(session_id):
    db = get_db()
    rows = db.execute('''
        SELECT m.*, u.full_name as uploader_name
        FROM training_materials m JOIN users u ON m.uploaded_by = u.id
        WHERE m.session_id = ? ORDER BY m.uploaded_at DESC
    ''', (session_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/sessions/<int:session_id>/materials', methods=['POST'])
@token_required
@role_required(['admin', 'trainer'])
def upload_material(session_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_DOCUMENTS:
        return jsonify({'error': f'File type not allowed. Allowed: {", ".join(sorted(ALLOWED_DOCUMENTS))}'}), 400
    original_name = secure_filename(file.filename)
    stored_name = f'{uuid.uuid4().hex}.{ext}'
    save_path = os.path.join(UPLOAD_FOLDER, 'materials', stored_name)
    file.save(save_path)
    db = get_db()
    cursor = db.execute(
        'INSERT INTO training_materials (session_id, original_name, stored_name, file_type, file_size, description, uploaded_by) VALUES (?,?,?,?,?,?,?)',
        (session_id, original_name, stored_name, ext, os.path.getsize(save_path),
         request.form.get('description', ''), request.user['id'])
    )
    db.commit()
    return jsonify({'id': cursor.lastrowid, 'message': 'Material uploaded successfully'}), 201

@app.route('/api/materials/<int:mat_id>/download', methods=['GET'])
def download_material(mat_id):
    try:
        data = _decode_token(_token_from_request())
    except Exception:
        return jsonify({'error': 'Authentication required'}), 401
    db = get_db()
    mat = db.execute('SELECT * FROM training_materials WHERE id=?', (mat_id,)).fetchone()
    if not mat:
        return jsonify({'error': 'File not found'}), 404
    file_path = os.path.join(UPLOAD_FOLDER, 'materials', mat['stored_name'])
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found on disk'}), 404
    return send_file(file_path, as_attachment=True, download_name=mat['original_name'])

@app.route('/api/materials/<int:mat_id>', methods=['DELETE'])
@token_required
@role_required(['admin', 'trainer'])
def delete_material(mat_id):
    db = get_db()
    mat = db.execute('SELECT * FROM training_materials WHERE id=?', (mat_id,)).fetchone()
    if not mat:
        return jsonify({'error': 'File not found'}), 404
    if request.user['role'] != 'admin' and mat['uploaded_by'] != request.user['id']:
        return jsonify({'error': 'Unauthorized'}), 403
    file_path = os.path.join(UPLOAD_FOLDER, 'materials', mat['stored_name'])
    if os.path.exists(file_path):
        os.remove(file_path)
    db.execute('DELETE FROM training_materials WHERE id=?', (mat_id,))
    db.commit()
    return jsonify({'message': 'Material deleted'})

# ============ TRAINING IMAGES ENDPOINTS ============

@app.route('/api/sessions/<int:session_id>/images', methods=['GET'])
@token_required
def list_images(session_id):
    db = get_db()
    rows = db.execute('''
        SELECT i.*, u.full_name as uploader_name
        FROM training_images i JOIN users u ON i.uploaded_by = u.id
        WHERE i.session_id = ? ORDER BY i.uploaded_at ASC
    ''', (session_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/sessions/<int:session_id>/images', methods=['POST'])
@token_required
@role_required(['admin', 'trainer'])
def upload_image(session_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_IMAGES:
        return jsonify({'error': f'Image type not allowed. Allowed: {", ".join(sorted(ALLOWED_IMAGES))}'}), 400
    original_name = secure_filename(file.filename)
    stored_name = f'{uuid.uuid4().hex}.{ext}'
    save_path = os.path.join(UPLOAD_FOLDER, 'images', stored_name)
    file.save(save_path)
    db = get_db()
    cursor = db.execute(
        'INSERT INTO training_images (session_id, original_name, stored_name, caption, uploaded_by) VALUES (?,?,?,?,?)',
        (session_id, original_name, stored_name, request.form.get('caption', ''), request.user['id'])
    )
    db.commit()
    return jsonify({'id': cursor.lastrowid, 'message': 'Image uploaded successfully'}), 201

@app.route('/api/images/<int:img_id>/view', methods=['GET'])
def view_image(img_id):
    try:
        _decode_token(_token_from_request())
    except Exception:
        return jsonify({'error': 'Authentication required'}), 401
    db = get_db()
    img = db.execute('SELECT * FROM training_images WHERE id=?', (img_id,)).fetchone()
    if not img:
        return jsonify({'error': 'Image not found'}), 404
    file_path = os.path.join(UPLOAD_FOLDER, 'images', img['stored_name'])
    if not os.path.exists(file_path):
        return jsonify({'error': 'Image not found on disk'}), 404
    mime = mimetypes.guess_type(img['stored_name'])[0] or 'image/jpeg'
    return send_file(file_path, mimetype=mime)

@app.route('/api/images/<int:img_id>', methods=['DELETE'])
@token_required
@role_required(['admin', 'trainer'])
def delete_image(img_id):
    db = get_db()
    img = db.execute('SELECT * FROM training_images WHERE id=?', (img_id,)).fetchone()
    if not img:
        return jsonify({'error': 'Image not found'}), 404
    if request.user['role'] != 'admin' and img['uploaded_by'] != request.user['id']:
        return jsonify({'error': 'Unauthorized'}), 403
    file_path = os.path.join(UPLOAD_FOLDER, 'images', img['stored_name'])
    if os.path.exists(file_path):
        os.remove(file_path)
    db.execute('DELETE FROM training_images WHERE id=?', (img_id,))
    db.commit()
    return jsonify({'message': 'Image deleted'})

# ============ STATIC FILES ============

@app.route('/logo.png')
def serve_logo():
    logo_path = os.path.join(BASE_DIR, 'logo.png')
    if os.path.exists(logo_path):
        return send_file(logo_path, mimetype='image/png')
    return jsonify({'error': 'Logo not found'}), 404

# ============ MAIN ROUTE ============

@app.route('/')
@app.route('/form/<path:form_link>')
def index(form_link=None):
    html_path = os.path.join(BASE_DIR, 'complete-demo.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return '<h1>EPHI API Running — open complete-demo.html</h1>'

if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        print("ERROR: Database not found. Run: python init-database.py")
        import sys
        sys.exit(1)

    print("=" * 60)
    print("EPHI Training Management System")
    print("Server: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
