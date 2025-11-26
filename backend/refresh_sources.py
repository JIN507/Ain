"""
Refresh sources in database based on seed_data.py
This will enable newly-enabled sources without deleting existing data
"""
from models import get_db, Source
from seed_data import VERIFIED_FEEDS

db = get_db()

print("🔄 Refreshing sources from seed_data.py...\n")

updated = 0
added = 0

for country_name, feeds in VERIFIED_FEEDS.items():
    for feed in feeds:
        # Check if source exists
        existing = db.query(Source).filter(
            Source.country_name == country_name,
            Source.name == feed['name']
        ).first()
        
        if existing:
            # Update enabled status if it changed
            if existing.enabled != feed.get('enabled', True):
                existing.enabled = feed.get('enabled', True)
                status = "✅ ENABLED" if existing.enabled else "❌ DISABLED"
                print(f"{status}: {country_name} | {feed['name']}")
                updated += 1
        else:
            # Add new source
            new_source = Source(
                country_name=country_name,
                name=feed['name'],
                url=feed['url'],
                enabled=feed.get('enabled', True)
            )
            db.add(new_source)
            print(f"➕ ADDED: {country_name} | {feed['name']}")
            added += 1

db.commit()

print(f"\n{'='*60}")
print(f"✅ Refresh complete!")
print(f"   Updated: {updated} sources")
print(f"   Added: {added} sources")
print(f"{'='*60}\n")

# Show summary by country
print("📊 Enabled sources by country:\n")
countries = db.query(Source.country_name).distinct().all()
for (country,) in countries:
    enabled_count = db.query(Source).filter(
        Source.country_name == country,
        Source.enabled == True
    ).count()
    total_count = db.query(Source).filter(Source.country_name == country).count()
    print(f"   {country}: {enabled_count}/{total_count} enabled")

db.close()
