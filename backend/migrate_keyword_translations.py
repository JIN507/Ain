"""
Migration: Add translations_json column to keywords table
Phase 2 of the stability fix plan

This migration:
1. Adds translations_json (TEXT) column to keywords table
2. Adds translations_updated_at (TIMESTAMP) column
3. Re-translates all existing keywords and saves to database

Run this on Render shell: python backend/migrate_keyword_translations.py
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, get_db, Keyword, DATABASE_URL
from keyword_expansion import expand_keyword
from sqlalchemy import text

def run_migration():
    print("=" * 60)
    print("Migration: Keyword Translations to Database")
    print("=" * 60)
    
    # Step 1: Add new columns if they don't exist
    print("\n[Step 1] Adding new columns to keywords table...")
    
    with engine.connect() as conn:
        # Check if PostgreSQL or SQLite
        is_postgres = 'postgresql' in DATABASE_URL or 'postgres' in DATABASE_URL
        
        if is_postgres:
            # PostgreSQL syntax
            try:
                conn.execute(text("ALTER TABLE keywords ADD COLUMN IF NOT EXISTS translations_json TEXT"))
                conn.execute(text("ALTER TABLE keywords ADD COLUMN IF NOT EXISTS translations_updated_at TIMESTAMP"))
                conn.commit()
                print("   ✅ Columns added (PostgreSQL)")
            except Exception as e:
                print(f"   ⚠️ Column add error (may already exist): {e}")
        else:
            # SQLite - check if columns exist first
            try:
                result = conn.execute(text("PRAGMA table_info(keywords)"))
                columns = [row[1] for row in result]
                
                if 'translations_json' not in columns:
                    conn.execute(text("ALTER TABLE keywords ADD COLUMN translations_json TEXT"))
                    print("   ✅ Added translations_json column")
                else:
                    print("   ⏭️ translations_json already exists")
                
                if 'translations_updated_at' not in columns:
                    conn.execute(text("ALTER TABLE keywords ADD COLUMN translations_updated_at TIMESTAMP"))
                    print("   ✅ Added translations_updated_at column")
                else:
                    print("   ⏭️ translations_updated_at already exists")
                
                conn.commit()
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    # Step 2: Re-translate all existing keywords
    print("\n[Step 2] Re-translating existing keywords...")
    
    db = get_db()
    try:
        keywords = db.query(Keyword).filter(Keyword.enabled == True).all()
        print(f"   Found {len(keywords)} enabled keywords")
        
        success_count = 0
        fail_count = 0
        
        for i, kw in enumerate(keywords, 1):
            print(f"\n   [{i}/{len(keywords)}] {kw.text_ar}")
            
            # Skip if already has translations
            if kw.translations_json:
                print(f"      ⏭️ Already has translations, skipping")
                success_count += 1
                continue
            
            try:
                # Expand and save to database
                expansion = expand_keyword(kw.text_ar, keyword_obj=kw, db=db)
                
                if expansion['status'] in ['success', 'partial']:
                    success_count += 1
                    print(f"      ✅ Translated to {len(expansion['translations'])} languages")
                else:
                    fail_count += 1
                    print(f"      ❌ Translation failed")
                    
            except Exception as e:
                fail_count += 1
                print(f"      ❌ Error: {str(e)[:50]}")
        
        print(f"\n" + "=" * 60)
        print(f"Migration Complete!")
        print(f"   ✅ Success: {success_count}")
        print(f"   ❌ Failed: {fail_count}")
        print("=" * 60)
        
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
