"""
Database migration script to add new columns for keyword translations and article language
Run this once to update existing database
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('ain_news.db')
    cursor = conn.cursor()
    
    print("🔄 Migrating database...")
    
    try:
        # Add translation columns to keywords table
        print("📝 Adding translation columns to keywords table...")
        columns_to_add = [
            ('text_en', 'VARCHAR(200)'),
            ('text_fr', 'VARCHAR(200)'),
            ('text_tr', 'VARCHAR(200)'),
            ('text_ur', 'VARCHAR(200)'),
            ('text_zh', 'VARCHAR(200)'),
            ('text_ru', 'VARCHAR(200)'),
            ('text_es', 'VARCHAR(200)')
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE keywords ADD COLUMN {col_name} {col_type}")
                print(f"   ✅ Added {col_name}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e):
                    print(f"   ⏭️ {col_name} already exists")
                else:
                    raise
        
        # Remove old translations column if it exists
        try:
            # SQLite doesn't support DROP COLUMN, so we check if it exists
            cursor.execute("PRAGMA table_info(keywords)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'translations' in columns:
                print("   ℹ️ Old 'translations' column exists (SQLite can't drop it, but it won't be used)")
        except:
            pass
        
        # Add language column to articles table
        print("📝 Adding language column to articles table...")
        try:
            cursor.execute("ALTER TABLE articles ADD COLUMN language VARCHAR(10)")
            print("   ✅ Added language column")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                print("   ⏭️ language column already exists")
            else:
                raise
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
