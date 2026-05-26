"""
EPHI Training Management System - Backend API
Python Flask REST API with SQLite database
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
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

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'ephi-training-secret-key-change-in-production'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'ephi_training.db')
app.config['DATABASE'] = DATABASE_PATH

app.config['SMTP_SERVER'] = 'smtp.gmail.com'
app.config['SMTP_PORT'] = 587
app.config['SMTP_EMAIL'] = 'your-email@gmail.com'
app.config['SMTP_PASSWORD'] = 'your-password'

# ============ DATABASE HELPERS ============

def get_db():
    if not os.path.exists(app.config['DATABASE']):
        return None
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

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

# ============ AUTHENTICATION ENDPOINTS ============

@app.route('/api/auth/login', methods=['POST'])
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

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if user['password_hash'] != password_hash:
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

    new_hash = hashlib.sha256(new_password.encode()).hexdigest()
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

    password_hash = hashlib.sha256(data['password'].encode()).hexdigest()

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

# ============ MAIN ROUTE ============

@app.route('/')
def index():
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
