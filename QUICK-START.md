# EPHI Training System - Quick Start Guide

## 🚀 Two Ways to Use This System

---

## Option 1: Instant Demo (Recommended for Presentations)

**No installation required! Perfect for showing to EPHI leadership.**

### Steps:
1. Find the file: `complete-demo.html`
2. Double-click it
3. It opens in your web browser
4. Start using immediately!

### Demo Login Credentials:
- **Admin**: admin@ephi.gov.et / admin123
- **Trainer**: trainer@ephi.gov.et / trainer123
- **Trainee**: trainee@ephi.gov.et / trainee123
- **External**: external@who.int / external123

---

## Option 2: Full Installation (For Production/Testing)

### For Windows:

1. **Install Python** (if not already installed)
   - Download from: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
   - Click "Install Now"

2. **Run Installation Script**
   - Double-click: `install-windows.bat`
   - Wait for installation to complete
   - Server starts automatically

3. **Access System**
   - Open browser
   - Go to: http://localhost:5000
   - Log in with demo credentials above

### For Linux/Mac:

1. **Open Terminal** in this folder

2. **Run Installation Script**
   ```bash
   chmod +x install-linux-mac.sh
   ./install-linux-mac.sh
   ```

3. **Access System**
   - Open browser
   - Go to: http://localhost:5000
   - Log in with demo credentials above

---

## 📁 File Structure

```
ephi-system/
├── complete-demo.html          ← OPEN THIS for instant demo!
├── requirements.txt            ← Python packages needed
├── install-windows.bat         ← Windows installer
├── install-linux-mac.sh        ← Linux/Mac installer
├── README.md                   ← Full documentation
├── PRESENTATION-GUIDE.md       ← Guide for presenting to EPHI
├── backend/
│   ├── app.py                  ← Main server code
│   └── requirements.txt        ← Same as root requirements.txt
└── database/
    └── schema.sql              ← Database structure
```

---

## ⚡ Manual Installation (If Scripts Don't Work)

### Step 1: Install Python Packages
```bash
pip install Flask==3.0.0
pip install Flask-CORS==4.0.0
pip install PyJWT==2.8.0
```

Or simply:
```bash
pip install -r requirements.txt
```

### Step 2: Set Up Database
```bash
cd database
sqlite3 ephi_training.db < schema.sql
cd ..
```

### Step 3: Run Server
```bash
cd backend
python app.py
```

### Step 4: Open Browser
- Visit: http://localhost:5000

---

## 🔧 Troubleshooting

### "Python is not recognized"
- **Windows**: Reinstall Python and check "Add to PATH"
- **Linux**: Run `sudo apt install python3 python3-pip`
- **Mac**: Run `brew install python3`

### "pip is not recognized"
- **Windows**: Use `python -m pip install -r requirements.txt`
- **Linux/Mac**: Use `pip3` instead of `pip`

### "Port 5000 already in use"
- Edit `backend/app.py`, line 469
- Change `port=5000` to `port=8000`
- Access at: http://localhost:8000

### "No module named 'flask'"
- Run: `pip install -r requirements.txt`
- Or: `pip install Flask Flask-CORS PyJWT`

### Database errors
- Delete `database/ephi_training.db`
- Run installation script again
- Database will be recreated

---

## 📱 Access from Phone/Tablet

### While server is running on your computer:

1. **Find your computer's IP address**
   - Windows: Run `ipconfig` in Command Prompt
   - Mac/Linux: Run `ifconfig` in Terminal
   - Look for something like: 192.168.1.100

2. **On your phone/tablet**
   - Connect to same WiFi as computer
   - Open browser
   - Go to: http://YOUR-IP-ADDRESS:5000
   - Example: http://192.168.1.100:5000

---

## 🌐 Deploy to Internet (HahuCloud)

See `README.md` for full deployment instructions.

Quick summary:
1. Purchase hosting from hahucloud.com (500-1000 ETB/month)
2. Upload all files via FTP
3. Configure domain name
4. Done! Accessible from anywhere

---

## 📧 Email Configuration

To enable email notifications:

1. Edit `backend/app.py`
2. Find lines 20-23
3. Update with your email settings:
   ```python
   app.config['SMTP_EMAIL'] = 'your-email@gmail.com'
   app.config['SMTP_PASSWORD'] = 'your-app-password'
   ```
4. Restart server

---

## 💡 Tips

### For Presentations:
- Use `complete-demo.html` - no setup needed!
- Practice logging in as different roles
- Show the charts and statistics

### For Testing:
- Use the full installation
- Add your own test data
- Try all features

### For Production:
- Follow deployment guide in README.md
- Use HahuCloud hosting
- Configure email notifications
- Set up daily backups

---

## 🆘 Need Help?

1. Check `README.md` for detailed documentation
2. Check `PRESENTATION-GUIDE.md` for demo tips
3. Review troubleshooting section above
4. Check error messages in terminal/command prompt

---

## ✅ Success Checklist

After installation, you should be able to:
- [ ] Open http://localhost:5000 in browser
- [ ] See EPHI login page
- [ ] Log in as admin@ephi.gov.et / admin123
- [ ] View dashboard with statistics
- [ ] Switch between different user roles
- [ ] See charts and graphs

If all checked, installation successful! ✨

---

**Last Updated**: May 2026
**Version**: 1.0
**For**: Ethiopian Public Health Institute (EPHI)
