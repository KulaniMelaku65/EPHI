# Windows Installation Fix Guide

## ❌ Error: "pip is not recognized"

This is a common Windows issue. Here are **3 easy solutions**:

---

## ✅ Solution 1: Use the Simple Installer (Easiest!)

1. **Double-click**: `install-simple.bat`
2. Wait for it to complete
3. Then double-click: `start-server.bat`
4. Open browser to: http://localhost:5000

Done! ✨

---

## ✅ Solution 2: Manual Installation (Copy & Paste)

### Step 1: Open Command Prompt
- Press `Windows Key + R`
- Type: `cmd`
- Press Enter

### Step 2: Navigate to EPHI folder
```cmd
cd C:\path\to\ephi-system
```
(Replace with your actual folder path)

### Step 3: Install packages ONE BY ONE
```cmd
python -m pip install Flask==3.0.0
python -m pip install Flask-CORS==4.0.0
python -m pip install PyJWT==2.8.0
```

### Step 4: Setup database
```cmd
cd database
sqlite3 ephi_training.db < schema.sql
cd ..
```

### Step 5: Start server
```cmd
cd backend
python app.py
```

### Step 6: Open browser
- Visit: http://localhost:5000

---

## ✅ Solution 3: Fix pip Path (Permanent Fix)

### Step A: Find where pip is installed
1. Open Command Prompt
2. Run: `python -m site --user-site`
3. Copy the path shown

### Step B: Add to Windows PATH
1. Press `Windows Key`
2. Search: "Environment Variables"
3. Click "Edit the system environment variables"
4. Click "Environment Variables" button
5. Under "User variables", find "Path"
6. Click "Edit"
7. Click "New"
8. Paste: `C:\Users\YourName\AppData\Local\Programs\Python\Python3X\Scripts`
   (Use your actual Python path)
9. Click OK on all windows
10. Close and reopen Command Prompt
11. Try `install-windows.bat` again

---

## 🎯 Quick Test: Is Python Installed Correctly?

Open Command Prompt and run:
```cmd
python --version
```

✅ **Should show**: Python 3.x.x
❌ **If error**: Python not installed or not in PATH

---

## 🚀 Fastest Way to Get Started

**Skip installation completely!**

1. Just open: `complete-demo.html`
2. Works immediately in browser
3. No setup needed!
4. Perfect for presentations

**Demo Login:**
- admin@ephi.gov.et / admin123

---

## 📝 What Each Script Does

| Script | What It Does |
|--------|--------------|
| `install-windows.bat` | Full auto-install (fixed version) |
| `install-simple.bat` | Install packages one-by-one (NEW!) |
| `start-server.bat` | Just start the server (NEW!) |
| `complete-demo.html` | No installation demo |

---

## 💡 Recommended Approach

**For Presentation:**
→ Use `complete-demo.html` (no installation!)

**For Testing:**
→ Use `install-simple.bat` then `start-server.bat`

**For Production:**
→ Deploy to HahuCloud (see README.md)

---

## 🆘 Still Having Issues?

### Error: "Python is not recognized"
**Fix**: Reinstall Python from python.org
- ✅ Check "Add Python to PATH" during installation
- ✅ Check "Install pip"

### Error: "sqlite3 is not recognized"
**Fix**: SQLite not installed
- Download from: https://www.sqlite.org/download.html
- Or skip database setup and use demo HTML

### Server won't start
**Fix**: Port 5000 in use
- Edit `backend/app.py`, line 469
- Change `port=5000` to `port=8000`
- Visit: http://localhost:8000

---

## ✅ Installation Checklist

After installation:
- [ ] `python --version` shows Python 3.x
- [ ] `python -m pip --version` shows pip version
- [ ] Packages installed (Flask, Flask-CORS, PyJWT)
- [ ] Server starts without errors
- [ ] Can access http://localhost:5000
- [ ] Can login as admin@ephi.gov.et

---

## 📞 Need More Help?

1. Try the **simple installer**: `install-simple.bat`
2. Try the **demo**: `complete-demo.html`
3. Check other error messages in console
4. Review the steps above carefully

---

**Remember**: The demo HTML file works with ZERO installation!
Perfect for showing to EPHI immediately. 🎉
