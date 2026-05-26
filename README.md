# EPHI Training Management System

A comprehensive Flask + SQLite web application for managing health worker training programs across Ethiopian health facilities.

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation & Running Locally

1. **Clone/Navigate to project directory**
   ```bash
   cd EPHI
   ```

2. **Install dependencies**
   ```bash
   pip install flask python-dotenv
   ```

3. **Initialize the database**
   ```bash
   python init-database.py
   ```
   - Choose "yes" to recreate the database with sample data
   - Creates 11 regions, 4 demo users, 10 facilities, 8 training topics

4. **Start the server**
   ```bash
   python backend/app.py
   ```
   - Server runs at http://localhost:5000
   - Open in browser - complete-demo.html loads automatically

5. **Demo Credentials**
   ```
   Admin:     admin@ephi.gov.et / admin123
   Trainer:   trainer@ephi.gov.et / trainer123
   Trainee:   trainee@ephi.gov.et / trainee123
   External:  external@who.int / external123
   ```

---

## 🏢 Production Deployment

### ⚠️ Current Limitations (Development Only)

**SQLite Database Issues:**
- ❌ SQLite cannot handle more than 10-20 concurrent users reliably
- ❌ No proper concurrent write support (file locking)
- ❌ Not suitable for multi-user production environments

### ✅ Production Requirements

**1. Database Migration (PostgreSQL Recommended)**

Replace SQLite with PostgreSQL (handles 100s of concurrent users):

```bash
# Install PostgreSQL
# Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib python3-psycopg2

# Create database and user
sudo -u postgres psql
CREATE DATABASE ephi_training;
CREATE USER ephi_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE ephi_training TO ephi_user;
\q
```

**2. Update backend/app.py (Database Connection)**

Replace:
```python
DATABASE = os.path.join(BASE_DIR, 'database', 'ephi_training.db')
sqlite3.connect(DATABASE)
```

With PostgreSQL connection:
```python
import psycopg2
from psycopg2 import pool

db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20,
    host="your_db_host",
    database="ephi_training",
    user="ephi_user",
    password="secure_password_here"
)
```

**3. Update Schema (PostgreSQL Compatible)**

PostgreSQL uses different syntax. Convert schema.sql:
- `AUTOINCREMENT` → `SERIAL PRIMARY KEY` or `BIGSERIAL`
- `BOOLEAN DEFAULT 1` → `BOOLEAN DEFAULT true`
- Use `uuid-ossp` extension for IDs if needed

**4. Production Web Server**

Replace Flask dev server (insecure) with Gunicorn:

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers (4 concurrent processes)
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app

# For 100+ concurrent users, increase workers:
gunicorn -w 16 -b 0.0.0.0:5000 --worker-class sync backend.app:app
```

**5. Reverse Proxy (Nginx)**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**6. SSL/HTTPS (Let's Encrypt)**

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Auto-renew
sudo systemctl enable certbot.timer
```

**7. Environment Configuration**

Create `.env` file:
```
FLASK_ENV=production
SECRET_KEY=your_random_secret_key_here
DATABASE_URL=postgresql://ephi_user:password@localhost/ephi_training
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

Update backend/app.py to load from .env:
```python
from dotenv import load_dotenv
import os

load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
```

---

## 👥 Concurrent User Capacity

| Database | Workers | Concurrent Users | Use Case |
|----------|---------|-----------------|----------|
| SQLite | 1 | 5-10 | Development only |
| SQLite | 4 | 10-20 | Small testing |
| PostgreSQL | 4 | 50-100 | Small production |
| PostgreSQL | 16 | 200-500 | Medium production |
| PostgreSQL + Load Balancer | 32+ | 1000+ | Large production |

**Current Setup:** SQLite + Flask dev server = ~10 concurrent users max

---

## 🔐 Session Management

### Current Implementation (JWT Tokens)
- **Token Type:** JWT (JSON Web Token)
- **Expiry:** 7 days
- **Storage:** Browser localStorage
- **Issue:** No refresh mechanism, no logout on server side

### Production Improvements Needed

**1. Add Token Refresh Endpoint**
```python
@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    old_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    # Validate old token (can be expired)
    # Issue new token valid for 7 more days
    # Return new token
```

**2. Add Session Timeout**
```python
# Reduce JWT expiry to 1 hour
# Require refresh token every hour
# Store refresh tokens in DB (revocable)
```

**3. Add Logout (Server-Side Token Blacklist)**
```python
# When user clicks logout:
# - Add token to blacklist in database
# - Check blacklist on each request
# - Blacklist expires after 7 days
```

**4. Add Session Activity Tracking**
```python
# Log user login/logout
# Track last activity timestamp
# Auto-logout after 30 minutes of inactivity
```

---

## 📧 Email Authentication

### Current Status: **DEMO MODE** (No Real Emails Sent)

When email/password reset is requested:
- ✅ If SMTP configured: Sends email with verification code (currently **not configured**)
- ❌ If SMTP not configured: Returns token on screen (demo mode)

### To Enable Real Email Sending

**1. Configure Gmail SMTP**

```python
# In backend/app.py
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-specific-password"  # NOT regular password!
```

**2. Get Gmail App Password**
- Go to myaccount.google.com → Security
- Enable 2-Factor Authentication
- Create "App password" for Gmail
- Use that 16-character password above

**3. Test Email**
```bash
python -c "from backend.app import send_email; send_email('test@example.com', 'Test', '<h1>Hello</h1>')"
```

**4. Verification Flow**
- User enters email → 8-character code sent to their email
- User enters code + new password → password reset
- Code expires in 1 hour
- Single-use only

---

## 🗂️ Project Structure

```
EPHI/
├── backend/
│   └── app.py                 # Flask API server (650+ lines)
├── database/
│   ├── schema.sql             # Database schema + sample data
│   └── ephi_training.db       # SQLite database (generated)
├── complete-demo.html         # Full frontend (2300+ lines)
├── init-database.py           # Database initialization script
├── README.md                  # This file
└── .env                       # Environment config (create yourself)
```

---

## 📊 Features Implemented

### ✅ Complete
- User authentication (login, password reset, email verification)
- Role-based access (admin, trainer, trainee, external)
- Training session management (create, edit, register)
- Trainer & topic management
- Funding request workflow (request → approve/reject)
- Analytics dashboards (by region, by topic)
- Region management
- User profile editing
- User management (admin panel)
- Data export (CSV)
- Certificate generation (printable)
- Toast notifications
- Responsive design

### ⏳ In Progress
- Trainee registration forms
- Dual-role support

### 🚀 Recommended Future Additions
- PostgreSQL migration
- Token refresh mechanism
- Session timeout/inactivity logout
- Email notification queue (background jobs)
- File upload (certificates, documents)
- Two-factor authentication (2FA)
- Audit logging
- API rate limiting
- Mobile app (React Native)
- Real-time notifications (WebSockets)

---

## 🛠️ Maintenance Checklist

### Daily
- Monitor server logs: `tail -f /var/log/ephi-training.log`
- Check database backup: `ls -lh database/ephi_training.db`

### Weekly
- Review failed login attempts
- Check disk space: `df -h`
- Verify SSL certificate expiry: `sudo certbot certificates`

### Monthly
- Update Python packages: `pip list --outdated`
- Database cleanup (archive old data)
- Review admin actions log

### Quarterly
- Security audit (dependency vulnerabilities)
- Performance review (query optimization)
- User feedback review

### Annually
- Full system audit
- Disaster recovery drill
- Update documentation

---

## 🆘 Troubleshooting

**Server won't start**
```bash
# Check port 5000 is free
lsof -i :5000
# Kill process using port
kill -9 <PID>
```

**Database locked (SQLite)**
```bash
# Delete the database and reinit (dev only)
rm database/ephi_training.db
python init-database.py
```

**Out of memory**
```bash
# Reduce gunicorn workers
gunicorn -w 2 backend.app:app
```

**Email not sending**
```bash
# Test SMTP credentials
python -c "import smtplib; smtplib.SMTP('smtp.gmail.com', 587).starttls()"
```

---

## 📞 Support

For issues or questions:
1. Check this README
2. Review database schema (database/schema.sql)
3. Check Flask logs: `python backend/app.py`
4. Verify .env configuration
5. Test API endpoints with curl

---

## 📄 License

Internal use only - EPHI Training System

---

**Last Updated:** May 26, 2026
**Version:** 1.0 (Development)
**Status:** Ready for small production deployment with PostgreSQL migration
