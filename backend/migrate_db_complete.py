"""
Complete Database Migration Script
Handles all migrations from v1 to latest version
Idempotent - safe to run multiple times
"""
import sqlite3

def migrate_complete():
    """Run all migrations in order"""
    conn = sqlite3.connect('ain_news.db')
    cursor = conn.cursor()
    
    print("🔄 Running complete database migration...")
    print("=" * 60)
    
    try:
        # ========== MIGRATION 1: Add translation columns to keywords ==========
        print("\n📝 Migration 1: Adding keyword translation columns...")
        
        keyword_columns = [
            ('text_en', 'VARCHAR(200)'),
            ('text_fr', 'VARCHAR(200)'),
            ('text_tr', 'VARCHAR(200)'),
            ('text_ur', 'VARCHAR(200)'),
            ('text_zh', 'VARCHAR(200)'),
            ('text_ru', 'VARCHAR(200)'),
            ('text_es', 'VARCHAR(200)')
        ]
        
        for col_name, col_type in keyword_columns:
            try:
                cursor.execute(f"ALTER TABLE keywords ADD COLUMN {col_name} {col_type}")
                print(f"   ✅ Added keywords.{col_name}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e):
                    print(f"   ⏭️ keywords.{col_name} already exists")
                else:
                    raise
        
        # ========== MIGRATION 2: Add new columns to articles ==========
        print("\n📝 Migration 2: Adding article schema columns...")
        
        article_columns = [
            ('original_language', 'VARCHAR(10)'),
            ('arabic_text', 'TEXT'),
            ('keyword_original', 'VARCHAR(200)'),
            ('keywords_translations', 'TEXT'),
            ('sentiment_label', 'VARCHAR(50)'),
            ('sentiment_score', 'VARCHAR(20)'),
            ('fetched_at', 'DATETIME'),
        ]
        
        for col_name, col_type in article_columns:
            try:
                cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
                print(f"   ✅ Added articles.{col_name}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e):
                    print(f"   ⏭️ articles.{col_name} already exists")
                else:
                    raise
        
        # ========== MIGRATION 3: Migrate existing data ==========
        print("\n📝 Migration 3: Migrating existing data to new columns...")
        
        try:
            # Copy old column data to new columns
            cursor.execute("UPDATE articles SET original_language = language WHERE language IS NOT NULL AND original_language IS NULL")
            cursor.execute("UPDATE articles SET keyword_original = keyword WHERE keyword IS NOT NULL AND keyword_original IS NULL")
            cursor.execute("UPDATE articles SET sentiment_label = sentiment WHERE sentiment IS NOT NULL AND sentiment_label IS NULL")
            cursor.execute("UPDATE articles SET fetched_at = created_at WHERE created_at IS NOT NULL AND fetched_at IS NULL")
            cursor.execute("UPDATE articles SET arabic_text = title_ar || ' ' || COALESCE(summary_ar, '') WHERE title_ar IS NOT NULL AND arabic_text IS NULL")
            print("   ✅ Data migrated to new columns")
        except Exception as e:
            print(f"   ⚠️ Data migration warning (may be expected for new DB): {e}")
        
        # ========== COMMIT ALL CHANGES ==========
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ Complete migration finished successfully!")
        print("=" * 60)
        
        # ========== SHOW FINAL SCHEMA ==========
        print("\n📊 Final Schema:")
        
        cursor.execute("PRAGMA table_info(keywords)")
        print("\n  Keywords table:")
        for row in cursor.fetchall():
            print(f"    - {row[1]} ({row[2]})")
        
        cursor.execute("PRAGMA table_info(articles)")
        print("\n  Articles table:")
        for row in cursor.fetchall():
            print(f"    - {row[1]} ({row[2]})")
        
        print()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        print("   Rolling back changes...")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_complete()
