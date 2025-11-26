"""
Check if RT article about Egypt exists in database
"""
from models import SessionLocal, Article, Keyword

db = SessionLocal()

# Check for the specific article
url_pattern = "1727904"
articles = db.query(Article).filter(Article.url.like(f'%{url_pattern}%')).all()

print("="*80)
print("CHECKING DATABASE FOR RT ARTICLE")
print("="*80)
print()
print(f"Looking for article with URL containing: {url_pattern}")
print(f"Found: {len(articles)} article(s)")
print()

if articles:
    for a in articles:
        print(f"✅ ARTICLE FOUND:")
        print(f"   ID: {a.id}")
        print(f"   Title (AR): {a.title_ar[:100] if a.title_ar else 'N/A'}")
        print(f"   Keyword: {a.keyword_original}")
        print(f"   URL: {a.url}")
        print(f"   Created: {a.created_at}")
else:
    print("❌ ARTICLE NOT FOUND IN DATABASE")
    print()
    print("This means the article was NOT captured during monitoring.")
    print()
    
    # Check if keyword exists
    print("Checking if 'مصر' keyword exists...")
    keyword = db.query(Keyword).filter(Keyword.text_ar == 'مصر').first()
    if keyword:
        print(f"✅ Keyword 'مصر' exists:")
        print(f"   Enabled: {keyword.enabled}")
        print(f"   Translations: EN={keyword.text_en}, FR={keyword.text_fr}")
    else:
        print("❌ Keyword 'مصر' NOT FOUND in keywords table!")
        print("   The keyword must be added first!")
    
    print()
    # Check total articles from RT
    print("Checking articles from RT Arabic...")
    rt_articles = db.query(Article).filter(Article.url.like('%arabic.rt.com%')).count()
    print(f"Total articles from RT Arabic in database: {rt_articles}")
    
    # Check latest articles
    print()
    print("Latest 5 articles in database:")
    latest = db.query(Article).order_by(Article.id.desc()).limit(5).all()
    for a in latest:
        print(f"   ID {a.id}: {a.title_ar[:60] if a.title_ar else a.title_original[:60]}... (Keyword: {a.keyword_original})")

db.close()
