"""
Multilingual Monitoring Service
Fetches RSS feeds and matches articles using expanded multilingual keywords
"""
import feedparser
from datetime import datetime
from multilingual_matcher import match_article_against_keywords, detect_article_language
from translation_cache import translate_article_to_arabic
from arabic_utils import extract_text_for_matching
import re
import socket
import urllib.request
import threading

# Set global timeout for all HTTP requests (10 seconds)
socket.setdefaulttimeout(10)


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


def fetch_with_timeout(func, args=(), kwargs=None, timeout=10):
    """
    Execute a function with a hard timeout using threading
    
    Args:
        func: Function to execute
        args: Function arguments
        kwargs: Function keyword arguments
        timeout: Maximum seconds to wait
        
    Returns:
        Function result or None on timeout
    """
    if kwargs is None:
        kwargs = {}
    
    result = [None]
    exception = [None]
    
    def worker():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        # Thread is still running - timeout occurred
        raise TimeoutError(f"Operation timed out after {timeout}s")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


def fetch_feed_entries(source_url, timeout=10):
    """
    Fetch entries from an RSS feed with HARD timeout protection
    
    Args:
        source_url: URL of the RSS feed
        timeout: Maximum seconds to wait (default 10)
        
    Returns:
        List of feed entries or empty list on error
    """
    try:
        # Use threading-based timeout for GUARANTEED timeout
        def parse_feed():
            return feedparser.parse(source_url)
        
        feed = fetch_with_timeout(parse_feed, timeout=timeout)
        
        # Check for parsing issues
        if feed.bozo:
            if hasattr(feed, 'bozo_exception'):
                error_msg = str(feed.bozo_exception)
                print(f"      ⚠️ Feed parsing warning: {error_msg[:80]}")
        
        # Return entries if available
        if hasattr(feed, 'entries') and feed.entries:
            return feed.entries
        else:
            print(f"      ⚠️ No entries found")
            return []
            
    except TimeoutError as e:
        print(f"      ⏱️ TIMEOUT: {str(e)} - skipping source")
        return []
    except socket.timeout:
        print(f"      ⏱️ Socket timeout after {timeout}s - skipping")
        return []
    except Exception as e:
        error_msg = str(e)
        print(f"      ❌ Error: {error_msg[:80]}")
        return []


def process_feed_entry(entry):
    """
    Process a feed entry into a standardized article dict
    
    Args:
        entry: Feed entry from feedparser
        
    Returns:
        Article dict with title, summary, url, published_at
    """
    # Get title
    title = entry.get('title', '').strip()
    if not title:
        return None
    
    # Get summary/description
    summary = entry.get('summary', '') or entry.get('description', '')
    summary = extract_text_for_matching(summary)
    
    # Get URL
    url = entry.get('link', '')
    if not url:
        return None
    
    # Get published date
    published_at = None
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            published_at = datetime(*entry.published_parsed[:6])
        except:
            pass
    
    return {
        'title': title,
        'summary': summary,
        'url': url,
        'published_at': published_at
    }


def fetch_and_match_multilingual(sources, keyword_expansions, max_per_source=20):
    """
    Fetch feeds from sources and match against expanded multilingual keywords
    
    Args:
        sources: List of source dicts with 'name', 'url', 'country_name'
        keyword_expansions: List of keyword expansion dicts
        max_per_source: Maximum articles to process per source
        
    Returns:
        List of (article, source, matched_keywords) tuples
    """
    all_matches = []
    
    print(f"\n🔍 Starting multilingual monitoring...")
    print(f"   Sources: {len(sources)}")
    print(f"   Keyword expansions: {len(keyword_expansions)}")
    print(f"   Timeout: 10s per source")
    print()
    
    total_sources = len(sources)
    success_count = 0
    timeout_count = 0
    error_count = 0
    
    for idx, source in enumerate(sources, 1):
        print(f"📡 [{idx}/{total_sources}] Fetching: {source['name']} ({source['country_name']})")
        print(f"   URL: {source['url']}")
        
        # Fetch feed entries with timeout protection
        try:
            entries = fetch_feed_entries(source['url'], timeout=10)
        except Exception as e:
            print(f"   ❌ CRITICAL ERROR: {str(e)[:80]}")
            print(f"   ⏭️  Skipping to next source...")
            error_count += 1
            print()
            continue
        
        if not entries:
            # Already logged in fetch_feed_entries
            timeout_count += 1
            print(f"   ⏭️  Moving to next source...")
            print()
            continue
        
        success_count += 1
        print(f"   ✅ {len(entries)} entries retrieved")
        
        # Process each entry
        matched_count = 0
        for entry in entries[:max_per_source]:
            article = process_feed_entry(entry)
            if not article:
                continue
            
            # Match against all expanded keywords (pass source name for debug logging)
            matches = match_article_against_keywords(article, keyword_expansions, source_name=source.get('name', ''))
            
            if matches:
                matched_count += 1
                all_matches.append((article, source, matches))
                
                # Log match
                matched_keywords = [m['keyword_ar'] for m in matches]
                print(f"   ✅ MATCH: {article['title'][:60]}...")
                print(f"      Keywords: {', '.join(matched_keywords)}")
                print(f"      Languages: {[m['matched_lang'] for m in matches]}")
        
        print(f"   📊 {matched_count} matches from {len(entries[:max_per_source])} articles")
        print()
    
    # Final summary
    print("=" * 80)
    print("📊 MONITORING SUMMARY")
    print("=" * 80)
    print(f"   Total sources: {total_sources}")
    print(f"   ✅ Success: {success_count} ({success_count*100//total_sources if total_sources else 0}%)")
    print(f"   ⏱️  Timeout/Empty: {timeout_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   🎯 Total matches: {len(all_matches)}")
    print("=" * 80)
    
    return all_matches


def save_matched_articles(db, matches):
    """
    Save matched articles to database with Arabic translations
    
    Args:
        db: Database session
        matches: List of (article, source, matched_keywords) tuples
        
    Returns:
        List of saved article IDs
    """
    from models import Article
    import json
    
    saved_ids = []
    
    print(f"\n💾 Saving {len(matches)} matched articles...")
    print()
    
    for article, source, matched_keywords in matches:
        # Check for duplicates (by URL only - matches database UNIQUE constraint)
        existing = db.query(Article).filter(
            Article.url == article['url']
        ).first()
        
        if existing:
            print(f"   ⏭️  SKIPPED (duplicate): {article['title'][:50]}...")
            continue
        
        print(f"   📝 Processing: {article['title'][:60]}...")
        
        # Detect language
        detected_lang = detect_article_language(article['title'], article['summary'])
        print(f"      🌍 Language: {detected_lang}")
        
        # Translate to Arabic (with caching)
        translation_result = translate_article_to_arabic(
            article['title'],
            article['summary'],
            detected_lang
        )
        
        title_ar = translation_result['title_ar']
        summary_ar = translation_result['summary_ar']
        translation_status = translation_result['overall_status']
        
        print(f"      🔄 Translation: {translation_status}")
        
        # Get primary matched keyword (first one)
        primary_keyword = matched_keywords[0]['keyword_ar']
        
        # Prepare keyword info as JSON
        keywords_info = json.dumps({
            'primary': primary_keyword,
            'all_matched': [m['keyword_ar'] for m in matched_keywords],
            'match_details': matched_keywords
        }, ensure_ascii=False)
        
        # Save to database
        new_article = Article(
            country=source['country_name'],
            source_name=source['name'],
            url=article['url'],
            title_original=article['title'],
            summary_original=article['summary'],
            original_language=detected_lang,
            image_url=article.get('image_url'),
            title_ar=title_ar,
            summary_ar=summary_ar,
            arabic_text=f"{title_ar} {summary_ar}",
            keyword_original=primary_keyword,
            keywords_translations=keywords_info,
            sentiment_label="محايد",  # Default neutral
            sentiment_score=None,
            published_at=article.get('published_at'),
            fetched_at=datetime.utcnow()
        )
        
        db.add(new_article)
        db.commit()
        
        saved_ids.append(new_article.id)
        print(f"      ✅ SAVED (ID: {new_article.id})")
        print()
    
    return saved_ids


# Test function
if __name__ == "__main__":
    print("=" * 80)
    print("MULTILINGUAL MONITORING TEST")
    print("=" * 80)
    
    # Test with a sample source
    test_sources = [
        {
            'name': 'BBC News',
            'url': 'http://feeds.bbci.co.uk/news/rss.xml',
            'country_name': 'بريطانيا'
        }
    ]
    
    test_expansions = [
        {
            'original_ar': 'ترامب',
            'normalized_ar': 'ترامب',
            'translations': {
                'en': 'Trump',
                'fr': 'Trump',
                'es': 'Trump',
                'ru': 'Трамп'
            }
        }
    ]
    
    matches = fetch_and_match_multilingual(test_sources, test_expansions, max_per_source=10)
    print(f"\nFound {len(matches)} matches")
