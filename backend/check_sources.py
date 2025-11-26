from models import get_db, Source, Keyword
from sqlalchemy import func

db = get_db()

print("=" * 80)
print("SOURCE & KEYWORD ANALYSIS")
print("=" * 80)

# Check sources
total_sources = db.query(Source).count()
enabled_sources = db.query(Source).filter(Source.enabled == True).count()

print(f"\n📡 SOURCES:")
print(f"   Total: {total_sources}")
print(f"   Enabled: {enabled_sources}")

# Group by country
print(f"\n📊 Enabled sources by country:")
countries_sources = db.query(
    Source.country_name,
    func.count(Source.id).label('count')
).filter(Source.enabled == True).group_by(Source.country_name).order_by(func.count(Source.id).desc())

for country, count in countries_sources:
    print(f"   • {country}: {count} sources")

# Check keywords
total_keywords = db.query(Keyword).count()
enabled_keywords = db.query(Keyword).filter(Keyword.enabled == True).count()

print(f"\n🔑 KEYWORDS:")
print(f"   Total: {total_keywords}")
print(f"   Enabled: {enabled_keywords}")

if enabled_keywords > 0:
    keywords = db.query(Keyword).filter(Keyword.enabled == True).all()
    for kw in keywords:
        print(f"   • {kw.text_ar}")

print("\n" + "=" * 80)

if enabled_sources < 10:
    print(f"\n⚠️  Only {enabled_sources} sources enabled!")
    print("   You may need to enable more sources from different countries.")
    print("   Run: python refresh_sources.py")
elif enabled_keywords == 0:
    print("\n⚠️  No keywords enabled!")
    print("   Add keywords from the UI or run seed_data.py")
else:
    print(f"\n✅ Ready to fetch from {enabled_sources} sources with {enabled_keywords} keywords")

db.close()
