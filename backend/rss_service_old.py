"""
RSS Feed Fetching Service
"""
import feedparser
import requests
from bs4 import BeautifulSoup
from utils import normalize_arabic, keyword_matches, parse_datetime, is_valid_url
import time

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def fetch_rss_feed(url, timeout=10):
    """
    Fetch and parse RSS feed
    
    Args:
        url: RSS feed URL
        timeout: Request timeout in seconds
    
    Returns:
        List of article dicts or empty list on error
    """
    if not is_valid_url(url):
        print(f"❌ Invalid URL: {url}")
        return []
    
    try:
        # Try direct fetch
        response = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=timeout
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code} for {url}")
            return []
        
        # Parse feed
        feed = feedparser.parse(response.content)
        
        if not feed.entries:
            print(f"⚠️ No entries found in {url}")
            return []
        
        articles = []
        for entry in feed.entries[:20]:  # Limit to 20 most recent
            article = parse_entry(entry)
            if article:
                articles.append(article)
        
        print(f"✅ Fetched {len(articles)} articles from {url}")
        return articles
    
    except Exception as e:
        print(f"❌ Error fetching {url}: {str(e)}")
        return []

def parse_entry(entry):
    """
    Parse a single RSS entry into article dict
    """
    try:
        # Extract title
        title = entry.get('title', '').strip()
        if not title:
            return None
        
        # Extract URL
        url = entry.get('link', '').strip()
        if not url or not is_valid_url(url):
            return None
        
        # Extract summary/description
        summary = ''
        if 'summary' in entry:
            summary = entry.summary
        elif 'description' in entry:
            summary = entry.description
        elif 'content' in entry and entry.content:
            summary = entry.content[0].value
        
        # Clean HTML from summary
        if summary:
            soup = BeautifulSoup(summary, 'html.parser')
            summary = soup.get_text().strip()
        
        # Extract published date
        published_at = None
        if 'published' in entry:
            published_at = parse_datetime(entry.published)
        elif 'updated' in entry:
            published_at = parse_datetime(entry.updated)
        
        return {
            'title': title,
            'summary': summary[:500] if summary else '',  # Limit summary length
            'url': url,
            'published_at': published_at
        }
    
    except Exception as e:
        print(f"⚠️ Error parsing entry: {str(e)}")
        return None

def match_articles_with_keywords(articles, keywords):
    """
    Filter articles that match at least one keyword
    
    Args:
        articles: List of article dicts
        keywords: List of keyword dicts with {text_ar, translations}
    
    Returns:
        List of (article, keyword) tuples
    """
    matches = []
    
    for article in articles:
        text_to_search = f"{article['title']} {article['summary']}".lower()
        
        for keyword in keywords:
            # Parse translations (stored as JSON string)
            translations = {}
            if keyword.get('translations'):
                try:
                    import json
                    translations = json.loads(keyword['translations'])
                except:
                    pass
            
            # Check if keyword matches
            if keyword_matches(text_to_search, keyword['text_ar'], translations):
                matches.append((article, keyword))
                break  # Each article matched once
    
    return matches

def fetch_all_feeds(sources, keywords):
    """
    Fetch all RSS feeds and match with keywords
    
    Args:
        sources: List of source dicts
        keywords: List of keyword dicts
    
    Returns:
        List of (article, source, keyword) tuples
    """
    all_matches = []
    
    for source in sources:
        if not source.get('enabled', True):
            continue
        
        print(f"📡 Fetching: {source['name']} ({source['country_name']})")
        articles = fetch_rss_feed(source['url'])
        
        if articles:
            # Match with keywords
            matches = match_articles_with_keywords(articles, keywords)
            
            # Add source info to each match
            for article, keyword in matches:
                all_matches.append((article, source, keyword))
        
        # Small delay to avoid hammering servers
        time.sleep(0.5)
    
    print(f"\n📊 Total matches found: {len(all_matches)}")
    return all_matches
