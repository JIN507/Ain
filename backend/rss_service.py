"""
Production-Grade RSS Feed Fetching Service
Handles SSL issues, retries, DNS problems, and various feed formats
"""
import os
import socket
import time
import json
import certifi
import feedparser
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from utils import normalize_arabic, keyword_matches, parse_datetime, clean_html_content

# Timeouts: (connect, read)
DEFAULT_TIMEOUT = (8, 12)
HARD_TIMEOUT_SEC = 15

# Set global socket timeout to prevent hanging
socket.setdefaulttimeout(10)

# Realistic headers to avoid 403
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, application/xhtml+xml, text/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "ar,en;q=0.9",
    "Connection": "keep-alive",
}

# Force SSL certificates on Windows (fixes SSLCertVerificationError)
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())


class IPv4HttpAdapter(HTTPAdapter):
    """Prefer IPv4 to avoid Windows DNS issues"""
    def init_poolmanager(self, *args, **kwargs):
        from urllib3 import PoolManager
        kwargs.setdefault("socket_options", [])
        kwargs["socket_options"] += [
            (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        ]
        self.poolmanager = PoolManager(*args, **kwargs)


def build_session():
    """Create a requests session with retries and IPv4 preference"""
    s = requests.Session()
    
    # Retry strategy
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"])
    )
    
    adapter = IPv4HttpAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update(HEADERS)
    
    return s


# Global session for connection pooling
SESSION = build_session()


def _parse_with_feedparser(url: str, timeout=10):
    """Parse feed using feedparser with custom headers and timeout"""
    try:
        # Set socket timeout (feedparser doesn't accept timeout param)
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        
        result = feedparser.parse(url, request_headers=HEADERS)
        
        # Restore original timeout
        socket.setdefaulttimeout(old_timeout)
        
        return result
    except socket.timeout:
        # Return empty feed on timeout
        empty_feed = feedparser.FeedParserDict()
        empty_feed.entries = []
        empty_feed.bozo = True
        empty_feed.bozo_exception = Exception(f"Timeout after {timeout}s")
        return empty_feed
    finally:
        # Ensure timeout is restored even on error
        try:
            socket.setdefaulttimeout(old_timeout)
        except:
            pass


def _fallback_xml_parse(text: str, base_link: str = ""):
    """
    Fallback XML parser using BeautifulSoup
    For when feedparser fails but we have valid XML
    """
    try:
        soup = BeautifulSoup(text, "xml")
        items = soup.find_all(["item", "entry"])
        results = []
        
        for it in items:
            # Extract title
            title = ""
            title_tag = it.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # Extract link
            link = ""
            link_tag = it.find("link")
            if link_tag:
                if link_tag.has_attr("href"):
                    link = link_tag["href"]
                else:
                    link = link_tag.get_text(strip=True)
            
            # Extract description/summary
            desc = ""
            for tag_name in ["description", "summary", "content"]:
                tag = it.find(tag_name)
                if tag:
                    desc = tag.get_text(strip=True)
                    break
            
            # Extract published date
            pub = ""
            for tag_name in ["pubDate", "published", "updated"]:
                tag = it.find(tag_name)
                if tag:
                    pub = tag.get_text(strip=True)
                    break
            
            if title:  # Only add if we have at least a title
                results.append({
                    "title": title,
                    "link": link or base_link,
                    "summary": desc,
                    "published": pub
                })
        
        return results
    except Exception as e:
        print(f"⚠️ XML fallback parse error: {e}")
        return []


def fetch_feed(url: str, hard_timeout_sec: int = HARD_TIMEOUT_SEC):
    """
    Robust feed fetcher with comprehensive error handling
    
    Returns:
        dict with:
            - status: "ok"|"empty"|"403"|"404"|"ssl"|"dns"|"timeout"|"error"
            - http_status: HTTP status code or None
            - entries: list of article dicts
            - error: error message or None
    """
    start = time.time()
    http_status = None
    last_err = None
    tried_http_variant = False
    
    def over_time():
        return (time.time() - start) > hard_timeout_sec
    
    # ===== STEP 1: Try feedparser (usually most robust) =====
    try:
        fp = _parse_with_feedparser(url)
        http_status = getattr(fp, "status", None)
        
        # Check for parsing errors
        if getattr(fp, "bozo", 0) and not fp.entries:
            last_err = str(getattr(fp, "bozo_exception", ""))[:300]
        
        # Success - we have entries!
        if fp.entries:
            entries = []
            for e in fp.entries[:50]:  # Limit to 50 most recent
                # Extract image from various possible locations
                image_url = None
                
                # Try media:thumbnail
                if hasattr(e, 'media_thumbnail') and e.media_thumbnail:
                    image_url = e.media_thumbnail[0].get('url', '')
                
                # Try media:content
                elif hasattr(e, 'media_content') and e.media_content:
                    image_url = e.media_content[0].get('url', '')
                
                # Try enclosure (for podcasts/media)
                elif hasattr(e, 'enclosures') and e.enclosures:
                    for enc in e.enclosures:
                        if enc.get('type', '').startswith('image/'):
                            image_url = enc.get('href', '')
                            break
                
                # Try extracting from content
                elif hasattr(e, 'content') and e.content:
                    try:
                        soup = BeautifulSoup(e.content[0].value, 'html.parser')
                        img = soup.find('img')
                        if img and img.get('src'):
                            image_url = img.get('src')
                    except:
                        pass
                
                # Try summary/description for img tags
                if not image_url:
                    summary = e.get("summary", e.get("description", ""))
                    if summary and '<img' in summary:
                        try:
                            soup = BeautifulSoup(summary, 'html.parser')
                            img = soup.find('img')
                            if img and img.get('src'):
                                image_url = img.get('src')
                        except:
                            pass
                
                entries.append({
                    "title": e.get("title", "").strip(),
                    "link": e.get("link", ""),
                    "summary": e.get("summary", e.get("description", "")),
                    "published": e.get("published", e.get("updated", "")),
                    "image_url": image_url
                })
            return {
                "status": "ok",
                "http_status": http_status,
                "entries": entries,
                "error": None
            }
        
        # Special status codes
        if http_status == 404:
            return {
                "status": "404",
                "http_status": 404,
                "entries": [],
                "error": "404 Not Found"
            }
        elif http_status == 403:
            # Will retry with requests below
            pass
            
    except Exception as ex:
        last_err = f"feedparser error: {str(ex)[:200]}"
    
    if over_time():
        return {
            "status": "timeout",
            "http_status": http_status,
            "entries": [],
            "error": f"Hard timeout ({hard_timeout_sec}s)"
        }
    
    # ===== STEP 2: Raw HTTP fetch then XML parse =====
    try:
        r = SESSION.get(url, timeout=DEFAULT_TIMEOUT, verify=True)
        http_status = r.status_code
        
        # Handle 403 - retry with stronger headers
        if r.status_code == 403:
            stronger = dict(HEADERS)
            stronger["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            stronger["Referer"] = url
            r = SESSION.get(url, headers=stronger, timeout=DEFAULT_TIMEOUT, verify=True)
            http_status = r.status_code
        
        # Success - parse the XML
        if r.ok and r.text.strip():
            parsed = _fallback_xml_parse(r.text, base_link=url)
            if parsed:
                return {
                    "status": "ok",
                    "http_status": http_status,
                    "entries": parsed,
                    "error": None
                }
            else:
                return {
                    "status": "empty",
                    "http_status": http_status,
                    "entries": [],
                    "error": "XML parsed but no entries found"
                }
        
        # Error codes
        elif r.status_code == 404:
            return {
                "status": "404",
                "http_status": 404,
                "entries": [],
                "error": "404 Not Found"
            }
        elif r.status_code == 403:
            return {
                "status": "403",
                "http_status": 403,
                "entries": [],
                "error": "403 Forbidden (even with stronger headers)"
            }
        else:
            return {
                "status": "error",
                "http_status": r.status_code,
                "entries": [],
                "error": f"HTTP {r.status_code}"
            }
            
    except requests.exceptions.SSLError as ex:
        # SSL error - try HTTP fallback if it was HTTPS
        last_err = f"SSL error: {str(ex)[:200]}"
        
        if not tried_http_variant and url.startswith("https://"):
            tried_http_variant = True
            http_url = "http://" + url[len("https://"):]
            
            try:
                r = SESSION.get(http_url, timeout=DEFAULT_TIMEOUT)
                if r.ok and r.text.strip():
                    parsed = _fallback_xml_parse(r.text, base_link=http_url)
                    if parsed:
                        return {
                            "status": "ok",
                            "http_status": r.status_code,
                            "entries": parsed,
                            "error": "SSL failed, used HTTP fallback"
                        }
                
                return {
                    "status": "ssl",
                    "http_status": r.status_code,
                    "entries": [],
                    "error": "SSL failed; HTTP fallback returned empty"
                }
            except Exception as ex2:
                return {
                    "status": "ssl",
                    "http_status": None,
                    "entries": [],
                    "error": f"SSL + HTTP fallback error: {str(ex2)[:200]}"
                }
        
        return {
            "status": "ssl",
            "http_status": None,
            "entries": [],
            "error": last_err
        }
        
    except requests.exceptions.ConnectionError as ex:
        # DNS or connection error
        last_err = f"Connection/DNS error: {str(ex)[:200]}"
        return {
            "status": "dns",
            "http_status": None,
            "entries": [],
            "error": last_err
        }
        
    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "http_status": http_status,
            "entries": [],
            "error": f"Timeout after {DEFAULT_TIMEOUT[0]}+{DEFAULT_TIMEOUT[1]}s"
        }
        
    except Exception as ex:
        last_err = f"Unexpected error: {str(ex)[:200]}"
        return {
            "status": "error",
            "http_status": http_status,
            "entries": [],
            "error": last_err
        }
    
    # Fallthrough
    return {
        "status": "empty",
        "http_status": http_status,
        "entries": [],
        "error": last_err or "No entries found"
    }


def match_articles_with_keywords(articles, keywords):
    """
    Filter articles that match at least one keyword
    Uses Arabic normalization and multi-language matching
    
    Args:
        articles: List of article dicts
        keywords: List of keyword dicts with text_ar, text_en, text_fr, etc.
    
    Returns:
        List of (article, keyword) tuples
    """
    matches = []
    
    for article in articles:
        text_to_search = f"{article['title']} {article['summary']}".lower()
        
        for keyword in keywords:
            # Build translations dict from individual columns
            translations = {}
            for lang in ['en', 'fr', 'tr', 'ur', 'zh', 'ru', 'es']:
                trans_key = f'text_{lang}'
                if keyword.get(trans_key):
                    translations[lang] = keyword[trans_key]
            
            # Check if keyword matches (Arabic or any translation)
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
    feed_results = []
    
    for source in sources:
        if not source.get('enabled', True):
            continue
        
        print(f"📡 Fetching: {source['name']} ({source['country_name']})")
        result = fetch_feed(source['url'])
        
        # Store diagnostics
        feed_results.append({
            'source': source,
            'result': result
        })
        
        if result['status'] == 'ok' and result['entries']:
            # Convert to standardized format
            articles = []
            for entry in result['entries']:
                # Clean HTML from summary (remove ads, navigation, social links, etc.)
                summary_raw = entry['summary']
                summary_clean = clean_html_content(summary_raw) if summary_raw else ''
                
                articles.append({
                    'title': entry['title'],
                    'summary': summary_clean,
                    'url': entry['link'],
                    'published_at': parse_datetime(entry['published']) if entry['published'] else None,
                    'image_url': entry.get('image_url')
                })
            
            # Match with keywords
            matches = match_articles_with_keywords(articles, keywords)
            
            # Add source info to each match
            for article, keyword in matches:
                all_matches.append((article, source, keyword))
            
            print(f"   ✅ {len(result['entries'])} entries, {len(matches)} matches")
        else:
            print(f"   ⚠️ {result['status']}: {result['error']}")
        
        # Small delay to avoid hammering servers
        time.sleep(0.5)
    
    print(f"\n📊 Total matches found: {len(all_matches)}")
    return all_matches
