"""
Migration: Add monitor_jobs table

This script creates the monitor_jobs table for tracking background monitoring jobs.

Run this script once to add the table:
    python migrate_add_monitor_jobs.py
"""
import sqlite3
import os

DB_PATH = "ain_news.db"

def migrate():
    """Add monitor_jobs table"""
    print("=" * 60)
    print("Migration: Add monitor_jobs table")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Check if table already exists
        cur.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='monitor_jobs'
        """)
        if cur.fetchone():
            print("✅ Table 'monitor_jobs' already exists - skipping")
            return True
        
        # Create table
        print("Creating table 'monitor_jobs'...")
        cur.execute("""
            CREATE TABLE monitor_jobs (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'QUEUED',
                progress INTEGER DEFAULT 0,
                progress_message VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                finished_at DATETIME,
                total_fetched INTEGER DEFAULT 0,
                total_matched INTEGER DEFAULT 0,
                total_saved INTEGER DEFAULT 0,
                error_message TEXT,
                meta_json TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Create indexes
        print("Creating indexes...")
        cur.execute("""
            CREATE INDEX ix_monitor_jobs_user_id ON monitor_jobs(user_id)
        """)
        cur.execute("""
            CREATE INDEX ix_monitor_jobs_status ON monitor_jobs(status)
        """)
        cur.execute("""
            CREATE INDEX ix_monitor_jobs_created_at ON monitor_jobs(created_at)
        """)
        
        conn.commit()
        print("✅ Table 'monitor_jobs' created successfully")
        
        # Verify
        cur.execute("SELECT sql FROM sqlite_master WHERE name='monitor_jobs'")
        schema = cur.fetchone()[0]
        print(f"\nSchema:\n{schema}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    print("\n" + "=" * 60)
    if success:
        print("✅ Migration completed successfully")
    else:
        print("❌ Migration failed")
    print("=" * 60)
