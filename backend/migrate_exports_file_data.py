"""
Migration: Add file_data column to exports table for Render compatibility.

This allows storing PDF files in the database instead of filesystem,
which is necessary for Render's ephemeral filesystem.

Run this migration on Render after deployment:
    python migrate_exports_file_data.py
"""
import os
import sys
from sqlalchemy import create_engine, text, LargeBinary
from sqlalchemy.exc import OperationalError

# Database URL from environment or default
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./news_monitor.db')

# Fix for Render PostgreSQL URL format
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def run_migration():
    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if column already exists
        try:
            if 'postgresql' in DATABASE_URL:
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'exports' AND column_name = 'file_data'
                """))
            else:
                # SQLite
                result = conn.execute(text("PRAGMA table_info(exports)"))
                columns = [row[1] for row in result.fetchall()]
                if 'file_data' in columns:
                    print("✅ Column 'file_data' already exists. No migration needed.")
                    return True
                result = None
            
            if result and result.fetchone():
                print("✅ Column 'file_data' already exists. No migration needed.")
                return True
                
        except Exception as e:
            print(f"Warning checking column existence: {e}")
        
        # Add the column
        try:
            if 'postgresql' in DATABASE_URL:
                conn.execute(text("ALTER TABLE exports ADD COLUMN file_data BYTEA"))
            else:
                conn.execute(text("ALTER TABLE exports ADD COLUMN file_data BLOB"))
            conn.commit()
            print("✅ Successfully added 'file_data' column to exports table.")
            return True
        except OperationalError as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print("✅ Column 'file_data' already exists. No migration needed.")
                return True
            print(f"❌ Migration failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
