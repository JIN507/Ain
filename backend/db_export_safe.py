"""
Safe Database Export Scripts
Exports schema (DDL) and data with PII redaction
"""
import sqlite3
import json
import os
from datetime import datetime
import hashlib

DB_PATH = "ain_news.db"
EXPORT_DIR = "db_exports"

def ensure_export_dir():
    """Create export directory if not exists"""
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
    return EXPORT_DIR

def redact_email(email):
    """Redact email for privacy"""
    if not email:
        return None
    parts = email.split('@')
    if len(parts) == 2:
        return parts[0][:2] + '***@' + parts[1][:3] + '***'
    return '***@***'

def redact_hash(value):
    """Hash sensitive values"""
    if not value:
        return None
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]

def truncate_text(text, max_len=100):
    """Truncate long text"""
    if not text:
        return None
    if len(text) <= max_len:
        return text
    return text[:max_len] + '...'


# ============================================================
# 1. EXPORT SCHEMA (DDL)
# ============================================================

def export_schema():
    """Export database schema as SQL DDL"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    export_dir = ensure_export_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{export_dir}/schema_{timestamp}.sql"
    
    print("📋 Exporting database schema...")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("-- Ain News Monitor - Database Schema Export\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write("-- Engine: SQLite 3\n\n")
        
        # Get all tables
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cur.fetchall()
        
        for table_name, create_sql in tables:
            if create_sql:  # Skip internal tables
                f.write(f"-- Table: {table_name}\n")
                f.write(create_sql + ";\n\n")
                
                # Get indexes for this table
                cur.execute(f"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table_name,))
                indexes = cur.fetchall()
                for idx in indexes:
                    if idx[0]:
                        f.write(idx[0] + ";\n")
                f.write("\n")
    
    conn.close()
    print(f"✅ Schema exported to: {filename}")
    return filename


# ============================================================
# 2. EXPORT DATA (JSON with redaction)
# ============================================================

def export_data_safe():
    """Export all data with PII redaction"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    export_dir = ensure_export_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("📦 Exporting data with redaction...")
    
    exports = {}
    
    # ---- users (redact email, hash password) ----
    print("  - Exporting users...")
    cur.execute("SELECT * FROM users")
    users = []
    for row in cur.fetchall():
        users.append({
            'id': row['id'],
            'email': redact_email(row['email']),
            'name': row['name'][:10] + '***' if row['name'] else None,
            'password_hash': '[REDACTED]',
            'role': row['role'],
            'is_active': row['is_active'],
            'must_change_password': row['must_change_password'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        })
    exports['users'] = users
    
    # ---- countries (safe - no PII) ----
    print("  - Exporting countries...")
    cur.execute("SELECT * FROM countries")
    exports['countries'] = [dict(row) for row in cur.fetchall()]
    
    # ---- sources (safe - no PII) ----
    print("  - Exporting sources...")
    cur.execute("SELECT * FROM sources")
    exports['sources'] = [dict(row) for row in cur.fetchall()]
    
    # ---- keywords (safe - no PII, just text) ----
    print("  - Exporting keywords...")
    cur.execute("SELECT * FROM keywords")
    exports['keywords'] = [dict(row) for row in cur.fetchall()]
    
    # ---- articles (truncate long text) ----
    print("  - Exporting articles...")
    cur.execute("SELECT * FROM articles")
    articles = []
    for row in cur.fetchall():
        articles.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'country': row['country'],
            'source_name': row['source_name'],
            'url': row['url'],
            'title_original': truncate_text(row['title_original'], 200),
            'summary_original': truncate_text(row['summary_original'], 300),
            'original_language': row['original_language'],
            'image_url': row['image_url'],
            'title_ar': truncate_text(row['title_ar'], 200),
            'summary_ar': truncate_text(row['summary_ar'], 300),
            'keyword_original': row['keyword_original'],
            'sentiment_label': row['sentiment_label'],
            'published_at': row['published_at'],
            'created_at': row['created_at']
        })
    exports['articles'] = articles
    
    # ---- exports (safe) ----
    print("  - Exporting export records...")
    cur.execute("SELECT * FROM exports")
    exports['exports'] = [dict(row) for row in cur.fetchall()]
    
    # ---- search_history (safe) ----
    print("  - Exporting search history...")
    cur.execute("SELECT * FROM search_history")
    exports['search_history'] = [dict(row) for row in cur.fetchall()]
    
    # ---- user_files (redact filenames) ----
    print("  - Exporting user files...")
    cur.execute("SELECT * FROM user_files")
    user_files = []
    for row in cur.fetchall():
        user_files.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'filename': '[REDACTED]',
            'stored_filename': '[REDACTED]',
            'file_type': row['file_type'],
            'file_size': row['file_size'],
            'created_at': row['created_at']
        })
    exports['user_files'] = user_files
    
    # ---- audit_log (redact meta_json) ----
    print("  - Exporting audit log...")
    cur.execute("SELECT * FROM audit_log")
    audit = []
    for row in cur.fetchall():
        audit.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'admin_id': row['admin_id'],
            'action': row['action'],
            'meta_json': '[REDACTED]',
            'created_at': row['created_at']
        })
    exports['audit_log'] = audit
    
    # ---- Junction tables ----
    for table in ['user_articles', 'user_countries', 'user_sources']:
        print(f"  - Exporting {table}...")
        try:
            cur.execute(f"SELECT * FROM {table}")
            exports[table] = [dict(row) for row in cur.fetchall()]
        except:
            exports[table] = []
    
    conn.close()
    
    # Save to JSON
    filename = f"{export_dir}/data_safe_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(exports, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"✅ Data exported to: {filename}")
    
    # Print summary
    print("\n📊 Export Summary:")
    for table, data in exports.items():
        print(f"   {table}: {len(data)} rows")
    
    return filename


# ============================================================
# 3. EXPORT DATA COUNTS ONLY (No actual data)
# ============================================================

def export_stats_only():
    """Export only statistics, no actual data"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    export_dir = ensure_export_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("📊 Exporting statistics only...")
    
    stats = {
        'generated_at': datetime.now().isoformat(),
        'db_engine': 'SQLite',
        'tables': {}
    }
    
    # Get all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]
    
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        
        # Get column count
        cur.execute(f"PRAGMA table_info({table})")
        columns = len(cur.fetchall())
        
        stats['tables'][table] = {
            'row_count': count,
            'column_count': columns
        }
    
    # User distribution
    cur.execute("""
        SELECT user_id, COUNT(*) as cnt 
        FROM articles 
        WHERE user_id IS NOT NULL 
        GROUP BY user_id
    """)
    stats['articles_per_user'] = {str(row[0]): row[1] for row in cur.fetchall()}
    
    cur.execute("""
        SELECT user_id, COUNT(*) as cnt 
        FROM keywords 
        WHERE user_id IS NOT NULL 
        GROUP BY user_id
    """)
    stats['keywords_per_user'] = {str(row[0]): row[1] for row in cur.fetchall()}
    
    conn.close()
    
    # Save to JSON
    filename = f"{export_dir}/stats_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Stats exported to: {filename}")
    return filename


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("📦 AIN NEWS MONITOR - Database Safe Export")
    print("=" * 60)
    
    print("\n[1/3] Exporting Schema (DDL)...")
    schema_file = export_schema()
    
    print("\n[2/3] Exporting Data (with redaction)...")
    data_file = export_data_safe()
    
    print("\n[3/3] Exporting Statistics Only...")
    stats_file = export_stats_only()
    
    print("\n" + "=" * 60)
    print("✅ All exports complete!")
    print(f"   Schema: {schema_file}")
    print(f"   Data:   {data_file}")
    print(f"   Stats:  {stats_file}")
    print("=" * 60)
