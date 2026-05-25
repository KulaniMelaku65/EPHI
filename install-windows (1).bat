@echo off
REM EPHI Training System - Windows Installation Script
REM Run this file to install and start the system

echo ============================================
echo EPHI Training Management System
echo Installation Script for Windows
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/5] Python found!
echo.

REM Install required packages
echo [2/5] Installing required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)
echo.

REM Initialize database
echo [3/5] Setting up database...
cd database
if not exist ephi_training.db (
    sqlite3 ephi_training.db < schema.sql
    echo Database created successfully!
) else (
    echo Database already exists, skipping...
)
cd ..
echo.

REM Start the server
echo [4/5] Starting EPHI Training System...
echo.
echo ============================================
echo Server will start at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo ============================================
echo.
cd backend
python app.py

pause
