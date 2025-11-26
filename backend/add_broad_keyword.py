"""
Quick script to add a broad international keyword
This will help fetch articles from many countries, not just Saudi Arabia and USA
"""
from models import get_db, Keyword
from translation_service import translate_keyword

db = get_db()

# Add a broad keyword that will match many countries
keyword_ar = "العالم"  # "The World" - will match international news

print("=" * 80)
print("ADDING BROAD INTERNATIONAL KEYWORD")
print("=" * 80)

# Check if already exists
existing = db.query(Keyword).filter(Keyword.text_ar == keyword_ar).first()
if existing:
    print(f"\n⚠️  Keyword '{keyword_ar}' already exists!")
    print(f"   Enabled: {existing.enabled}")
    if not existing.enabled:
        existing.enabled = True
        db.commit()
        print(f"   ✅ Enabled the keyword")
else:
    # Translate to 7 languages
    print(f"\n🔄 Translating '{keyword_ar}' to 7 languages...")
    translations = translate_keyword(keyword_ar)
    
    if translations:
        # Create keyword
        keyword = Keyword(
            text_ar=keyword_ar,
            text_en=translations.get('en'),
            text_fr=translations.get('fr'),
            text_tr=translations.get('tr'),
            text_ur=translations.get('ur'),
            text_zh=translations.get('zh'),
            text_ru=translations.get('ru'),
            text_es=translations.get('es'),
            enabled=True
        )
        
        db.add(keyword)
        db.commit()
        
        print(f"\n✅ Keyword added successfully!")
        print(f"\n📝 Translations:")
        print(f"   AR: {keyword_ar}")
        print(f"   EN: {translations.get('en')}")
        print(f"   FR: {translations.get('fr')}")
        print(f"   TR: {translations.get('tr')}")
        print(f"   UR: {translations.get('ur')}")
        print(f"   ZH: {translations.get('zh')}")
        print(f"   RU: {translations.get('ru')}")
        print(f"   ES: {translations.get('es')}")
    else:
        print("\n❌ Translation failed!")
        print("   Keyword not added")

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("1. Go to Settings page (الإعدادات)")
print("2. Click 'تشغيل المراقبة الآن' (Run Monitoring Now)")
print("3. Wait for articles to be fetched")
print("4. Go to Dashboard (الخلاصة)")
print("5. Check the country filter dropdown")
print("6. You should now see 5+ countries!")
print("=" * 80)

db.close()
