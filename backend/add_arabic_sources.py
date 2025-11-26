"""
Add verified Arabic and Gulf RSS feeds
Checks for duplicates before adding
"""
from models import SessionLocal, Country, Source

# Arabic RSS feeds organized by country
ARABIC_FEEDS = {
    # Gulf Countries (GCC)
    'الإمارات': [
        ('https://www.aljazeera.com/xml/rss/all.xml', 'Al Jazeera'),
        ('https://skynewsarabia.com/rss.xml', 'Sky News Arabia'),
        ('https://emirates247.com/cmlink/rss-feed', 'Emirates 247'),
        ('https://emaratalyoum.com/feed', 'Emarat Al Youm'),
        ('https://www.thenationalnews.com/rss', 'The National News'),
        ('https://arabianbusiness.com/gcc/uae/feed', 'Arabian Business UAE'),
        ('https://thearabianpost.com/feed', 'The Arabian Post'),
        ('https://gulfnews.com/rss/index.html', 'Gulf News'),
    ],
    'السعودية': [
        ('https://www.arabnews.com/rss', 'Arab News'),
        ('https://aawsat.com/feed', 'Asharq Al-Awsat'),
        ('https://www.alriyadh.com/rss', 'Al Riyadh'),
        ('https://okaz.com.sa/rss/rss.xml', 'Okaz'),
        ('https://www.alarabiya.net/rss', 'Al Arabiya'),
        ('https://english.aawsat.com/feed', 'Asharq Al-Awsat English'),
        ('https://sabq.org/rss', 'Sabq'),
        ('https://www.aleqt.com/feed', 'Al-Eqtisadiah'),
        ('https://www.alwatan.com.sa/feed', 'Al Watan Saudi'),
    ],
    'قطر': [
        ('https://www.aljazeera.com/xml/rss/all.xml', 'Al Jazeera'),
        ('https://www.dohanews.co/feed', 'Doha News'),
        ('https://al-sharq.com/rss/latestNews', 'Al-Sharq'),
        ('https://www.gulf-times.com/rss', 'Gulf Times'),
    ],
    'الكويت': [
        ('https://www.arabtimes.com/rss', 'Arab Times Kuwait'),
        ('https://www.alqabas.com/rss', 'Al Qabas'),
        ('https://www.kuna.net.kw/rss', 'Kuwait News Agency'),
    ],
    'البحرين': [
        ('https://www.bahraintribune.com/rss', 'Bahrain Tribune'),
        ('https://www.alayam.com/rss', 'Al Ayam Bahrain'),
        ('https://www.bna.bh/rss', 'Bahrain News Agency'),
    ],
    'عُمان': [
        ('https://www.timesofoman.com/rss', 'Times of Oman'),
        ('https://www.omanobserver.om/rss', 'Oman Observer'),
        ('https://www.alwatan.om/rss', 'Al Watan Oman'),
        ('https://www.omannews.gov.om/rss', 'Oman News Agency'),
    ],
    
    # Levantine Countries
    'لبنان': [
        ('https://www.annahar.com/rss', 'An-Nahar'),
        ('https://www.thedailystarnews.com/feed', 'The Daily Star Lebanon'),
        ('https://www.aliwaa.com.lb/rss', 'Al Liwa'),
        ('https://www.elnashra.com/rss', 'El Nashra'),
        ('https://www.alakhbar.com/rss', 'Al Akhbar Lebanon'),
        ('https://www.lpagency.net/rss', 'Lebanese Press Agency'),
    ],
    'سوريا': [
        ('https://www.sana.sy/en/rss', 'Syrian Arab News Agency'),
    ],
    'الأردن': [
        ('https://www.jordantimes.com/rss', 'Jordan Times'),
        ('https://www.alghad.com/rss', 'Al Ghad'),
        ('https://petra.gov.jo/rss', 'Petra News Agency'),
    ],
    
    # North Africa (Maghreb)
    'مصر': [
        ('https://www.almasryalyoum.com/rss/rssfeed', 'Al-Masry Al-Youm'),
        ('https://www.bbc.com/arabic/feed.xml', 'BBC Arabic'),
        ('https://www.ahram.org.eg/rss', 'Al Ahram'),
        ('https://www.akhbarelyom.com/rss', 'Akhbar El Yom'),
        ('https://www.youm7.com/feed', 'Youm7'),
        ('https://www.mena.org.eg/rss', 'Middle East News Agency'),
        ('https://arabic.cnn.com/rss/feed.xml', 'CNN Arabic'),
    ],
    'المغرب': [
        ('https://www.telquel.ma/feed', 'TelQuel'),
        ('https://www.hespress.com/rss', 'Hespress'),
        ('https://www.almassae.ma/rss', 'Al Massae'),
        ('https://www.maroc.ma/rss', 'Official Morocco News'),
        ('https://www.map.ma/rss', 'Moroccan Press Agency'),
    ],
    'تونس': [
        ('https://www.assabah.tn/rss', 'Assabah'),
        ('https://www.afriquinfos.com/feeds/tunisie.rss', 'AfrikInfo Tunisia'),
        ('https://www.businessnews.com.tn/rss', 'Business News Tunisia'),
        ('https://www.tap.info.tn/rss', 'Tunisian Press Agency'),
    ],
    'الجزائر': [
        ('https://www.elkhabar.com/rss', 'El Khabar'),
        ('https://www.ennaharonline.com/rss', 'Ennahar Online'),
        ('https://www.aps.dz/rss', 'Algerian Press Service'),
        ('https://www.radioalgerie.dz/fr/rss', 'Radio Algérie'),
    ],
    
    # Other Arab Countries
    'العراق': [
        ('https://www.asaaspress.com/rss', 'Asaas Press'),
        ('https://www.iraqinews.com/rss', 'Iraqi News'),
        ('https://www.ina.iq/rss', 'Iraqi News Agency'),
    ],
    'فلسطين': [
        ('https://www.wafa.ps/rss', 'WAFA News Agency'),
        ('https://www.maan-ctr.org/rss', 'Ma\'an News Agency'),
    ],
    'اليمن': [
        ('https://www.sputnikarabic.ae/yemen/rss', 'Sputnik Arabic Yemen'),
    ],
    'السودان': [
        ('https://www.sudanTribune.com/rss', 'Sudan Tribune'),
    ],
    
    # International Arabic Services (categorized as دولي)
    'دولي': [
        ('https://www.france24.com/en/rss', 'France 24 Arabic'),
        ('https://arabic.rt.com/feeds/news/', 'Russia Today Arabic'),
        ('https://www.menafn.com/rss', 'MENAFN'),
        ('https://www.newarab.com/rss', 'The New Arab'),
        ('https://www.albawaba.com/rss/ar-all', 'Al Bawaba Arabic'),
        ('https://www.thearabweekly.com/feeds', 'The Arab Weekly'),
        ('https://www.arabianbusiness.com/rss', 'Arabian Business'),
        ('https://www.arabiangulfnews.com/rss', 'Arabian Gulf News'),
        ('https://www.gulftalent.com/rss', 'Gulf Talent'),
    ],
}

# Countries that might need to be added
MISSING_COUNTRIES = [
    'الكويت',
    'البحرين',
    'عُمان',
    'لبنان',
    'سوريا',
    'الأردن',
    'تونس',
    'الجزائر',
    'العراق',
    'فلسطين',
    'اليمن',
    'السودان',
]

def add_missing_countries(db):
    """Add countries that don't exist yet"""
    existing_countries = db.query(Country).all()
    existing_names = {c.name_ar for c in existing_countries}
    
    added = 0
    for country_name in MISSING_COUNTRIES:
        if country_name not in existing_names:
            new_country = Country(
                name_ar=country_name,
                enabled=True
            )
            db.add(new_country)
            print(f"  ✅ Added country: {country_name}")
            added += 1
    
    if added > 0:
        db.commit()
        print(f"\n✅ Added {added} new countries")
    else:
        print("\n✅ All countries already exist")
    
    return added

def main():
    db = SessionLocal()
    
    print("="*80)
    print("ADDING ARABIC & GULF RSS FEEDS")
    print("="*80)
    print()
    
    try:
        # Step 1: Add missing countries
        print("STEP 1: Checking countries...")
        print("-" * 80)
        add_missing_countries(db)
        
        # Reload countries
        countries_dict = {c.name_ar: c for c in db.query(Country).all()}
        
        print()
        print("="*80)
        print("STEP 2: Adding sources...")
        print("="*80)
        print()
        
        # Get all existing sources to check for duplicates
        existing_sources = db.query(Source).all()
        existing_urls = {s.url.lower().strip() for s in existing_sources}
        
        print(f"📊 Current sources in database: {len(existing_urls)}")
        print()
        
        added_count = 0
        skipped_count = 0
        missing_countries = set()
        
        for country_name, feeds in ARABIC_FEEDS.items():
            # Check if country exists
            country = countries_dict.get(country_name)
            
            if not country:
                missing_countries.add(country_name)
                print(f"⚠️  {country_name}: Country not in database - skipping {len(feeds)} feeds")
                skipped_count += len(feeds)
                continue
            
            print(f"\n🌍 {country_name}:")
            print("-" * 60)
            
            for url, name in feeds:
                url_normalized = url.lower().strip()
                
                # Check if URL already exists
                if url_normalized in existing_urls:
                    print(f"  ⏭️  SKIP: {name}")
                    print(f"      (Already exists)")
                    skipped_count += 1
                    continue
                
                # Add new source
                new_source = Source(
                    name=name,
                    url=url,
                    country_id=country.id,
                    country_name=country_name,
                    enabled=True
                )
                
                db.add(new_source)
                existing_urls.add(url_normalized)  # Add to set to avoid duplicates in same batch
                
                print(f"  ✅ ADDED: {name}")
                print(f"      URL: {url}")
                added_count += 1
        
        # Commit all changes
        db.commit()
        
        print()
        print("="*80)
        print("SUMMARY")
        print("="*80)
        print(f"✅ Added: {added_count} new sources")
        print(f"⏭️  Skipped: {skipped_count} existing sources")
        
        if missing_countries:
            print(f"\n⚠️  Missing countries:")
            for country in sorted(missing_countries):
                print(f"   - {country}")
        
        # Final count
        total_sources = db.query(Source).count()
        total_countries = db.query(Country).count()
        
        print()
        print("="*80)
        print(f"📊 TOTAL DATABASE STATS:")
        print(f"   Countries: {total_countries}")
        print(f"   Sources: {total_sources}")
        print("="*80)
        print("✅ DONE!")
        print("="*80)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    main()
