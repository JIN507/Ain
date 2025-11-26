"""
Add verified RSS feeds from around the world
Checks for duplicates before adding
"""
from models import SessionLocal, Country, Source

# Global RSS feeds organized by country
GLOBAL_FEEDS = {
    # North America
    'أمريكا': [
        ('https://feeds.nbcnews.com/nbcnews/public/news', 'NBC News'),
        ('https://feeds.npr.org/1001/rss.xml', 'NPR News'),
        ('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'The New York Times'),
        ('http://rss.cnn.com/rss/edition.rss', 'CNN'),
        ('http://feeds.reuters.com/Reuters/worldNews', 'Reuters World'),
        ('https://feeds.washingtonpost.com/rss/world', 'Washington Post'),
        ('https://www.politico.com/rss/politics08.xml', 'Politico'),
        ('https://feeds.bloomberg.com/markets/news.rss', 'Bloomberg Markets'),
        ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'),
        ('https://feeds.abcnews.go.com/abcnews/topstories', 'ABC News'),
        ('https://feeds.foxnews.com/foxnews/latest', 'Fox News'),
        ('https://apnews.com/rss', 'Associated Press'),
    ],
    'كندا': [
        ('https://globalnews.ca/feed/', 'Global News'),
        ('https://www.ctvnews.ca/rss/ctvnews-ca-top-stories-public-rss-1.822009', 'CTV News'),
        ('https://www.cbc.ca/cmlink/rss-topstories', 'CBC News'),
        ('https://nationalpost.com/feed/', 'National Post'),
        ('https://financialpost.com/feed/', 'Financial Post'),
    ],
    'المكسيك': [
        ('https://excelsior.com.mx/rss.xml', 'Excélsior'),
        ('https://reforma.com/rss/portada.xml', 'Reforma'),
        ('https://sinembargo.mx/feed', 'SinEmbargo'),
    ],
    
    # Europe
    'بريطانيا': [
        ('https://feeds.bbci.co.uk/news/rss.xml', 'BBC News'),
        ('https://www.theguardian.com/world/rss', 'The Guardian'),
        ('https://telegraph.co.uk/rss.xml', 'The Telegraph'),
        ('https://independent.co.uk/rss', 'The Independent'),
        ('https://feeds.skynews.com/feeds/rss/home.xml', 'Sky News UK'),
        ('https://feeds.bbci.co.uk/news/world/rss.xml', 'BBC World'),
    ],
    'ألمانيا': [
        ('https://rss.dw.com/rdf/rss-en-all', 'Deutsche Welle All'),
        ('https://rss.dw.com/rdf/rss-en-top', 'Deutsche Welle Top'),
    ],
    'فرنسا': [
        ('https://feeds.elpais.com/mrss-s/pages/1/', 'EL PAÍS English'),
        ('https://lemonde.fr/rss/', 'Le Monde'),
    ],
    'إسبانيا': [
        ('https://feeds.elpais.com/mrss-s/pages/1/', 'EL PAÍS'),
        ('https://e00-elmundo.uecdn.es/rss/portada.xml', 'El Mundo'),
    ],
    'إيطاليا': [
        ('https://corriere.it/rss', 'Corriere della Sera'),
        ('https://repubblica.it/rss/', 'La Repubblica'),
    ],
    'هولندا': [
        ('https://nltimes.nl/rssfeed2', 'NL Times'),
        ('https://dutchnews.nl/feed', 'Dutch News'),
    ],
    
    # Middle East
    'قطر': [
        ('https://www.aljazeera.com/xml/rss/all.xml', 'Al Jazeera'),
        ('https://dohanews.co/feed', 'Doha News'),
    ],
    'السعودية': [
        ('https://skynewsarabia.com/feed.xml', 'Sky News Arabia'),
    ],
    
    # Africa
    'جنوب أفريقيا': [
        ('https://mg.co.za/feed', 'Mail & Guardian'),
        ('https://dailymaverick.co.za/dmrss', 'Daily Maverick'),
    ],
    'نيجيريا': [
        ('https://vanguardngr.com/feed', 'Vanguard News'),
        ('https://guardian.ng/feed', 'Guardian Nigeria'),
        ('https://premiumtimesng.com/feed', 'Premium Times'),
    ],
    'كينيا': [
        ('https://nation.africa/rss', 'Daily Nation'),
        ('https://standardmedia.co.ke/rss/headlines.php', 'The Standard Kenya'),
    ],
    
    # Asia-Pacific
    'الهند': [
        ('https://timesofindia.indiatimes.com/rssfeedstopstories.cms', 'Times of India'),
        ('http://feeds.feedburner.com/ndtvnews-world-news', 'NDTV'),
        ('https://indianexpress.com/feed', 'Indian Express'),
        ('https://thehindu.com/news/national/?service=rss', 'The Hindu'),
        ('https://business-standard.com/rss/latest-news.rss', 'Business Standard'),
    ],
    'اليابان': [
        ('https://japantimes.co.jp/feed', 'The Japan Times'),
        ('https://rss.asahi.com/rss/asahi/newsheadlines.xml', 'Asahi Shimbun'),
        ('https://www3.nhk.or.jp/rss/news/cat0010001_0.xml', 'NHK News'),
    ],
    'تايلاند': [
        ('https://bangkokpost.com/rss/data/top.xml', 'Bangkok Post'),
    ],
    'ماليزيا': [
        ('https://malaysiakini.com/rss/en/news.xml', 'Malaysiakini'),
    ],
    'سنغافورة': [
        ('https://straitstimes.com/rss', 'The Straits Times'),
        ('https://businesstimes.com.sg/rss', 'Business Times SG'),
    ],
    'إندونيسيا': [
        ('https://en.antaranews.com/rss/news.xml', 'ANTARA News'),
        ('https://viva.co.id/get/all', 'VIVA.co.id'),
        ('https://tribunnews.com/rss', 'Tribun News'),
    ],
    'فيتنام': [
        ('https://tuoitre.vn/rss/tin-moi-nhat.rss', 'Tuổi Trẻ Online'),
        ('https://vnexpress.net/rss/news.xml', 'VnExpress'),
        ('https://vietnamnews.vn/rss/news.rss', 'Vietnam News'),
    ],
    'الفلبين': [
        ('https://inquirer.net/fullfeed', 'Inquirer.net'),
        ('https://rappler.com/feed', 'Rappler'),
        ('https://philstar.com/rss', 'Philippine Star'),
    ],
    'باكستان': [
        ('https://dawn.com/feeds/home', 'Dawn'),
        ('https://tribune.com.pk/feed', 'Express Tribune'),
    ],
    'أستراليا': [
        ('https://abc.net.au/news/feed/2942460/rss.xml', 'ABC News AU'),
        ('https://news.com.au/content-feeds/latest-news-feed/', 'News.com.au'),
        ('https://9news.com.au/rss', '9News'),
        ('https://smh.com.au/rss/feed.xml', 'Sydney Morning Herald'),
        ('https://theage.com.au/rss/feed.xml', 'The Age'),
    ],
    
    # South America
    'البرازيل': [
        ('https://g1.globo.com/rss/feeds/', 'G1 Globo'),
        ('https://folha.uol.com.br/rss/index.shtml', 'Folha de São Paulo'),
        ('https://estadao.com.br/rss', 'O Estado de São Paulo'),
    ],
    'الأرجنتين': [
        ('https://lanacion.com.ar/rss', 'La Nación'),
        ('https://clarin.com/rss', 'Clarín'),
    ],
    'كولومبيا': [
        ('https://eltiempo.com/rss', 'El Tiempo'),
        ('https://semana.com/rss', 'Semana'),
    ],
    'بيرو': [
        ('https://elcomercio.pe/rss', 'El Comercio Peru'),
    ],
    'تشيلي': [
        ('https://elmercurio.cl/rss', 'El Mercurio'),
        ('https://latercera.com/rss', 'La Tercera'),
    ],
    
    # Global
    'دولي': [
        ('https://politico.eu/feed', 'POLITICO Europe'),
    ],
}

def main():
    db = SessionLocal()
    
    print("="*80)
    print("ADDING GLOBAL RSS FEEDS")
    print("="*80)
    print()
    
    try:
        # Get all existing sources to check for duplicates
        existing_sources = db.query(Source).all()
        existing_urls = {s.url.lower().strip() for s in existing_sources}
        
        print(f"📊 Current sources in database: {len(existing_urls)}")
        print()
        
        added_count = 0
        skipped_count = 0
        missing_countries = set()
        
        for country_name, feeds in GLOBAL_FEEDS.items():
            # Check if country exists
            country = db.query(Country).filter(Country.name_ar == country_name).first()
            
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
                    print(f"      (Already exists: {url})")
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
            print(f"\n⚠️  Missing countries (need to be added first):")
            for country in sorted(missing_countries):
                print(f"   - {country}")
            print(f"\n💡 To add these countries, go to 'الدول' tab in the app")
        
        print()
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
