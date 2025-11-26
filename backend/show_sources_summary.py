"""
Show summary of all sources in the database
"""
from models import SessionLocal, Country, Source
from sqlalchemy import func

db = SessionLocal()

print("="*80)
print("SOURCES SUMMARY")
print("="*80)
print()

try:
    # Get all countries with source count
    countries_query = db.query(
        Country.name_ar,
        func.count(Source.id).label('source_count')
    ).outerjoin(Source, Country.id == Source.country_id) \
     .group_by(Country.name_ar) \
     .order_by(func.count(Source.id).desc())
    
    total_countries = 0
    total_sources = 0
    
    for country_name, source_count in countries_query:
        total_countries += 1
        total_sources += source_count
        
        if source_count > 0:
            print(f"  📰 {country_name}: {source_count} sources")
        else:
            print(f"  ⚠️  {country_name}: 0 sources")
    
    print()
    print("="*80)
    print(f"📊 TOTAL: {total_countries} countries, {total_sources} sources")
    print("="*80)
    
    # Show top sources by country
    print()
    print("🌍 TOP 10 COUNTRIES BY SOURCE COUNT:")
    print("-" * 80)
    
    top_countries = db.query(
        Country.name_ar,
        func.count(Source.id).label('source_count')
    ).join(Source, Country.id == Source.country_id) \
     .group_by(Country.name_ar) \
     .order_by(func.count(Source.id).desc()) \
     .limit(10)
    
    for idx, (country_name, source_count) in enumerate(top_countries, 1):
        print(f"  {idx}. {country_name}: {source_count} sources")
    
    print()
    print("="*80)
    
finally:
    db.close()
