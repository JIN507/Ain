"""
Migration: Increase URL column sizes to handle long Arabic URLs
Phase 1 of the stability fix plan

This migration increases:
- sources.url: 500 -> 2000
- articles.url: 500 -> 2000  
- articles.image_url: 1000 -> 2000

Run this on Render shell: python backend/migrate_increase_url_columns.py
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, DATABASE_URL

def run_migration():
    print("=" * 60)
    print("Migration: Increase URL Column Sizes")
    print("=" * 60)
    
    # Only run on PostgreSQL
    if 'postgresql' not in DATABASE_URL and 'postgres' not in DATABASE_URL:
        print("⚠️  This migration is for PostgreSQL only.")
        print(f"   Current DB: {DATABASE_URL[:50]}...")
        print("   Skipping migration.")
        return
    
    print(f"Database: PostgreSQL")
    print()
    
    migrations = [
        ("sources", "url", "VARCHAR(2000)"),
        ("articles", "url", "VARCHAR(2000)"),
        ("articles", "image_url", "VARCHAR(2000)"),
    ]
    
    with engine.connect() as conn:
        for table, column, new_type in migrations:
            sql = f'ALTER TABLE {table} ALTER COLUMN {column} TYPE {new_type};'
            print(f"Running: {sql}")
            try:
                conn.execute(sql)
                conn.commit()
                print(f"  ✅ {table}.{column} -> {new_type}")
            except Exception as e:
                if "already" in str(e).lower():
                    print(f"  ⏭️  Already migrated")
                else:
                    print(f"  ❌ Error: {e}")
    
    print()
    print("=" * 60)
    print("✅ Phase 1 Migration Complete")
    print("=" * 60)

if __name__ == "__main__":
    run_migration()
