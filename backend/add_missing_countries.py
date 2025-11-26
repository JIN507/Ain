"""
Add missing countries to the database
"""
from models import SessionLocal, Country

MISSING_COUNTRIES = [
    'أستراليا',
    'إسبانيا',
    'إندونيسيا',
    'إيطاليا',
    'الأرجنتين',
    'البرازيل',
    'الفلبين',
    'المكسيك',
    'باكستان',
    'بيرو',
    'تايلاند',
    'تشيلي',
    'جنوب أفريقيا',
    'فيتنام',
    'كندا',
    'كولومبيا',
    'كينيا',
    'ماليزيا',
    'نيجيريا',
]

def main():
    db = SessionLocal()
    
    print("="*80)
    print("ADDING MISSING COUNTRIES")
    print("="*80)
    print()
    
    try:
        # Get existing countries
        existing_countries = db.query(Country).all()
        existing_names = {c.name_ar for c in existing_countries}
        
        print(f"📊 Current countries in database: {len(existing_names)}")
        print()
        
        added_count = 0
        skipped_count = 0
        
        for country_name in sorted(MISSING_COUNTRIES):
            if country_name in existing_names:
                print(f"  ⏭️  SKIP: {country_name} (already exists)")
                skipped_count += 1
                continue
            
            # Add new country
            new_country = Country(
                name_ar=country_name,
                enabled=True
            )
            
            db.add(new_country)
            print(f"  ✅ ADDED: {country_name}")
            added_count += 1
        
        # Commit all changes
        db.commit()
        
        print()
        print("="*80)
        print("SUMMARY")
        print("="*80)
        print(f"✅ Added: {added_count} new countries")
        print(f"⏭️  Skipped: {skipped_count} existing countries")
        print(f"📊 Total countries now: {len(existing_names) + added_count}")
        print()
        print("="*80)
        print("✅ DONE!")
        print("="*80)
        print()
        print("💡 Next step: Run add_global_sources.py again to add sources for these countries")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    main()
