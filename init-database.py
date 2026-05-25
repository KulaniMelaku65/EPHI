#!/usr/bin/env python3
"""
EPHI Training System - Database Initializer
This script creates and initializes the SQLite database
Works on Windows, Linux, and Mac!
"""

import sqlite3
import os
import sys

def init_database():
    print("=" * 50)
    print("EPHI Training System - Database Setup")
    print("=" * 50)
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('database'):
        print("ERROR: 'database' folder not found!")
        print("Please run this script from the ephi-system root folder")
        print()
        input("Press Enter to exit...")
        sys.exit(1)
    
    db_path = os.path.join('database', 'ephi_training.db')
    schema_path = os.path.join('database', 'schema.sql')
    
    # Check if schema file exists
    if not os.path.exists(schema_path):
        print("ERROR: schema.sql not found in database folder!")
        print()
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Check if database already exists
    if os.path.exists(db_path):
        print("⚠ Database already exists!")
        response = input("Do you want to recreate it? (yes/no): ").lower()
        if response not in ['yes', 'y']:
            print("Keeping existing database.")
            print()
            input("Press Enter to exit...")
            return
        else:
            print("Removing old database...")
            os.remove(db_path)
    
    print()
    print("Creating new database...")
    
    try:
        # Connect to database (creates it if doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Read and execute schema
        print("Reading schema.sql...")
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        print("Creating tables...")
        cursor.executescript(schema)
        
        conn.commit()
        print()
        print("✓ Database created successfully!")
        print()
        print("Database location:", os.path.abspath(db_path))
        
        # Show some stats
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM health_facilities")
        facility_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM training_topics")
        topic_count = cursor.fetchone()[0]
        
        print()
        print("Sample data loaded:")
        print(f"  - {user_count} demo users")
        print(f"  - {facility_count} health facilities")
        print(f"  - {topic_count} training topics")
        print()
        print("=" * 50)
        print("✓ Setup complete!")
        print("=" * 50)
        print()
        print("Next step: Start the server")
        print("  Windows: start-server.bat or start-server.ps1")
        print("  Linux/Mac: ./start-server.sh")
        print()
        
        conn.close()
        
    except Exception as e:
        print()
        print("✗ ERROR creating database:")
        print(str(e))
        print()
        
    input("Press Enter to exit...")

if __name__ == '__main__':
    init_database()
