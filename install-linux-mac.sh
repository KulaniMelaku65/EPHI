#!/bin/bash
# EPHI Training System - Linux/Mac Installation Script
# Run this file to install and start the system

echo "============================================"
echo "EPHI Training Management System"
echo "Installation Script for Linux/Mac"
echo "============================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  Mac: brew install python3"
    exit 1
fi

echo "[1/5] Python found!"
echo ""

# Install required packages
echo "[2/5] Installing required packages..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install packages"
    exit 1
fi
echo ""

# Initialize database
echo "[3/5] Setting up database..."
cd database
if [ ! -f ephi_training.db ]; then
    sqlite3 ephi_training.db < schema.sql
    echo "Database created successfully!"
else
    echo "Database already exists, skipping..."
fi
cd ..
echo ""

# Start the server
echo "[4/5] Starting EPHI Training System..."
echo ""
echo "============================================"
echo "Server will start at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo "============================================"
echo ""
cd backend
python3 app.py
