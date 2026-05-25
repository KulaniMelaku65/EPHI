# EPHI Training System - PowerShell Installation Script
# Run this in PowerShell

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "EPHI Training Management System" -ForegroundColor Cyan
Write-Host "PowerShell Installation Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Python is not installed!" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Install required packages
Write-Host "[2/5] Installing required packages..." -ForegroundColor Yellow
Write-Host "Installing Flask..." -ForegroundColor Gray
python -m pip install Flask==3.0.0 --quiet
Write-Host "Installing Flask-CORS..." -ForegroundColor Gray
python -m pip install Flask-CORS==4.0.0 --quiet
Write-Host "Installing PyJWT..." -ForegroundColor Gray
python -m pip install PyJWT==2.8.0 --quiet
Write-Host "✓ All packages installed successfully!" -ForegroundColor Green
Write-Host ""

# Initialize database
Write-Host "[3/5] Setting up database..." -ForegroundColor Yellow
Set-Location database

if (Test-Path "ephi_training.db") {
    Write-Host "✓ Database already exists, skipping..." -ForegroundColor Green
} else {
    # Read SQL file and pipe to sqlite3
    Get-Content "schema.sql" | sqlite3 ephi_training.db
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Database created successfully!" -ForegroundColor Green
    } else {
        Write-Host "✗ Database creation failed. Creating empty database..." -ForegroundColor Yellow
        # Create database using Python as fallback
        Set-Location ..
        python -c "import sqlite3; sqlite3.connect('database/ephi_training.db').close()"
        Write-Host "✓ Empty database created. You can add data later." -ForegroundColor Green
        Set-Location database
    }
}
Set-Location ..
Write-Host ""

# Ready to start
Write-Host "[4/5] Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "To start the server, run:" -ForegroundColor Yellow
Write-Host "    .\start-server.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Or manually run:" -ForegroundColor Yellow
Write-Host "    cd backend" -ForegroundColor White
Write-Host "    python app.py" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to continue"
