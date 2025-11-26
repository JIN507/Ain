"""
Add image_url column to articles table
"""
import sqlite3

db_path = 'ain_news.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(articles)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'image_url' not in columns:
        print("Adding image_url column to articles table...")
        cursor.execute("ALTER TABLE articles ADD COLUMN image_url TEXT")
        conn.commit()
        print("✅ image_url column added successfully!")
    else:
        print("✅ image_url column already exists")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
