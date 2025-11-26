"""
Verify that we have sources in database for Top Headlines feature
"""
from models import SessionLocal, Source

db = SessionLocal()

print("="*80)
print("CHECKING SOURCES FOR TOP HEADLINES")
print("="*80)
print()

try:
    # Get all sources grouped by country
    from sqlalchemy import func
    
    countries_query = db.query(
        Source.country_name,
        func.count(Source.id).label('source_count')
    ).filter(Source.enabled == True).group_by(Source.country_name).order_by(func.count(Source.id).desc())
    
    countries = []
    for country, count in countries_query:
        if country:
            countries.append({'name': country, 'count': count})
    
    if countries:
        print(f"✅ Found {len(countries)} countries with sources:\n")
        for c in countries:
            print(f"   📰 {c['name']}: {c['count']} sources")
        
        print(f"\n{'='*80}")
        print("✅ Top Headlines feature is ready to use!")
        print("   Go to the app and select a country from the dropdown.")
        
    else:
        print("❌ NO SOURCES FOUND IN DATABASE!")
        print("\nYou need to add sources first:")
        print("   1. Go to 'الدول' (Countries) page in the app")
        print("   2. Add countries")
        print("   3. Add RSS sources for each country")
        print("\nOr run the system monitoring to auto-populate sources.")
        
finally:
    db.close()

print()
