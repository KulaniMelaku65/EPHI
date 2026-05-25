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
from functools import wraps
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'ephi-training-secret-key-change-in-production'

# Get the absolute path to the database file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'ephi_training.db')
app.config['DATABASE'] = DATABASE_PATH

app.config['SMTP_SERVER'] = 'smtp.gmail.com'
app.config['SMTP_PORT'] = 587
app.config['SMTP_EMAIL'] = 'your-email@gmail.com'  # Configure in production
app.config['SMTP_PASSWORD'] = 'your-password'  # Use environment variable

# Database helper functions
def get_db():
    """Get database connection"""
    # Ensure database file exists
    if not os.path.exists(app.config['DATABASE']):
        print(f"ERROR: Database not found at {app.config['DATABASE']}")
        print("Please run 'python init-database.py' from the main folder")
        return None
    
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with schema"""
    with app.app_context():
        db = get_db()
        if db is None:
            print("Cannot initialize database - database connection failed")
            return
        schema_path = os.path.join(BASE_DIR, 'database', 'schema.sql')
        with open(schema_path, 'r') as f:
            db.executescript(f.read())
        db.commit()
        print("Database initialized successfully!")

# Authentication decorator
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
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

# Role-based access decorator
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.user['role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# Email notification function
def send_email(to_email, subject, body):
    """Send email notification"""
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
        
        # Log email
        db = get_db()
        db.execute(
            'INSERT INTO email_logs (recipient_email, subject, body, status) VALUES (?, ?, ?, ?)',
            (to_email, subject, body, 'sent')
        )
        db.commit()
        
        return True
    except Exception as e:
        # Log failed email
        db = get_db()
        db.execute(
            'INSERT INTO email_logs (recipient_email, subject, body, status, error_message) VALUES (?, ?, ?, ?, ?)',
            (to_email, subject, body, 'failed', str(e))
        )
        db.commit()
        return False

# ============ AUTHENTICATION ENDPOINTS ============

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # In demo, accept any password. In production, verify hash
    # password_hash = hashlib.sha256(password.encode()).hexdigest()
    # if user['password_hash'] != password_hash:
    #     return jsonify({'error': 'Invalid credentials'}), 401
    
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
            'role': user['role']
        }
    })

# ============ DASHBOARD ENDPOINTS ============

@app.route('/api/dashboard/stats', methods=['GET'])
@token_required
def get_dashboard_stats():
    """Get dashboard statistics based on user role"""
    db = get_db()
    role = request.user['role']
    
    if role == 'admin':
        stats = {
            'total_trainings': db.execute('SELECT COUNT(*) as count FROM training_sessions').fetchone()['count'],
            'active_trainers': db.execute('SELECT COUNT(*) as count FROM users WHERE role = "trainer" AND is_active = 1').fetchone()['count'],
            'total_trainees': db.execute('SELECT COUNT(DISTINCT trainee_id) as count FROM training_registrations').fetchone()['count'],
            'completion_rate': 85  # Calculate from actual data
        }
    elif role == 'trainer':
        trainer_id = request.user['id']
        stats = {
            'my_trainings': db.execute('SELECT COUNT(*) as count FROM training_sessions WHERE trainer_id = ?', (trainer_id,)).fetchone()['count'],
            'total_participants': db.execute(
                'SELECT COUNT(*) as count FROM training_registrations r JOIN training_sessions s ON r.session_id = s.id WHERE s.trainer_id = ?',
                (trainer_id,)
            ).fetchone()['count'],
            'upcoming_sessions': db.execute(
                'SELECT COUNT(*) as count FROM training_sessions WHERE trainer_id = ? AND status = "scheduled"',
                (trainer_id,)
            ).fetchone()['count'],
            'rating': 4.8
        }
    elif role == 'trainee':
        trainee_id = request.user['id']
        stats = {
            'completed_trainings': db.execute(
                'SELECT COUNT(*) as count FROM training_registrations WHERE trainee_id = ? AND completion_status = "completed"',
                (trainee_id,)
            ).fetchone()['count'],
            'certificates': db.execute(
                'SELECT COUNT(*) as count FROM certificates c JOIN training_registrations r ON c.registration_id = r.id WHERE r.trainee_id = ?',
                (trainee_id,)
            ).fetchone()['count'],
            'upcoming': db.execute(
                'SELECT COUNT(*) as count FROM training_registrations r JOIN training_sessions s ON r.session_id = s.id WHERE r.trainee_id = ? AND s.status = "scheduled"',
                (trainee_id,)
            ).fetchone()['count']
        }
    else:  # external
        stats = {
            'total_trainings_2026': db.execute('SELECT COUNT(*) as count FROM training_sessions WHERE strftime("%Y", start_date) = "2026"').fetchone()['count'],
            'healthcare_workers_trained': db.execute('SELECT COUNT(DISTINCT trainee_id) as count FROM training_registrations').fetchone()['count'],
            'health_facilities': db.execute('SELECT COUNT(*) as count FROM health_facilities').fetchone()['count']
        }
    
    return jsonify(stats)

# ============ TRAINING TOPICS ENDPOINTS ============

@app.route('/api/topics', methods=['GET'])
@token_required
def get_topics():
    """Get all training topics"""
    db = get_db()
    topics = db.execute('SELECT * FROM training_topics WHERE is_active = 1').fetchall()
    return jsonify([dict(topic) for topic in topics])

@app.route('/api/topics', methods=['POST'])
@token_required
@role_required(['admin'])
def create_topic():
    """Create new training topic (admin only)"""
    data = request.get_json()
    db = get_db()
    
    cursor = db.execute(
        'INSERT INTO training_topics (title, description, duration_days, category, created_by) VALUES (?, ?, ?, ?, ?)',
        (data['title'], data['description'], data['duration_days'], data['category'], request.user['id'])
    )
    db.commit()
    
    return jsonify({'id': cursor.lastrowid, 'message': 'Topic created successfully'}), 201

# ============ TRAINING SESSIONS ENDPOINTS ============

@app.route('/api/sessions', methods=['GET'])
@token_required
def get_sessions():
    """Get training sessions"""
    db = get_db()
    role = request.user['role']
    
    query = '''
        SELECT s.*, t.title as topic_title, u.full_name as trainer_name, f.name as facility_name, f.region,
               (SELECT COUNT(*) FROM training_registrations WHERE session_id = s.id) as registered_count
        FROM training_sessions s
        JOIN training_topics t ON s.topic_id = t.id
        JOIN users u ON s.trainer_id = u.id
        JOIN health_facilities f ON s.health_facility_id = f.id
    '''
    
    if role == 'trainer':
        query += ' WHERE s.trainer_id = ?'
        sessions = db.execute(query, (request.user['id'],)).fetchall()
    else:
        sessions = db.execute(query).fetchall()
    
    return jsonify([dict(session) for session in sessions])

@app.route('/api/sessions', methods=['POST'])
@token_required
@role_required(['admin', 'trainer'])
def create_session():
    """Create new training session"""
    data = request.get_json()
    db = get_db()
    
    cursor = db.execute(
        '''INSERT INTO training_sessions 
        (topic_id, trainer_id, health_facility_id, start_date, end_date, max_participants, location_details)
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (data['topic_id'], request.user['id'], data['health_facility_id'], 
         data['start_date'], data['end_date'], data.get('max_participants', 50),
         data.get('location_details', ''))
    )
    db.commit()
    
    # Send email notification
    topic = db.execute('SELECT title FROM training_topics WHERE id = ?', (data['topic_id'],)).fetchone()
    facility = db.execute('SELECT name FROM health_facilities WHERE id = ?', (data['health_facility_id'],)).fetchone()
    
    email_body = f"""
    <h2>New Training Session Created</h2>
    <p><strong>Topic:</strong> {topic['title']}</p>
    <p><strong>Location:</strong> {facility['name']}</p>
    <p><strong>Dates:</strong> {data['start_date']} to {data['end_date']}</p>
    <p>Please log in to the EPHI Training System to view details.</p>
    """
    
    # Notify admins
    admins = db.execute('SELECT email FROM users WHERE role = "admin"').fetchall()
    for admin in admins:
        send_email(admin['email'], 'New Training Session Created', email_body)
    
    return jsonify({'id': cursor.lastrowid, 'message': 'Session created successfully'}), 201

# ============ REGISTRATION ENDPOINTS ============

@app.route('/api/registrations', methods=['POST'])
@token_required
@role_required(['trainee'])
def register_for_training():
    """Register trainee for training session"""
    data = request.get_json()
    db = get_db()
    
    # Check if already registered
    existing = db.execute(
        'SELECT * FROM training_registrations WHERE session_id = ? AND trainee_id = ?',
        (data['session_id'], request.user['id'])
    ).fetchone()
    
    if existing:
        return jsonify({'error': 'Already registered for this session'}), 400
    
    # Check capacity
    session = db.execute(
        '''SELECT s.max_participants, 
           (SELECT COUNT(*) FROM training_registrations WHERE session_id = s.id) as registered
           FROM training_sessions s WHERE s.id = ?''',
        (data['session_id'],)
    ).fetchone()
    
    if session['registered'] >= session['max_participants']:
        return jsonify({'error': 'Session is full'}), 400
    
    cursor = db.execute(
        'INSERT INTO training_registrations (session_id, trainee_id) VALUES (?, ?)',
        (data['session_id'], request.user['id'])
    )
    db.commit()
    
    # Send confirmation email
    user = db.execute('SELECT email, full_name FROM users WHERE id = ?', (request.user['id'],)).fetchone()
    session_info = db.execute(
        '''SELECT t.title, s.start_date, s.end_date, f.name as facility 
           FROM training_sessions s
           JOIN training_topics t ON s.topic_id = t.id
           JOIN health_facilities f ON s.health_facility_id = f.id
           WHERE s.id = ?''',
        (data['session_id'],)
    ).fetchone()
    
    email_body = f"""
    <h2>Training Registration Confirmed</h2>
    <p>Dear {user['full_name']},</p>
    <p>Your registration has been confirmed for:</p>
    <p><strong>{session_info['title']}</strong></p>
    <p><strong>Location:</strong> {session_info['facility']}</p>
    <p><strong>Dates:</strong> {session_info['start_date']} to {session_info['end_date']}</p>
    <p>Please arrive 30 minutes early on the first day.</p>
    <p>EPHI Training System</p>
    """
    
    send_email(user['email'], 'Training Registration Confirmed', email_body)
    
    return jsonify({'id': cursor.lastrowid, 'message': 'Registration successful'}), 201

# ============ FUNDING REQUEST ENDPOINTS ============

@app.route('/api/funding-requests', methods=['GET'])
@token_required
@role_required(['admin', 'trainer'])
def get_funding_requests():
    """Get funding requests"""
    db = get_db()
    
    query = '''
        SELECT f.*, u.full_name as trainer_name, t.title as topic_title
        FROM funding_requests f
        JOIN users u ON f.trainer_id = u.id
        JOIN training_topics t ON f.topic_id = t.id
    '''
    
    if request.user['role'] == 'trainer':
        query += ' WHERE f.trainer_id = ?'
        requests = db.execute(query, (request.user['id'],)).fetchall()
    else:
        requests = db.execute(query).fetchall()
    
    return jsonify([dict(req) for req in requests])

@app.route('/api/funding-requests', methods=['POST'])
@token_required
@role_required(['trainer'])
def create_funding_request():
    """Create funding request"""
    data = request.get_json()
    db = get_db()
    
    cursor = db.execute(
        '''INSERT INTO funding_requests 
        (trainer_id, topic_id, requested_amount, num_participants, duration_days, justification)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (request.user['id'], data['topic_id'], data['requested_amount'],
         data['num_participants'], data['duration_days'], data['justification'])
    )
    db.commit()
    
    return jsonify({'id': cursor.lastrowid, 'message': 'Funding request submitted'}), 201

# ============ ANALYTICS ENDPOINTS ============

@app.route('/api/analytics/by-region', methods=['GET'])
@token_required
def get_analytics_by_region():
    """Get training analytics by region"""
    db = get_db()
    
    analytics = db.execute('''
        SELECT f.region, 
               COUNT(DISTINCT s.id) as trainings,
               COUNT(DISTINCT r.trainee_id) as participants,
               COUNT(DISTINCT s.health_facility_id) as facilities
        FROM training_sessions s
        JOIN health_facilities f ON s.health_facility_id = f.id
        LEFT JOIN training_registrations r ON s.id = r.session_id
        GROUP BY f.region
        ORDER BY trainings DESC
    ''').fetchall()
    
    return jsonify([dict(row) for row in analytics])

@app.route('/api/analytics/by-topic', methods=['GET'])
@token_required
def get_analytics_by_topic():
    """Get training analytics by topic"""
    db = get_db()
    
    analytics = db.execute('''
        SELECT t.title, COUNT(s.id) as sessions, COUNT(r.id) as total_participants
        FROM training_topics t
        LEFT JOIN training_sessions s ON t.id = s.topic_id
        LEFT JOIN training_registrations r ON s.id = r.session_id
        GROUP BY t.id
        ORDER BY sessions DESC
        LIMIT 10
    ''').fetchall()
    
    return jsonify([dict(row) for row in analytics])

# ============ HEALTH FACILITIES ENDPOINTS ============

@app.route('/api/facilities', methods=['GET'])
@token_required
def get_facilities():
    """Get all health facilities"""
    db = get_db()
    region = request.args.get('region')
    
    if region:
        facilities = db.execute('SELECT * FROM health_facilities WHERE region = ?', (region,)).fetchall()
    else:
        facilities = db.execute('SELECT * FROM health_facilities').fetchall()
    
    return jsonify([dict(f) for f in facilities])

# ============ MAIN ROUTE ============

@app.route('/')
def index():
    """Serve the main application"""
    # Serve the complete demo HTML
    html_path = os.path.join(BASE_DIR, 'complete-demo.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """
        <html>
        <head><title>EPHI Training System</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h1>EPHI Training Management System</h1>
            <h2>API Server is Running!</h2>
            <p>The backend API is working correctly.</p>
            <p>To use the full application, please open <strong>complete-demo.html</strong> from the main folder.</p>
            <hr>
            <p><strong>Available API Endpoints:</strong></p>
            <ul style="text-align: left; max-width: 500px; margin: 20px auto;">
                <li>POST /api/auth/login - User login</li>
                <li>GET /api/dashboard/stats - Dashboard statistics</li>
                <li>GET /api/topics - Training topics</li>
                <li>GET /api/sessions - Training sessions</li>
                <li>GET /api/facilities - Health facilities</li>
            </ul>
            <p style="margin-top: 40px; color: #666;">Server running at http://localhost:5000</p>
        </body>
        </html>
        """

if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists(app.config['DATABASE']):
        print("=" * 60)
        print("ERROR: Database not found!")
        print("=" * 60)
        print(f"Looking for: {app.config['DATABASE']}")
        print()
        print("Please run this command from the main folder:")
        print("    python init-database.py")
        print("=" * 60)
        import sys
        sys.exit(1)
    
    # Run development server
    print("=" * 60)
    print("EPHI Training Management System - Server Starting")
    print("=" * 60)
    print(f"Database: {app.config['DATABASE']}")
    print("Server: http://localhost:5000")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
