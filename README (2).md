# EPHI Training Management System
## Complete Setup & Deployment Guide

---

## 📦 **Package Contents**

```
ephi-training-system/
├── backend/
│   ├── app.py                 # Flask REST API
│   ├── requirements.txt       # Python dependencies
├── database/
│   ├── schema.sql             # Database schema
├── complete-demo.html         # Standalone demo (works offline!)
└── README.md                  # This file
```

---

## 🚀 **Quick Demo (No Installation Required!)**

**Option 1: Double-click `complete-demo.html`**
- Opens in your browser immediately
- All demo data built-in
- Perfect for presentations!

**Demo Login Credentials:**
- **Admin**: admin@ephi.gov.et / admin123
- **Trainer**: trainer@ephi.gov.et / trainer123
- **Trainee**: trainee@ephi.gov.et / trainee123
- **External**: external@who.int / external123

---

## 💻 **Full System Setup (For Production)**

### **Step 1: Install Python**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# Check installation
python3 --version
```

### **Step 2: Install Dependencies**

```bash
cd ephi-training-system/backend
pip3 install -r requirements.txt
```

### **Step 3: Initialize Database**

```bash
cd ../database
sqlite3 ephi_training.db < schema.sql
```

### **Step 4: Run the Server**

```bash
cd ../backend
python3 app.py
```

Server will start at: `http://localhost:5000`

---

## 🌐 **Hosting Options for Ethiopia**

### **Recommended: HahuCloud (accepts ETB)**

**Cost**: ~500-1000 ETB/month
**Website**: www.hahucloud.com
**Payment**: Telebirr, CBE, BoA

**Steps**:
1. Visit hahucloud.com
2. Choose "VPS Hosting" plan
3. Select Ubuntu 22.04 OS
4. Pay via Telebirr or bank transfer
5. Receive server credentials
6. Upload your files via FTP/SFTP

### **Alternative: Yegara Host**

**Cost**: Similar pricing
**Website**: www.yegarahost.com
**Payment**: Ethiopian banks, Telebirr

### **Alternative: Ethio Telecom**

**Cost**: Official government rates
**Website**: ethiotelecom.et
**Payment**: Direct birr payment

---

## 📊 **Database Information**

**Type**: SQLite (file-based, no separate server needed)
**Size**: ~2-5MB for typical usage
**Bandwidth**: Very efficient, ~100-200KB per page load

**Tables**:
- `users` - All system users
- `training_topics` - Training courses
- `training_sessions` - Scheduled trainings
- `training_registrations` - Trainee enrollments
- `health_facilities` - Health centers/hospitals
- `funding_requests` - Budget requests
- `certificates` - Issued certificates
- `email_logs` - Notification tracking

---

## 📧 **Email Configuration**

Edit `backend/app.py` lines 20-23:

```python
app.config['SMTP_SERVER'] = 'smtp.gmail.com'
app.config['SMTP_PORT'] = 587
app.config['SMTP_EMAIL'] = 'ephi.training@gmail.com'  # Your email
app.config['SMTP_PASSWORD'] = 'your-app-password'     # Gmail app password
```

**How to get Gmail App Password**:
1. Go to Google Account settings
2. Security → 2-Step Verification
3. App passwords → Generate
4. Use generated password

---

## 🎨 **EPHI Color Scheme**

The system uses official EPHI colors:
- **Primary Blue**: #0f47af (Ethiopian flag blue)
- **Gold/Yellow**: #fcdd09 (Ethiopian flag yellow)
- **Accent Green**: #2d8659 (Health/growth)

---

## 🔐 **Security Checklist**

Before going live:

- [ ] Change SECRET_KEY in app.py
- [ ] Enable password hashing (uncomment lines in login function)
- [ ] Set up HTTPS/SSL certificate
- [ ] Configure firewall rules
- [ ] Enable regular database backups
- [ ] Set up email notifications
- [ ] Create admin account with strong password

---

## 📱 **Mobile Access**

**No app installation needed!**

Users can:
1. Open the website in any mobile browser
2. Tap browser menu → "Add to Home Screen"
3. Icon appears on phone like a native app
4. Works offline with cached data

---

## 🔄 **Backup Strategy**

### **Automatic Daily Backup**

Create a backup script (`backup.sh`):

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
cp database/ephi_training.db backups/ephi_training_$DATE.db
# Keep only last 30 days
find backups/ -name "*.db" -mtime +30 -delete
```

Run daily via cron:
```bash
0 2 * * * /path/to/backup.sh
```

---

## 📈 **Features Implemented**

### **Admin Dashboard**
✅ View all training statistics
✅ Add training topics
✅ Register new trainers
✅ Approve funding requests
✅ View regional analytics
✅ Export reports (Excel/PDF/CSV)

### **Trainer Dashboard**
✅ Create training sessions
✅ Select location and dates
✅ View participant list
✅ Submit funding requests
✅ Track session history

### **Trainee Dashboard**
✅ Browse available trainings
✅ Register for sessions
✅ View certificates
✅ Track completion progress

### **External User Dashboard**
✅ View public training statistics
✅ Filter by region/topic/date
✅ Export public reports
✅ View training directory

### **Charts & Analytics**
✅ Training completion rates
✅ Regional distribution
✅ Topic popularity
✅ Trainer performance
✅ Monthly trends

---

## 🆘 **Troubleshooting**

### **Can't connect to database**
```bash
# Check if database file exists
ls -la database/ephi_training.db

# Reinitialize if needed
cd database
rm ephi_training.db
sqlite3 ephi_training.db < schema.sql
```

### **Port 5000 already in use**
Edit `app.py` line 469:
```python
app.run(debug=True, host='0.0.0.0', port=8000)  # Change port
```

### **Email not sending**
- Check SMTP credentials
- Enable "Less secure app access" in Gmail
- Use app-specific password
- Check firewall allows port 587

---

## 📞 **Support & Contact**

For EPHI-specific questions:
- Email: info@ephi.gov.et
- Phone: +251 112 75-15-22

For technical support:
- Check logs in `backend/logs/`
- Review database with `sqlite3 database/ephi_training.db`

---

## 🎯 **Next Steps for Full Production**

1. **Set up domain name** (e.g., training.ephi.gov.et)
2. **Configure SSL certificate** (Let's Encrypt - free)
3. **Set up automated backups**
4. **Configure email templates**
5. **Add PDF certificate generation**
6. **Integrate with DHIS2** (if needed)
7. **Set up monitoring** (uptime alerts)
8. **Train administrators**

---

## 💰 **Estimated Monthly Costs**

**Hosting**: 500-1,000 ETB
**Domain**: 200-500 ETB (first year)
**SSL Certificate**: FREE (Let's Encrypt)
**Email**: FREE (Gmail/Outlook)
**Bandwidth**: INCLUDED in hosting
**Database**: FREE (SQLite)

**Total**: ~700-1,500 ETB/month

---

## 📊 **Expected Performance**

**Page Load**: <2 seconds
**Concurrent Users**: 50-100 (on basic VPS)
**Database Size**: ~10MB per 1,000 trainings
**Bandwidth**: ~500MB/month for 500 active users

---

## ✅ **Testing Checklist**

Before launching:

- [ ] Admin can create topics
- [ ] Trainers can create sessions
- [ ] Trainees can register
- [ ] Email notifications work
- [ ] Reports export correctly
- [ ] Charts display properly
- [ ] Mobile view works
- [ ] All roles have correct permissions
- [ ] Backup system running
- [ ] SSL certificate installed

---

## 🎓 **Training Materials**

Provide these to EPHI staff:

1. **Admin Guide**: How to manage system
2. **Trainer Guide**: How to create sessions
3. **Trainee Guide**: How to register
4. **Technical Guide**: Server maintenance

---

**System developed for Ethiopian Public Health Institute (EPHI)**
**Version 1.0 - May 2026**
