"""
Migration: Add file_data column to exports table for Render compatibility.

This allows storing PDF files in the database instead of filesystem,
which is necessary for Render's ephemeral filesystem.

This migration is AUTO-RUN on app startup for production readiness.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Database URL from environment or default
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./news_monitor.db')

# Fix for Render PostgreSQL URL format
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def table_exists(conn, table_name, is_postgres):
    """Check if a table exists in the database."""
    try:
        if is_postgres:
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table)"
            ), {"table": table_name})
            return result.scalar()
        else:
            result = conn.execute(text(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
            ))
            return result.fetchone() is not None
    except Exception:
        return False

def column_exists(conn, table_name, column_name, is_postgres):
    """Check if a column exists in a table."""
    try:
        if is_postgres:
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = :table AND column_name = :column
            """), {"table": table_name, "column": column_name})
            return result.fetchone() is not None
        else:
            result = conn.execute(text(f"PRAGMA table_info({table_name})"))
            columns = [row[1] for row in result.fetchall()]
            return column_name in columns
    except Exception:
        return False

def run_migration(silent=False):
    """Run the migration. Returns True on success."""
    def log(msg):
        if not silent:
            print(msg)
    
    log("🔄 Running exports file_data migration...")
    engine = create_engine(DATABASE_URL)
    is_postgres = 'postgresql' in DATABASE_URL
    
    with engine.connect() as conn:
        # Check if exports table exists
        if not table_exists(conn, 'exports', is_postgres):
            log("⚠️  Exports table doesn't exist yet. Will be created by init_db.")
            return True
        
        # Check if column already exists
        if column_exists(conn, 'exports', 'file_data', is_postgres):
            log("✅ Column 'file_data' already exists.")
            return True
        
        # Add the column
        try:
            if is_postgres:
                conn.execute(text("ALTER TABLE exports ADD COLUMN file_data BYTEA"))
            else:
                conn.execute(text("ALTER TABLE exports ADD COLUMN file_data BLOB"))
            conn.commit()
            log("✅ Successfully added 'file_data' column to exports table.")
            return True
        except (OperationalError, ProgrammingError) as e:
            err_str = str(e).lower()
            if 'duplicate column' in err_str or 'already exists' in err_str:
                log("✅ Column 'file_data' already exists.")
                return True
            log(f"❌ Migration failed: {e}")
            return False
        except Exception as e:
            log(f"❌ Migration failed: {e}")
            return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
