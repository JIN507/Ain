"""Seed database with verified RSS feeds"""

import json

from models import init_db, get_db, Country, Source
from sqlalchemy.orm import Session

# Small default seed (kept for reference; main bulk seed is loaded in seed_database)
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

        # Use the large JSON seed exported from the local DB. We keep it as raw JSON
        # so that true/false/null are valid and parsed via json.loads.
        VERIFIED_FEEDS = json.loads(r'''{
    "السعودية": [
        {
            "name": "عكاظ",
            "url": "https://www.okaz.com.sa/rssFeed/0",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Asharq Al-Awsat (EN)",
            "url": "https://aawsat.com/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Arab News",
            "url": "https://www.arabnews.com/rss.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Arabiya",
            "url": "https://www.alarabiya.net/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Asharq Al-Awsat English",
            "url": "https://english.aawsat.com/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Watan Saudi",
            "url": "https://www.alwatan.com.sa/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "عكاظ 2",
            "url": "https://www.okaz.com.sa/rssFeed/190",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "المدينة",
            "url": "https://www.al-madina.com/rssFeed/193",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "البلاد",
            "url": "https://albiladdaily.com/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "مكة",
            "url": "https://makkahnewspaper.com/rssFeed/0",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "الجزيرة السعودية",
            "url": "https://www.al-jazirah.com/rss/ln.xml?utm_source=rss-jazirah&utm_medium=rss&utm_campaign=rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Saudi Gazette",
            "url": "https://saudigazette.com.sa/rssFeed/74",
            "reliability": "high",
            "enabled": true
        }
    ],
    "أمريكا": [
        {
            "name": "The New York Times",
            "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Washington Post",
            "url": "https://feeds.washingtonpost.com/rss/world",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Wall Street Journal",
            "url": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Forbes (Business)",
            "url": "https://www.forbes.com/business/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "npr",
            "url": "https://feeds.npr.org/500005/podcast.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Intercept",
            "url": "https://theintercept.com/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "CNN بالعربية",
            "url": "https://arabic.cnn.com/api/v1/rss/rss.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "NBC News",
            "url": "https://feeds.nbcnews.com/nbcnews/public/news",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "NPR News",
            "url": "https://feeds.npr.org/1001/rss.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "CNN",
            "url": "http://rss.cnn.com/rss/edition.rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": " الكونغرس Politico",
            "url": "https://rss.politico.com/congress.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Bloomberg Markets",
            "url": "https://feeds.bloomberg.com/markets/news.rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "CNBC",
            "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "ABC News",
            "url": "https://abcnews.go.com/abcnews/internationalheadlines",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Fox News",
            "url": "https://feeds.foxnews.com/foxnews/latest",
            "reliability": "high",
            "enabled": true
        }
    ],
    "بريطانيا": [
        {
            "name": "BBC العربية",
            "url": "https://www.bbc.com/arabic/index.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "BBC World",
            "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Guardian (World)",
            "url": "https://www.theguardian.com/world/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Financial Times (Home)",
            "url": "https://www.ft.com/rss/home",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "independent",
            "url": "https://www.independent.co.uk/news/uk/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "independent world",
            "url": "https://www.independent.co.uk/news/world/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "BBC News",
            "url": "https://feeds.bbci.co.uk/news/rss.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Telegraph",
            "url": "https://telegraph.co.uk/rss.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Independent",
            "url": "https://independent.co.uk/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Sky News UK",
            "url": "https://feeds.skynews.com/feeds/rss/home.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Sky News World",
            "url": "https://feeds.skynews.com/feeds/rss/world.xml",
            "reliability": "high",
            "enabled": true
        }
    ],
    "روسيا": [
        {
            "name": "RT Arabic",
            "url": "https://arabic.rt.com/rss/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Sputnik",
            "url": "https://sputniknews.com/export/rss2/archive/index.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "RT",
            "url": "https://www.rt.com/rss/",
            "reliability": "high",
            "enabled": true
        }
    ],
    "الصين": [
        {
            "name": "SCMP (China)",
            "url": "https://www.scmp.com/rss/91/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "الحكومة الصينية",
            "url": "https://rsshub.app/gov/zhengce/zuixin",
            "reliability": "high",
            "enabled": true
        }
    ],
    "قطر": [
        {
            "name": "الجزيرة - عربي (عام)",
            "url": "https://www.al-jazirah.com/rss/du.xml?utm_source=rss-jazirah&utm_medium=rss&utm_campaign=rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "الجزيرة - عربي (Net)",
            "url": "https://www.al-jazirah.com/rss/lp.xml?utm_source=rss-jazirah&utm_medium=rss&utm_campaign=rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Jazeera",
            "url": "https://www.aljazeera.com/xml/rss/all.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Doha News",
            "url": "https://dohanews.co/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Doha News",
            "url": "https://www.dohanews.co/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al-Sharq",
            "url": "https://al-sharq.com/rss/latestNews",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Gulf Times",
            "url": "https://www.gulf-times.com/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "مصر": [
        {
            "name": "identity-mag",
            "url": "https://identity-mag.com/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al-Masry Al-Youm",
            "url": "https://www.almasryalyoum.com/rss/rssfeed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "BBC Arabic",
            "url": "https://www.bbc.com/arabic/feed.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Ahram",
            "url": "https://www.ahram.org.eg/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "النفط والغاز ",
            "url": "https://egyptoil-gas.com/news/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "dailynewsegypt",
            "url": "https://www.dailynewsegypt.com/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Egyptian streets",
            "url": "https://egyptianstreets.com/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "CNN Arabic",
            "url": "https://arabic.cnn.com/rss/feed.xml",
            "reliability": "high",
            "enabled": true
        }
    ],
    "تركيا": [
        {
            "name": "الأناضول",
            "url": "https://www.aa.com.tr/tr/teyithatti/rss/news?cat=aktuel",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "nationalturk",
            "url": "https://www.nationalturk.com/en/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "haberler التركي",
            "url": "https://rss.haberler.com/RssNew.aspx",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "ntv داخلي",
            "url": "https://www.ntv.com.tr/turkiye.rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "ntv عالمي",
            "url": "https://www.ntv.com.tr/dunya.rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "إيران": [
        {
            "name": "طهران تايمز",
            "url": "https://www.tehrantimes.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "شبكة إنتخاب",
            "url": "https://www.entekhab.ir/fa/rss/allnews",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Iran news daily",
            "url": "https://irannewsdaily.com/feed/",
            "reliability": "high",
            "enabled": true
        }
    ],
    "الإمارات": [
        {
            "name": "The National",
            "url": "https://www.thenationalnews.com/rss/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Gulf News",
            "url": "https://gulfnews.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Emirates 247",
            "url": "https://emirates247.com/cmlink/rss-feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Emarat Al Youm",
            "url": "https://emaratalyoum.com/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The National News",
            "url": "https://www.thenationalnews.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Arabian Business UAE",
            "url": "https://arabianbusiness.com/gcc/uae/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Arabian Post",
            "url": "https://thearabianpost.com/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Gulf News",
            "url": "https://gulfnews.com/rss/index.html",
            "reliability": "high",
            "enabled": true
        }
    ],
    "ألمانيا": [
        {
            "name": "DW English (All)",
            "url": "https://rss.dw.com/xml/rss-en-all",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "DW Arabic",
            "url": "https://rss.dw.com/xml/rss-ara-all",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Deutsche Welle All",
            "url": "https://rss.dw.com/rdf/rss-en-all",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Deutsche Welle Top",
            "url": "https://rss.dw.com/rdf/rss-en-top",
            "reliability": "high",
            "enabled": true
        }
    ],
    "فرنسا": [
        {
            "name": "France 24 Arabic",
            "url": "https://www.france24.com/ar/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "France 24 English",
            "url": "https://www.france24.com/en/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Le Monde (Front Page)",
            "url": "https://www.lemonde.fr/rss/une.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "diplomatie",
            "url": "https://www.diplomatie.gouv.fr/spip.php?page=backend-fd&lang=en",
            "reliability": "high",
            "enabled": true
        }
    ],
    "المغرب": [
        {
            "name": "Morocco World News",
            "url": "https://www.moroccoworldnews.com/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "TelQuel",
            "url": "https://www.telquel.ma/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Hespress",
            "url": "https://www.hespress.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Massae",
            "url": "https://infosports.news/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Aujourd'hui le Maroc ",
            "url": "https://aujourdhui.ma/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": " Libération",
            "url": "https://www.libe.ma/xml/syndication.rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "الهند": [
        {
            "name": "The Hindu",
            "url": "https://www.thehindu.com/feeder/default.rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "timesofindia",
            "url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Times of India",
            "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "NDTV",
            "url": "http://feeds.feedburner.com/ndtvnews-world-news",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Indian Express",
            "url": "https://indianexpress.com/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Hindu",
            "url": "https://thehindu.com/news/national/?service=rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Business Standard",
            "url": "https://business-standard.com/rss/latest-news.rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "اليابان": [
        {
            "name": "Nikkei Asia",
            "url": "https://asia.nikkei.com/rss/feed/nar",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Japan News (Yomiuri)",
            "url": "https://japannews.yomiuri.co.jp/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "nippon اليابانية",
            "url": "https://www.nippon.com/en/rss-all/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Japan Times",
            "url": "https://japantimes.co.jp/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Asahi Shimbun",
            "url": "https://www.asahi.com/rss/asahi/newsheadlines.rdf",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "NHK News",
            "url": "https://www3.nhk.or.jp/rss/news/cat0010001_0.xml",
            "reliability": "high",
            "enabled": true
        }
    ],
    "سنغافورة": [
        {
            "name": "The Straits Times (World)",
            "url": "https://www.straitstimes.com/news/world/rss.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Straits Times",
            "url": "https://straitstimes.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Business Times SG",
            "url": "https://businesstimes.com.sg/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "كوريا الجنوبية": [
        {
            "name": "Yonhap (EN)",
            "url": "https://en.yna.co.kr/feed/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "هولندا": [
        {
            "name": "Bellingcat",
            "url": "https://www.bellingcat.com/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "NL Times",
            "url": "https://nltimes.nl/rssfeed2",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Dutch News",
            "url": "https://dutchnews.nl/feed",
            "reliability": "high",
            "enabled": true
        }
    ],
    "دولي": [
        {
            "name": "ICIJ",
            "url": "https://www.icij.org/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "OCCRP Daily",
            "url": "https://www.occrp.org/en/daily/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "POLITICO (Politics)",
            "url": "https://www.politico.com/rss/politics-news.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "POLITICO Europe",
            "url": "https://politico.eu/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Russia Today Arabic",
            "url": "https://arabic.rt.com/feeds/news/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The New Arab",
            "url": "https://www.newarab.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Arab Weekly",
            "url": "https://www.thearabweekly.com/feeds",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Arabian Business",
            "url": "https://www.arabianbusiness.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "haaretz إسرائيل",
            "url": "https://www.haaretz.com/srv/haaretz-latest-headlines",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "globes إسرائيل",
            "url": "https://en.globes.co.il/WebService/Rss/RssFeeder.asmx/FeederNode?iID=942",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "maariv إسرائيل",
            "url": "https://www.maariv.co.il/rss/rsschadashot",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "cursorinfo إسرائيل",
            "url": "https://cursorinfo.co.il/feed/",
            "reliability": "high",
            "enabled": true
        }
    ],
    "كندا": [
        {
            "name": "Global News",
            "url": "https://globalnews.ca/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "CTV News",
            "url": "https://www.ctvnews.ca/rss/ctvnews-ca-top-stories-public-rss-1.822009",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "CBC News",
            "url": "https://www.cbc.ca/cmlink/rss-topstories",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "National Post",
            "url": "https://nationalpost.com/feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Financial Post",
            "url": "https://financialpost.com/feed/",
            "reliability": "high",
            "enabled": true
        }
    ],
    "المكسيك": [
        {
            "name": "Excélsior",
            "url": "https://excelsior.com.mx/rss.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Reforma",
            "url": "https://reforma.com/rss/portada.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "SinEmbargo",
            "url": "https://sinembargo.mx/feed",
            "reliability": "high",
            "enabled": true
        }
    ],
    "إسبانيا": [
        {
            "name": "El Mundo",
            "url": "https://e00-elmundo.uecdn.es/rss/portada.xml",
            "reliability": "high",
            "enabled": true
        }
    ],
    "إيطاليا": [
        {
            "name": "Corriere della Sera",
            "url": "https://corriere.it/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "La Repubblica",
            "url": "https://repubblica.it/rss/",
            "reliability": "high",
            "enabled": true
        }
    ],
    "جنوب أفريقيا": [
        {
            "name": "Mail & Guardian",
            "url": "https://mg.co.za/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Daily Maverick",
            "url": "https://dailymaverick.co.za/dmrss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "نيجيريا": [
        {
            "name": "Vanguard News",
            "url": "https://vanguardngr.com/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Guardian Nigeria",
            "url": "https://guardian.ng/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Premium Times",
            "url": "https://premiumtimesng.com/feed",
            "reliability": "high",
            "enabled": true
        }
    ],
    "كينيا": [
        {
            "name": "Daily Nation",
            "url": "https://nation.africa/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Standard Kenya",
            "url": "https://standardmedia.co.ke/rss/headlines.php",
            "reliability": "high",
            "enabled": true
        }
    ],
    "تايلاند": [
        {
            "name": "Bangkok Post",
            "url": "https://bangkokpost.com/rss/data/top.xml",
            "reliability": "high",
            "enabled": true
        }
    ],
    "ماليزيا": [
        {
            "name": "Malaysiakini",
            "url": "https://malaysiakini.com/rss/en/news.xml",
            "reliability": "high",
            "enabled": true
        }
    ],
    "إندونيسيا": [
        {
            "name": "ANTARA News",
            "url": "https://en.antaranews.com/rss/news.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "VIVA.co.id",
            "url": "https://viva.co.id/get/all",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Tribun News",
            "url": "https://tribunnews.com/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "فيتنام": [
        {
            "name": "Tuổi Trẻ Online",
            "url": "https://tuoitre.vn/rss/tin-moi-nhat.rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "VnExpress",
            "url": "https://vnexpress.net/rss/news.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Vietnam News",
            "url": "https://vietnamnews.vn/rss/news.rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "الفلبين": [
        {
            "name": "Inquirer.net",
            "url": "https://inquirer.net/fullfeed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Rappler",
            "url": "https://rappler.com/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Philippine Star",
            "url": "https://philstar.com/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "باكستان": [
        {
            "name": "Dawn",
            "url": "https://dawn.com/feeds/home",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Express Tribune",
            "url": "https://tribune.com.pk/feed",
            "reliability": "high",
            "enabled": true
        }
    ],
    "أستراليا": [
        {
            "name": "ABC News AU",
            "url": "https://abc.net.au/news/feed/2942460/rss.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "News.com.au",
            "url": "https://news.com.au/content-feeds/latest-news-feed/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "9News",
            "url": "https://9news.com.au/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Sydney Morning Herald",
            "url": "https://smh.com.au/rss/feed.xml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Age",
            "url": "https://theage.com.au/rss/feed.xml",
            "reliability": "high",
            "enabled": true
        }
    ],
    "البرازيل": [
        {
            "name": "G1 Globo",
            "url": "https://g1.globo.com/rss/feeds/",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Folha de São Paulo",
            "url": "https://folha.uol.com.br/rss/index.shtml",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "O Estado de São Paulo",
            "url": "https://estadao.com.br/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "الأرجنتين": [
        {
            "name": "La Nación",
            "url": "https://lanacion.com.ar/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Clarín",
            "url": "https://clarin.com/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "كولومبيا": [
        {
            "name": "El Tiempo",
            "url": "https://eltiempo.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Semana",
            "url": "https://semana.com/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "بيرو": [
        {
            "name": "El Comercio Peru",
            "url": "https://elcomercio.pe/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "تشيلي": [
        {
            "name": "El Mercurio",
            "url": "https://elmercurio.cl/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "La Tercera",
            "url": "https://latercera.com/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "الكويت": [
        {
            "name": "Arab Times Kuwait",
            "url": "https://www.arabtimes.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Qabas",
            "url": "https://www.alqabas.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Kuwait News Agency",
            "url": "https://www.kuna.net.kw/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "البحرين": [
        {
            "name": "Bahrain Tribune",
            "url": "https://www.bahraintribune.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Ayam Bahrain",
            "url": "https://www.alayam.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Bahrain News Agency",
            "url": "https://www.bna.bh/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "عُمان": [
        {
            "name": "Times of Oman",
            "url": "https://www.timesofoman.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Oman Observer",
            "url": "https://www.omanobserver.om/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Watan Oman",
            "url": "https://www.alwatan.om/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Oman News Agency",
            "url": "https://www.omannews.gov.om/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "لبنان": [
        {
            "name": "An-Nahar",
            "url": "https://www.annahar.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "The Daily Star Lebanon",
            "url": "https://www.thedailystarnews.com/feed",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Liwa",
            "url": "https://www.aliwaa.com.lb/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "El Nashra",
            "url": "https://www.elnashra.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Akhbar Lebanon",
            "url": "https://www.alakhbar.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Lebanese Press Agency",
            "url": "https://www.lpagency.net/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "سوريا": [
        {
            "name": "Syrian Arab News Agency",
            "url": "https://www.sana.sy/en/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "الأردن": [
        {
            "name": "Jordan Times",
            "url": "https://jordantimes.com/rss-feed/47",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Al Ghad",
            "url": "https://www.alghad.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Petra News Agency",
            "url": "https://petra.gov.jo/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Jordan Times محلي",
            "url": "https://jordantimes.com/rss-feed/45",
            "reliability": "high",
            "enabled": true
        }
    ],
    "تونس": [
        {
            "name": "Assabah",
            "url": "https://www.assabah.tn/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "AfrikInfo Tunisia",
            "url": "https://www.afriquinfos.com/feeds/tunisie.rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Business News Tunisia",
            "url": "https://www.businessnews.com.tn/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Tunisian Press Agency",
            "url": "https://www.tap.info.tn/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "الجزائر": [
        {
            "name": "El Khabar",
            "url": "https://www.elkhabar.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Ennahar Online",
            "url": "https://www.ennaharonline.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Algerian Press Service",
            "url": "https://www.aps.dz/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Radio Algérie",
            "url": "https://www.radioalgerie.dz/fr/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "العراق": [
        {
            "name": "Asaas Press",
            "url": "https://www.asaaspress.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Iraqi News",
            "url": "https://www.iraqinews.com/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Iraqi News Agency",
            "url": "https://www.ina.iq/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "فلسطين": [
        {
            "name": "WAFA News Agency",
            "url": "https://www.wafa.ps/rss",
            "reliability": "high",
            "enabled": true
        },
        {
            "name": "Ma'an News Agency",
            "url": "https://www.maan-ctr.org/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "اليمن": [
        {
            "name": "Sputnik Arabic Yemen",
            "url": "https://www.sputnikarabic.ae/yemen/rss",
            "reliability": "high",
            "enabled": true
        }
    ],
    "السودان": [
        {
            "name": "Sudan Tribune",
            "url": "https://www.sudanTribune.com/rss",
            "reliability": "high",
            "enabled": true
        }
    ]
}
''')

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
