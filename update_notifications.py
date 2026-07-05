# update_notifications.py
import pysqlite3 as sqlite3

conn = sqlite3.connect('shop_management.db')
cursor = conn.cursor()

# Check existing columns
cursor.execute("PRAGMA table_info(notifications)")
columns = [col[1] for col in cursor.fetchall()]
print("Existing columns:", columns)

# Add missing columns
if 'icon' not in columns:
    cursor.execute("ALTER TABLE notifications ADD COLUMN icon TEXT DEFAULT 'fa-info-circle'")
    print("✅ Added icon column")

if 'color' not in columns:
    cursor.execute("ALTER TABLE notifications ADD COLUMN color TEXT DEFAULT '#2563EB'")
    print("✅ Added color column")

if 'link' not in columns:
    cursor.execute("ALTER TABLE notifications ADD COLUMN link TEXT")
    print("✅ Added link column")

if 'read_at' not in columns:
    cursor.execute("ALTER TABLE notifications ADD COLUMN read_at DATETIME")
    print("✅ Added read_at column")

if 'expires_at' not in columns:
    cursor.execute("ALTER TABLE notifications ADD COLUMN expires_at DATETIME")
    print("✅ Added expires_at column")

conn.commit()
conn.close()
print("✅ Notification table updated successfully!")
print("📋 New columns: icon, color, link, read_at, expires_at")