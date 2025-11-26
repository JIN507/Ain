"""
Seed database with verified RSS feeds
"""
from models import init_db, get_db, Country, Source
from sqlalchemy.orm import Session

# Verified RSS feeds by country with reliability ratings
# reliability: "high" = consistently works, "medium" = may have SSL/403, "low" = often empty/unstable
VERIFIED_FEEDS = {
    "السعودية": [
        # Saudi feeds can be restrictive; use regional alternatives
        {"name": "عكاظ (عام)", "url": "https://www.okaz.com.sa/rssFeed/0", "reliability": "high", "enabled": True},
        {"name": "CNN بالعربية", "url": "https://arabic.cnn.com/api/v1/rss/rss.xml", "reliability": "high", "enabled": True},
        {"name": "Arab News", "url": "https://www.arabnews.com/rss.xml", "reliability": "high", "enabled": True},
        {"name": "Asharq Al-Awsat (EN)", "url": "https://aawsat.com/feed", "reliability": "medium", "enabled": True},
    ],
    "أمريكا": [
        {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml", "reliability": "high", "enabled": True},
        {"name": "Reuters (Top)", "url": "https://feeds.reuters.com/reuters/topNews", "reliability": "medium", "enabled": True},
        {"name": "The New York Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "reliability": "high", "enabled": True},
        {"name": "The Washington Post", "url": "https://feeds.washingtonpost.com/rss/world", "reliability": "high", "enabled": True},
        {"name": "The Wall Street Journal", "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml", "reliability": "high", "enabled": True},
        {"name": "Foreign Policy", "url": "https://foreignpolicy.com/feed/", "reliability": "high", "enabled": True},
        {"name": "Forbes (Business)", "url": "https://www.forbes.com/business/feed/", "reliability": "high", "enabled": True},
        {"name": "ProPublica", "url": "https://www.propublica.org/feeds/propublica/main", "reliability": "high", "enabled": True},
        {"name": "Reveal (CIR)", "url": "https://revealnews.org/feed/", "reliability": "high", "enabled": True},
        {"name": "Center for Public Integrity", "url": "https://publicintegrity.org/feed/", "reliability": "high", "enabled": True},
        {"name": "The Intercept", "url": "https://theintercept.com/feed/", "reliability": "high", "enabled": True},
    ],
    "بريطانيا": [
        {"name": "BBC العربية", "url": "https://www.bbc.com/arabic/index.xml", "reliability": "high", "enabled": True},
        {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "reliability": "high", "enabled": True},
        {"name": "The Guardian (World)", "url": "https://www.theguardian.com/world/rss", "reliability": "high", "enabled": True},
        {"name": "Financial Times (Home)", "url": "https://www.ft.com/rss/home", "reliability": "medium", "enabled": True},
    ],
    "روسيا": [
        {"name": "RT Arabic", "url": "https://arabic.rt.com/rss/", "reliability": "high", "enabled": True},
        {"name": "Sputnik", "url": "https://sputniknews.com/export/rss2/archive/index.xml", "reliability": "high", "enabled": True},
    ],
    "الصين": [
        {"name": "China Daily (World)", "url": "https://www.chinadaily.com.cn/rss/world_rss.xml", "reliability": "high", "enabled": True},
        {"name": "Xinhua Arabic", "url": "https://arabic.news.cn/rss.xml", "reliability": "low", "enabled": False},
        {"name": "SCMP (China)", "url": "https://www.scmp.com/rss/91/feed", "reliability": "high", "enabled": True},
    ],
    "قطر": [
        {"name": "الجزيرة - عربي (عام)", "url": "https://www.aljazeera.com/xml/rss/all.xml", "reliability": "high", "enabled": True},
        {"name": "الجزيرة - عربي (Net)", "url": "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9", "reliability": "high", "enabled": True},
    ],
    "مصر": [
        {"name": "اليوم السابع - أخبار", "url": "https://www.youm7.com/rss/SectionRss?SectionID=65", "reliability": "high", "enabled": True},
        {"name": "الأهرام", "url": "http://gate.ahram.org.eg/RSS/News.aspx", "reliability": "medium", "enabled": True},
    ],
    "تركيا": [
        {"name": "الأناضول", "url": "https://www.aa.com.tr/ar/rss/default?cat=home", "reliability": "low", "enabled": False},
        {"name": "TRT Arabic", "url": "https://www.trt.net.tr/arabic/rss", "reliability": "medium", "enabled": True},
    ],
    "إيران": [
        {"name": "تسنيم", "url": "https://ar.tasnimnews.com/rss/feed", "reliability": "medium", "enabled": True},
    ],
    "الإمارات": [
        {"name": "The National", "url": "https://www.thenationalnews.com/rss/", "reliability": "low", "enabled": False},
        {"name": "Gulf News", "url": "https://gulfnews.com/rss", "reliability": "low", "enabled": False},
    ],
    "ألمانيا": [
        {"name": "DW English (All)", "url": "https://rss.dw.com/xml/rss-en-all", "reliability": "high", "enabled": True},
        {"name": "DW Arabic", "url": "https://rss.dw.com/xml/rss-ara-all", "reliability": "medium", "enabled": True},
        {"name": "Der Spiegel International", "url": "https://www.spiegel.de/international/index.rss", "reliability": "high", "enabled": True},
    ],
    "فرنسا": [
        {"name": "France 24 Arabic", "url": "https://www.france24.com/ar/rss", "reliability": "high", "enabled": True},
        {"name": "France 24 English", "url": "https://www.france24.com/en/rss", "reliability": "high", "enabled": True},
        {"name": "Le Monde (Front Page)", "url": "https://www.lemonde.fr/rss/une.xml", "reliability": "high", "enabled": True},
    ],
    "المغرب": [
        {"name": "Morocco World News", "url": "https://www.moroccoworldnews.com/feed/", "reliability": "high", "enabled": True},
    ],
    "الهند": [
        {"name": "The Hindu", "url": "https://www.thehindu.com/feeder/default.rss", "reliability": "high", "enabled": True},
    ],
    "اليابان": [
        {"name": "Nikkei Asia", "url": "https://asia.nikkei.com/rss", "reliability": "medium", "enabled": True},
        {"name": "The Japan News (Yomiuri)", "url": "https://japannews.yomiuri.co.jp/feed/", "reliability": "high", "enabled": True},
    ],
    "سنغافورة": [
        {"name": "The Straits Times (World)", "url": "https://www.straitstimes.com/news/world/rss.xml", "reliability": "high", "enabled": True},
    ],
    "كوريا الجنوبية": [
        {"name": "Yonhap (EN)", "url": "https://en.yna.co.kr/feed/rss", "reliability": "high", "enabled": True},
    ],
    "هولندا": [
        {"name": "Bellingcat", "url": "https://www.bellingcat.com/feed/", "reliability": "high", "enabled": True},
    ],
    "دولي": [
        {"name": "Eurasia Review", "url": "https://www.eurasiareview.com/feed/", "reliability": "high", "enabled": True},
        {"name": "ICIJ", "url": "https://www.icij.org/feed/", "reliability": "high", "enabled": True},
        {"name": "OCCRP Daily", "url": "https://www.occrp.org/en/daily/rss", "reliability": "high", "enabled": True},
        {"name": "POLITICO (Politics)", "url": "https://www.politico.com/rss/politics-news.xml", "reliability": "high", "enabled": True},
    ],
}

def seed_database():
    """Populate database with initial countries and sources"""
    print("🌱 Seeding database...")
    
    # Initialize DB
    init_db()
    db = get_db()
    
    try:
        # Clear existing data
        db.query(Source).delete()
        db.query(Country).delete()
        db.commit()
        
        country_id = 1
        source_count = 0
        
        for country_name, feeds in VERIFIED_FEEDS.items():
            # Add country
            country = Country(
                id=country_id,
                name_ar=country_name,
                enabled=True
            )
            db.add(country)
            
            # Add sources for this country
            for feed in feeds:
                source = Source(
                    country_id=country_id,
                    country_name=country_name,
                    name=feed['name'],
                    url=feed['url'],
                    enabled=feed.get('enabled', True)  # Respect enabled flag from VERIFIED_FEEDS
                )
                db.add(source)
                source_count += 1
            
            country_id += 1
        
        db.commit()
        
        print(f"✅ Added {len(VERIFIED_FEEDS)} countries")
        print(f"✅ Added {source_count} RSS sources")
        print("🎉 Database seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding database: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
