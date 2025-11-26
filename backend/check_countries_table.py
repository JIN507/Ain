"""
Check countries in the Country table
"""
from models import SessionLocal, Country, Source

db = SessionLocal()

print("="*80)
print("CHECKING COUNTRY TABLE")
print("="*80)
print()

try:
    # Get all countries
    countries = db.query(Country).all()
    
    if countries:
        print(f"✅ Found {len(countries)} countries in Country table:\n")
        for c in countries:
            status = "✅ Enabled" if c.enabled else "❌ Disabled"
            
            # Count sources for this country
            source_count = db.query(Source).filter(
                Source.country_name == c.name_ar,
                Source.enabled == True
            ).count()
            
            print(f"   {status} | {c.name_ar} | {source_count} sources")
        
        # Show only enabled countries with sources
        print(f"\n{'='*80}")
        print("COUNTRIES THAT WILL APPEAR IN TOP HEADLINES:")
        print("="*80)
        
        enabled_with_sources = []
        for c in countries:
            if c.enabled:
                source_count = db.query(Source).filter(
                    Source.country_name == c.name_ar,
                    Source.enabled == True
                ).count()
                if source_count > 0:
                    enabled_with_sources.append({'name': c.name_ar, 'count': source_count})
        
        if enabled_with_sources:
            print()
            for item in enabled_with_sources:
                print(f"   📰 {item['name']}: {item['count']} sources")
            print(f"\n✅ Total: {len(enabled_with_sources)} countries will appear")
        else:
            print("\n❌ NO countries with sources found!")
            print("   Make sure:")
            print("   1. Countries are enabled")
            print("   2. Sources exist with matching country names")
        
    else:
        print("❌ NO COUNTRIES FOUND IN DATABASE!")
        print("\nYou need to add countries first:")
        print("   1. Go to 'الدول' (Countries) page")
        print("   2. Add countries")
        print("   3. Add sources for each country")
        
finally:
    db.close()

print()
