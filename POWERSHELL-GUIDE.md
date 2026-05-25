# PowerShell Installation Guide for EPHI System

## ✅ SOLUTION: You're Using PowerShell!

PowerShell uses different commands than Command Prompt. I've created **PowerShell-specific scripts** for you!

---

## 🚀 Quick Fix - 3 Simple Steps

### **Step 1: Install Python Packages**

In PowerShell, run:
```powershell
cd C:\Users\kmelaku\Desktop\Codes\EPHI
python -m pip install Flask==3.0.0
python -m pip install Flask-CORS==4.0.0
python -m pip install PyJWT==2.8.0
```

### **Step 2: Create Database**

Run this Python script (works in PowerShell!):
```powershell
python init-database.py
```

### **Step 3: Start Server**

```powershell
cd backend
python app.py
```

Then open browser to: http://localhost:5000

**Done!** ✨

---

## 🎯 Alternative: Use PowerShell Scripts

I created **PowerShell-specific scripts** for you:

### **Full Installation:**
```powershell
.\install-powershell.ps1
```

### **Just Start Server:**
```powershell
.\start-server.ps1
```

---

## 📝 What Went Wrong?

The error you got:
```
The '<' operator is reserved for future use.
```

This happens because:
- ❌ You're in **PowerShell** (PS prompt)
- ❌ PowerShell doesn't support `<` for file redirection
- ✅ Command Prompt (CMD) does support it

### Two Solutions:

**Option A: Use Python script** (recommended!)
```powershell
python init-database.py
```

**Option B: Switch to Command Prompt**
1. Press Windows Key + R
2. Type: `cmd` (not PowerShell)
3. Press Enter
4. Navigate to folder: `cd C:\Users\kmelaku\Desktop\Codes\EPHI\database`
5. Run: `sqlite3 ephi_training.db < schema.sql`

---

## 🎯 Easiest Method - Copy & Paste These Commands

Open **PowerShell** in your EPHI folder and run these **one at a time**:

```powershell
# 1. Install packages
python -m pip install Flask==3.0.0
python -m pip install Flask-CORS==4.0.0
python -m pip install PyJWT==2.8.0

# 2. Create database (using Python script)
python init-database.py

# 3. Start server
cd backend
python app.py
```

That's it! Server will start at http://localhost:5000

---

## 🆘 If Python Script Doesn't Work

### Manual Database Creation (PowerShell):

```powershell
# Navigate to database folder
cd database

# Read SQL and pipe to sqlite3 (PowerShell way)
Get-Content schema.sql | sqlite3 ephi_training.db

# Go back to main folder
cd ..
```

---

## 💡 Pro Tip: Check What You're Using

**PowerShell:** Prompt shows `PS C:\>`
**Command Prompt:** Prompt shows `C:\>`

Use the PowerShell commands above if you see `PS`!

---

## ✅ Complete PowerShell Installation

### One-liner installation:
```powershell
python -m pip install Flask==3.0.0 Flask-CORS==4.0.0 PyJWT==2.8.0; python init-database.py
```

Then start server:
```powershell
cd backend; python app.py
```

---

## 📁 New Files for PowerShell Users

I created these **PowerShell-specific** files for you:

1. ✅ **install-powershell.ps1** - PowerShell installer
2. ✅ **start-server.ps1** - PowerShell server starter
3. ✅ **init-database.py** - Python database creator (works everywhere!)

---

## 🎉 Fastest Solution Right Now

Since you're already in the database folder:

```powershell
# Go back to main folder
cd ..

# Run the Python database script
python init-database.py
```

This Python script creates the database and works in **both** PowerShell and Command Prompt!

---

## 🚀 After Installation

Once database is created:

```powershell
cd backend
python app.py
```

Open browser: http://localhost:5000

Login: admin@ephi.gov.et / admin123

---

## 📞 Still Stuck?

### Quick Demo (No Installation):
Just double-click: `complete-demo.html`
- Works immediately
- No PowerShell needed
- Perfect for showing EPHI!

---

**Remember:** The `init-database.py` script I created works in **any** terminal (PowerShell, CMD, Linux, Mac) - use that! 🎯
