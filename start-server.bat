@echo off
REM Start EPHI Training System Server

echo ============================================
echo EPHI Training Management System
echo ============================================
echo.
echo Starting server...
echo.
echo Server will be available at:
echo http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ============================================
echo.

cd backend
python app.py

pause
