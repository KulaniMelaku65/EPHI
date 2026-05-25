@echo off
REM EPHI Training System - Simple Windows Setup
REM Alternative installation method

echo ============================================
echo EPHI Training System - Simple Setup
echo ============================================
echo.

echo Step 1: Upgrading pip...
python -m pip install --upgrade pip
echo.

echo Step 2: Installing Flask...
python -m pip install Flask==3.0.0
echo.

echo Step 3: Installing Flask-CORS...
python -m pip install Flask-CORS==4.0.0
echo.

echo Step 4: Installing PyJWT...
python -m pip install PyJWT==2.8.0
echo.

echo ============================================
echo Installation Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Press any key to close this window
echo 2. Double-click "start-server.bat" to run the system
echo.

pause
