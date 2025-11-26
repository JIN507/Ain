"""
Simplest fix - just clear articles and fix schema
Since you haven't done real monitoring yet, we can start fresh
"""
import sqlite3

def simple_fix():
    conn = sqlite3.connect('ain_news.db')
    cursor = conn.cursor()
    
    print("🔧 Simple fix: Clear articles and update schema...")
    
    try:
        # Just drop the entire articles table
        print("   🗑️ Dropping old articles table...")
        cursor.execute("DROP TABLE IF EXISTS articles")
        
        # Create new table with correct schema
        print("   ✅ Creating new articles table with correct schema...")
        cursor.execute("""
            CREATE TABLE articles (
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
                
                -- Keywords (both old and new)
                keyword VARCHAR(200),
                keyword_original VARCHAR(200),
                keywords_translations TEXT,
                
                -- Sentiment (both old and new)
                sentiment VARCHAR(50),
                sentiment_label VARCHAR(50),
                sentiment_score VARCHAR(20),
                
                -- Language (old column)
                language VARCHAR(10),
                
                -- Timestamps
                published_at DATETIME,
                fetched_at DATETIME,
                created_at DATETIME
            )
        """)
        
        conn.commit()
        
        print("\n✅ Fixed successfully!")
        print("   - Articles table recreated")
        print("   - All old columns are nullable")
        print("   - Ready for new monitoring")
        print("\nℹ️ Note: All old articles were cleared (start fresh)")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    simple_fix()
