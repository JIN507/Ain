"""
Fix database schema - make old columns nullable
Run this to allow new code to work with existing schema
"""
import sqlite3

def fix_schema():
    conn = sqlite3.connect('ain_news.db')
    cursor = conn.cursor()
    
    print("🔧 Fixing database schema...")
    
    try:
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        print("📝 Creating new articles table with nullable columns...")
        
        # First, check if there are duplicates
        cursor.execute("SELECT url, COUNT(*) as count FROM articles GROUP BY url HAVING count > 1")
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"   ⚠️ Found {len(duplicates)} duplicate URLs")
            print("   🧹 Removing duplicates (keeping newest)...")
            
            # Delete older duplicates, keep the most recent (highest id)
            total_removed = 0
            for url, count in duplicates:
                cursor.execute("""
                    DELETE FROM articles 
                    WHERE url = ? 
                    AND id NOT IN (
                        SELECT MAX(id) FROM articles WHERE url = ?
                    )
                """, (url, url))
                total_removed += cursor.rowcount
            
            # COMMIT the deletions before proceeding
            conn.commit()
            print(f"   ✅ Removed {total_removed} duplicate entries")
        
        # Create temporary table with correct schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles_new (
                id INTEGER PRIMARY KEY,
                country VARCHAR(100) NOT NULL,
                source_name VARCHAR(200) NOT NULL,
                url VARCHAR(500) NOT NULL UNIQUE,
                
                -- Original content
                title_original TEXT NOT NULL,
                summary_original TEXT,
                original_language VARCHAR(10),
                
                -- Arabic translation
                title_ar TEXT,
                summary_ar TEXT,
                arabic_text TEXT,
                
                -- Keywords
                keyword VARCHAR(200),  -- OLD (nullable for backward compat)
                keyword_original VARCHAR(200),  -- NEW
                keywords_translations TEXT,
                
                -- Sentiment
                sentiment VARCHAR(50),  -- OLD (nullable for backward compat)
                sentiment_label VARCHAR(50),  -- NEW
                sentiment_score VARCHAR(20),
                
                -- Timestamps
                published_at DATETIME,
                fetched_at DATETIME,
                created_at DATETIME,
                
                -- Old language column (deprecated)
                language VARCHAR(10)
            )
        """)
        
        # Copy data from old table to new, keeping only unique URLs (newest entry)
        print("   📋 Copying data (keeping unique URLs only)...")
        cursor.execute("""
            INSERT INTO articles_new 
            SELECT * FROM articles a1
            WHERE a1.id = (
                SELECT MAX(a2.id) 
                FROM articles a2 
                WHERE a2.url = a1.url
            )
        """)
        
        # Drop old table
        cursor.execute("DROP TABLE articles")
        
        # Rename new table
        cursor.execute("ALTER TABLE articles_new RENAME TO articles")
        
        conn.commit()
        
        print("✅ Schema fixed successfully!")
        print("   - Old 'keyword' column: now nullable")
        print("   - Old 'sentiment' column: now nullable")
        print("   - New columns ready to use")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    fix_schema()
