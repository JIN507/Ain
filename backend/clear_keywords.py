"""
Quick script to clear all existing keywords from database
Run this once to remove old keywords without translations
"""
from models import get_db, Keyword

db = get_db()
try:
    count = db.query(Keyword).count()
    db.query(Keyword).delete()
    db.commit()
    print(f"✅ Deleted {count} old keywords from database")
    print("   You can now add new keywords with translations")
except Exception as e:
    print(f"❌ Error: {str(e)}")
    db.rollback()
finally:
    db.close()
