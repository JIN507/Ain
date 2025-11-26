"""
Database migration v2 - Update article schema to match new specification
Run this to add new columns to articles table
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('ain_news.db')
    cursor = conn.cursor()
    
    print("🔄 Migrating database to v2...")
    
    try:
        # Rename old columns and add new ones for articles table
        print("📝 Updating articles table schema...")
        
        new_columns = [
            ('original_language', 'VARCHAR(10)'),
            ('arabic_text', 'TEXT'),
            ('keyword_original', 'VARCHAR(200)'),
            ('keywords_translations', 'TEXT'),
            ('sentiment_label', 'VARCHAR(50)'),
            ('sentiment_score', 'VARCHAR(20)'),
            ('fetched_at', 'DATETIME'),
        ]
        
        for col_name, col_type in new_columns:
            try:
                cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
                print(f"   ✅ Added {col_name}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e):
                    print(f"   ⏭️ {col_name} already exists")
                else:
                    raise
        
        # Copy data from old columns to new ones
        print("📝 Migrating existing data...")
        try:
            cursor.execute("UPDATE articles SET original_language = language WHERE language IS NOT NULL")
            cursor.execute("UPDATE articles SET keyword_original = keyword WHERE keyword IS NOT NULL")
            cursor.execute("UPDATE articles SET sentiment_label = sentiment WHERE sentiment IS NOT NULL")
            cursor.execute("UPDATE articles SET fetched_at = created_at WHERE created_at IS NOT NULL")
            cursor.execute("UPDATE articles SET arabic_text = title_ar || ' ' || COALESCE(summary_ar, '') WHERE title_ar IS NOT NULL")
            print("   ✅ Data migrated")
        except Exception as e:
            print(f"   ⚠️ Data migration error (may be expected if fresh DB): {e}")
        
        conn.commit()
        print("\n✅ Migration v2 completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
