# PostgreSQL Migration Guide

## Overview
This guide helps you migrate from SQLite (development) to PostgreSQL (production-ready) for the EPHI Training Management System.

**Current Status:**
- Database: SQLite (132 KB)
- Concurrent Users: 5-20 max
- Tables: 11 with sample data
- All changes are saved to disk

**After Migration:**
- Database: PostgreSQL
- Concurrent Users: 100s of users
- Same data structure
- Professional hosting-ready

---

## Step-by-Step Migration

### Part 1: Install PostgreSQL

#### On Linux (Ubuntu/Debian)
```bash
# Update system
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib python3-psycopg2 -y

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql  # Auto-start on reboot
```

#### On Windows
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Run installer (choose default options)
3. Remember the `postgres` superuser password
4. PostgreSQL automatically installs as Windows service

#### On macOS
```bash
brew install postgresql@15
brew services start postgresql@15
```

---

### Part 2: Create Database & User

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql
# (or on Windows/Mac, just: psql -U postgres)

# Run these SQL commands:
CREATE DATABASE ephi_training;
CREATE USER ephi_user WITH PASSWORD 'YourSecurePassword123!';
ALTER ROLE ephi_user CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE ephi_training TO ephi_user;

# Test the connection (still in psql):
\c ephi_training ephi_user
# You should see: ephi_training=> (connected as ephi_user)

\q
# Exit psql
```

---

### Part 3: Load Database Schema

```bash
# Navigate to your EPHI project
cd c:\Users\kmelaku\Desktop\Codes\EPHI

# Load the PostgreSQL schema
psql -U ephi_user -d ephi_training -f database/schema-postgres.sql
```

You should see output like:
```
CREATE TABLE
CREATE TABLE
...
INSERT 0 11
INSERT 0 10
INSERT 0 8
```

### Part 4: Install Python PostgreSQL Driver

```bash
pip install psycopg2-binary
```

---

### Part 5: Update Flask Backend

Create `.env` file in your EPHI root directory:

```
DB_TYPE=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ephi_training
POSTGRES_USER=ephi_user
POSTGRES_PASSWORD=YourSecurePassword123!
FLASK_ENV=production
SECRET_KEY=change-me-to-a-random-string-in-production
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

Now update `backend/app.py` - replace the database connection code at the top:

**FIND THIS SECTION (lines 1-35):**
```python
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
```

**REPLACE WITH:**
```python
"""
EPHI Training Management System - Backend API
Python Flask REST API with PostgreSQL database
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
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

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ephi-training-secret-key-change-in-production')

# Database Configuration
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')

if DB_TYPE == 'postgres':
    app.config['POSTGRES_HOST'] = os.getenv('POSTGRES_HOST', 'localhost')
    app.config['POSTGRES_PORT'] = os.getenv('POSTGRES_PORT', '5432')
    app.config['POSTGRES_DB'] = os.getenv('POSTGRES_DB', 'ephi_training')
    app.config['POSTGRES_USER'] = os.getenv('POSTGRES_USER', 'ephi_user')
    app.config['POSTGRES_PASSWORD'] = os.getenv('POSTGRES_PASSWORD', '')
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'ephi_training.db')
    app.config['DATABASE'] = DATABASE_PATH

app.config['SMTP_SERVER'] = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
app.config['SMTP_PORT'] = int(os.getenv('SMTP_PORT', '587'))
app.config['SMTP_EMAIL'] = os.getenv('SMTP_EMAIL', 'your-email@gmail.com')
app.config['SMTP_PASSWORD'] = os.getenv('SMTP_PASSWORD', 'your-password')

# ============ DATABASE HELPERS ============

def get_db():
    if DB_TYPE == 'postgres':
        try:
            conn = psycopg2.connect(
                host=app.config['POSTGRES_HOST'],
                port=app.config['POSTGRES_PORT'],
                database=app.config['POSTGRES_DB'],
                user=app.config['POSTGRES_USER'],
                password=app.config['POSTGRES_PASSWORD']
            )
            return conn
        except Exception as e:
            print(f"PostgreSQL connection error: {e}")
            return None
    else:
        import sqlite3
        if not os.path.exists(app.config['DATABASE']):
            return None
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        return conn
```

### Part 6: Update Database Queries

The good news: Most of your SQLite queries will work in PostgreSQL with small changes.

**Changes needed in all database queries:**

| SQLite | PostgreSQL |
|--------|-----------|
| `cursor.execute()` | `cursor.execute()` ✅ Same |
| `cursor.fetchone()` | `cursor.fetchone()` ✅ Same |
| `cursor.fetchall()` | `cursor.fetchall()` ✅ Same |
| `conn.commit()` | `conn.commit()` ✅ Same |
| `conn.close()` | `conn.close()` ✅ Same |
| `INSERT ... RETURNING id` | `INSERT ... RETURNING id` ✅ Better in PostgreSQL |

**Only one change needed:** When returning data as JSON, modify this section in your code:

```python
# SQLite version (current):
def dict_from_row(row):
    return dict(row)

# PostgreSQL version:
def dict_from_row(row):
    if isinstance(row, dict):
        return row
    return dict(row)
```

---

### Part 7: Test the Connection

```bash
# Create test-postgres.py in your EPHI folder:
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT'),
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"✓ Connected to PostgreSQL! Found {count} users")
    conn.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")

# Run it:
python test-postgres.py
```

---

### Part 8: Deploy to Production Server

Once PostgreSQL is working locally, deploy using Gunicorn:

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers (for small production)
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app

# For 100+ users, use more workers:
gunicorn -w 16 -b 0.0.0.0:5000 backend.app:app

# Or use a systemd service (Linux):
sudo nano /etc/systemd/system/ephi-training.service
```

**systemd service file example:**
```ini
[Unit]
Description=EPHI Training System
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/var/www/ephi
Environment="PATH=/var/www/ephi/venv/bin"
ExecStart=/var/www/ephi/venv/bin/gunicorn -w 8 -b 0.0.0.0:5000 backend.app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl start ephi-training
sudo systemctl enable ephi-training
```

---

## Backup & Restore

### Backup PostgreSQL Database
```bash
# Create backup
pg_dump -U ephi_user -d ephi_training > backup.sql

# Backup with compression (smaller file)
pg_dump -U ephi_user -d ephi_training | gzip > backup.sql.gz
```

### Restore from Backup
```bash
# From SQL file
psql -U ephi_user -d ephi_training < backup.sql

# From compressed backup
gunzip -c backup.sql.gz | psql -U ephi_user -d ephi_training
```

### Automatic Daily Backups (Linux Cron)
```bash
# Edit crontab
crontab -e

# Add this line (backup at 2 AM daily):
0 2 * * * pg_dump -U ephi_user ephi_training | gzip > /backups/ephi_$(date +\%Y\%m\%d).sql.gz
```

---

## Troubleshooting

### "connection refused" error
```bash
# Check if PostgreSQL is running
psql -U postgres -c "SELECT version();"

# If not running:
sudo systemctl start postgresql  # Linux
brew services start postgresql  # macOS
# Windows: Check Services app -> PostgreSQL
```

### "FATAL: password authentication failed"
- Check your .env file has correct POSTGRES_PASSWORD
- Reset password: `ALTER USER ephi_user WITH PASSWORD 'newpassword';`

### "role does not exist"
```bash
# Verify user exists
sudo -u postgres psql -c "\du"

# Recreate if needed
sudo -u postgres psql -c "CREATE USER ephi_user WITH PASSWORD 'password';"
```

### Slow queries
```bash
# Enable query logging in PostgreSQL
sudo nano /etc/postgresql/*/main/postgresql.conf
# Change: log_min_duration_statement = 1000  # Log queries taking >1s
sudo systemctl restart postgresql

# View slow query log
sudo tail -f /var/log/postgresql/*.log
```

---

## Performance Comparison

| Aspect | SQLite | PostgreSQL |
|--------|--------|-----------|
| Concurrent Users | 5-20 | 100-1000+ |
| Data Size | Unlimited | Unlimited |
| Write Speed | Slower | Faster |
| Query Optimization | Basic | Advanced |
| Backups | Manual | Automated |
| Replication | No | Yes |
| Cost | Free | Free |

---

## Next Steps

1. ✅ Create PostgreSQL database and user
2. ✅ Load schema-postgres.sql
3. ✅ Update Flask backend (app.py)
4. ✅ Create .env configuration file
5. ✅ Test connection locally
6. ✅ Deploy with Gunicorn
7. ✅ Set up automated backups
8. ✅ Monitor performance

Your system is now ready for production!
