from models import get_db, Article
from sqlalchemy import func

db = get_db()

print("=" * 80)
print("DATABASE ANALYSIS - ALL ARTICLES (NO LIMIT)")
print("=" * 80)

# Get total count
total = db.query(Article).count()
print(f"\n✅ Total articles in database: {total}")

# Get countries with counts
countries_query = db.query(
    Article.country,
    func.count(Article.id).label('count')
).group_by(Article.country).order_by(func.count(Article.id).desc())

print(f"\n📊 ALL Countries in database:")
print("-" * 80)

all_countries = []
for country, count in countries_query:
    if country:
        all_countries.append((country, count))
        print(f"   • {country}: {count} articles")
    else:
        print(f"   • [NULL/Empty]: {count} articles")

print(f"\n✅ Total distinct countries: {len(all_countries)}")
print("=" * 80)

if len(all_countries) < 5:
    print("\n⚠️  WARNING: Database only has articles from {} countries!".format(len(all_countries)))
    print("   The backend logs show fetching from many countries,")
    print("   but those articles are not being SAVED to the database.")
    print("\n   NEXT STEPS:")
    print("   1. Run monitoring from Settings page")
    print("   2. Check backend console logs during monitoring")
    print("   3. Verify articles from multiple countries are being saved")
else:
    print(f"\n✅ Database has articles from {len(all_countries)} countries")

db.close()
