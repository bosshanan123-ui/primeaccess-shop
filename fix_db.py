# fix_db.py
import sys
try:
    import sqlite3
except ImportError:
    import pysqlite3 as sqlite3
    sys.modules['sqlite3'] = sqlite3

import os

def fix_database():
    db_path = 'shop_management.db'
    
    if not os.path.exists(db_path):
        print("⚠️ Database not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("⚠️ Users table not found! Creating tables...")
            conn.close()
            return
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'theme_preference' not in columns:
            print("⚠️ Adding theme_preference column...")
            cursor.execute("ALTER TABLE users ADD COLUMN theme_preference TEXT DEFAULT 'auto'")
            conn.commit()
            print("✅ Theme preference column added successfully!")
        else:
            print("✅ Theme preference column already exists!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    fix_database()