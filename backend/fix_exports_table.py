"""Quick fix script to create/update exports table"""
import sqlite3
import os

db_path = 'news_monitor.db'

if not os.path.exists(db_path):
    print(f"Database {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"Existing tables: {tables}")

if 'exports' not in tables:
    # Create exports table
    print("Creating exports table...")
    cursor.execute('''
        CREATE TABLE exports (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            filters_json TEXT,
            article_count INTEGER DEFAULT 0,
            filename VARCHAR(255),
            stored_filename VARCHAR(255),
            file_size INTEGER,
            file_data BLOB,
            source_type VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('CREATE INDEX ix_exports_user_id ON exports(user_id)')
    conn.commit()
    print("✅ Exports table created with file_data column")
else:
    # Check if file_data column exists
    cursor.execute("PRAGMA table_info(exports)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Exports columns: {columns}")
    
    if 'file_data' not in columns:
        print("Adding file_data column...")
        cursor.execute("ALTER TABLE exports ADD COLUMN file_data BLOB")
        conn.commit()
        print("✅ file_data column added")
    else:
        print("✅ file_data column already exists")

conn.close()
print("Done!")
