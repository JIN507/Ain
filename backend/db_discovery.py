"""
Database Discovery Script
Comprehensive analysis of the SQLite database for Ain News Monitor
"""
import sqlite3
import json
from datetime import datetime

DB_PATH = "ain_news.db"

def run_discovery():
    """Run complete database discovery"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    report = []
    report.append("=" * 80)
    report.append("📊 AIN NEWS MONITOR - DATABASE DISCOVERY REPORT")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("=" * 80)
    
    # 1. List all tables
    report.append("\n\n## 1. ALL TABLES IN DATABASE")
    report.append("-" * 40)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]
    for t in tables:
        report.append(f"  - {t}")
    
    # 2. Schema for each table
    report.append("\n\n## 2. DETAILED SCHEMA FOR EACH TABLE")
    report.append("-" * 40)
    
    for table in tables:
        report.append(f"\n### TABLE: {table}")
        
        # Columns
        cur.execute(f"PRAGMA table_info({table})")
        columns = cur.fetchall()
        report.append("  COLUMNS:")
        for col in columns:
            cid, name, dtype, notnull, default, pk = col
            flags = []
            if pk: flags.append("PK")
            if notnull: flags.append("NOT NULL")
            if default is not None: flags.append(f"DEFAULT={default}")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            report.append(f"    - {name}: {dtype}{flag_str}")
        
        # Foreign Keys
        cur.execute(f"PRAGMA foreign_key_list({table})")
        fks = cur.fetchall()
        if fks:
            report.append("  FOREIGN KEYS:")
            for fk in fks:
                report.append(f"    - {fk[3]} -> {fk[2]}.{fk[4]}")
        
        # Indexes
        cur.execute(f"PRAGMA index_list({table})")
        indexes = cur.fetchall()
        if indexes:
            report.append("  INDEXES:")
            for idx in indexes:
                idx_name = idx[1]
                unique = "UNIQUE" if idx[2] else ""
                cur.execute(f"PRAGMA index_info({idx_name})")
                idx_cols = [r[2] for r in cur.fetchall()]
                report.append(f"    - {idx_name}: ({', '.join(idx_cols)}) {unique}")
    
    # 3. Row counts
    report.append("\n\n## 3. ROW COUNTS")
    report.append("-" * 40)
    row_counts = {}
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        row_counts[table] = count
        report.append(f"  {table}: {count:,} rows")
    
    # 4. User distribution analysis
    report.append("\n\n## 4. USER DISTRIBUTION ANALYSIS")
    report.append("-" * 40)
    
    # Users summary
    cur.execute("SELECT id, email, role, is_active, created_at FROM users")
    users = cur.fetchall()
    report.append(f"\n### Users ({len(users)} total):")
    for u in users:
        email_redacted = u[1][:3] + "***@***" if u[1] else "NULL"
        report.append(f"  - ID={u[0]}, Email={email_redacted}, Role={u[2]}, Active={u[3]}")
    
    # Keywords per user
    report.append("\n### Keywords per User:")
    cur.execute("""
        SELECT user_id, COUNT(*) as cnt 
        FROM keywords 
        GROUP BY user_id 
        ORDER BY cnt DESC
    """)
    for row in cur.fetchall():
        report.append(f"  - user_id={row[0]}: {row[1]} keywords")
    
    # NULL user_id in keywords
    cur.execute("SELECT COUNT(*) FROM keywords WHERE user_id IS NULL")
    null_kw = cur.fetchone()[0]
    report.append(f"  ⚠️ Keywords with NULL user_id: {null_kw}")
    
    # Articles per user
    report.append("\n### Articles per User:")
    cur.execute("""
        SELECT user_id, COUNT(*) as cnt 
        FROM articles 
        GROUP BY user_id 
        ORDER BY cnt DESC
    """)
    for row in cur.fetchall():
        report.append(f"  - user_id={row[0]}: {row[1]} articles")
    
    # NULL user_id in articles
    cur.execute("SELECT COUNT(*) FROM articles WHERE user_id IS NULL")
    null_art = cur.fetchone()[0]
    report.append(f"  ⚠️ Articles with NULL user_id: {null_art}")
    
    # 5. Data anomalies
    report.append("\n\n## 5. DATA ANOMALIES & POTENTIAL ISSUES")
    report.append("-" * 40)
    
    # Check for orphaned FKs in articles
    cur.execute("""
        SELECT COUNT(*) FROM articles a
        WHERE a.user_id IS NOT NULL 
        AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = a.user_id)
    """)
    orphaned_articles = cur.fetchone()[0]
    report.append(f"  - Orphaned articles (user_id not in users): {orphaned_articles}")
    
    # Check for orphaned FKs in keywords
    cur.execute("""
        SELECT COUNT(*) FROM keywords k
        WHERE k.user_id IS NOT NULL 
        AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = k.user_id)
    """)
    orphaned_keywords = cur.fetchone()[0]
    report.append(f"  - Orphaned keywords (user_id not in users): {orphaned_keywords}")
    
    # Duplicate keywords (same text_ar for same user)
    cur.execute("""
        SELECT user_id, text_ar, COUNT(*) as cnt 
        FROM keywords 
        GROUP BY user_id, text_ar 
        HAVING cnt > 1
    """)
    dup_keywords = cur.fetchall()
    report.append(f"  - Duplicate keywords (same user_id + text_ar): {len(dup_keywords)}")
    
    # Duplicate article URLs
    cur.execute("""
        SELECT url, COUNT(*) as cnt 
        FROM articles 
        GROUP BY url 
        HAVING cnt > 1
    """)
    dup_urls = cur.fetchall()
    report.append(f"  - Duplicate article URLs: {len(dup_urls)}")
    
    # 6. Sample data (redacted)
    report.append("\n\n## 6. SAMPLE DATA (REDACTED)")
    report.append("-" * 40)
    
    # Sample keywords
    report.append("\n### Sample Keywords (first 5):")
    cur.execute("SELECT id, user_id, text_ar, enabled, created_at FROM keywords LIMIT 5")
    for row in cur.fetchall():
        report.append(f"  - ID={row[0]}, user_id={row[1]}, text_ar='{row[2][:30] if row[2] else 'NULL'}...', enabled={row[3]}")
    
    # Sample articles
    report.append("\n### Sample Articles (first 5):")
    cur.execute("""
        SELECT id, user_id, country, source_name, keyword_original, 
               substr(title_ar, 1, 50) as title_preview, created_at 
        FROM articles LIMIT 5
    """)
    for row in cur.fetchall():
        report.append(f"  - ID={row[0]}, user_id={row[1]}, country={row[2]}, source={row[3]}")
        report.append(f"    keyword={row[4]}, title='{row[5]}...'")
    
    # 7. Countries and Sources summary
    report.append("\n\n## 7. SHARED/SYSTEM DATA")
    report.append("-" * 40)
    
    # Countries
    cur.execute("SELECT COUNT(*) FROM countries")
    report.append(f"  - Countries: {cur.fetchone()[0]}")
    
    # Countries with user_id
    cur.execute("SELECT COUNT(*) FROM countries WHERE user_id IS NOT NULL")
    report.append(f"  - Countries with user_id: {cur.fetchone()[0]}")
    
    # Sources
    cur.execute("SELECT COUNT(*) FROM sources")
    report.append(f"  - Sources: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(DISTINCT country_name) FROM sources")
    report.append(f"  - Unique country names in sources: {cur.fetchone()[0]}")
    
    # Sources per country (top 10)
    report.append("\n### Top 10 Countries by Source Count:")
    cur.execute("""
        SELECT country_name, COUNT(*) as cnt 
        FROM sources 
        GROUP BY country_name 
        ORDER BY cnt DESC 
        LIMIT 10
    """)
    for row in cur.fetchall():
        report.append(f"  - {row[0]}: {row[1]} sources")
    
    # 8. Search history and exports
    report.append("\n\n## 8. USER ACTIVITY DATA")
    report.append("-" * 40)
    
    # Search history per user
    cur.execute("""
        SELECT user_id, search_type, COUNT(*) as cnt 
        FROM search_history 
        GROUP BY user_id, search_type
    """)
    history = cur.fetchall()
    if history:
        report.append("### Search History by User and Type:")
        for row in history:
            report.append(f"  - user_id={row[0]}, type={row[1]}: {row[2]} searches")
    else:
        report.append("  - No search history records")
    
    # Exports per user
    cur.execute("""
        SELECT user_id, COUNT(*) as cnt, SUM(article_count) as total_articles 
        FROM exports 
        GROUP BY user_id
    """)
    exports = cur.fetchall()
    if exports:
        report.append("\n### Exports by User:")
        for row in exports:
            report.append(f"  - user_id={row[0]}: {row[1]} exports, {row[2]} total articles")
    else:
        report.append("  - No export records")
    
    # User files
    cur.execute("SELECT user_id, COUNT(*) FROM user_files GROUP BY user_id")
    files = cur.fetchall()
    if files:
        report.append("\n### User Files:")
        for row in files:
            report.append(f"  - user_id={row[0]}: {row[1]} files")
    else:
        report.append("  - No user files")
    
    # Audit log
    cur.execute("SELECT COUNT(*) FROM audit_log")
    report.append(f"\n### Audit Log: {cur.fetchone()[0]} entries")
    
    conn.close()
    
    # Print report
    full_report = "\n".join(report)
    print(full_report)
    
    # Save to file
    with open("db_discovery_report.txt", "w", encoding="utf-8") as f:
        f.write(full_report)
    
    print("\n\n✅ Report saved to db_discovery_report.txt")
    return full_report

if __name__ == "__main__":
    run_discovery()
