"""
Async RSS Fetcher - High Performance Feed Fetching
Fetches 200+ RSS feeds concurrently with connection pooling, retries, and adaptive timeouts
"""
import asyncio
import aiohttp
import feedparser
import hashlib
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncRSSFetcher:
    """
    High-performance async RSS fetcher with:
    - Concurrent fetching (all 200+ sources in parallel)
    - Connection pooling per domain
    - Adaptive timeouts (fast sites: 5s, slow: 15s)
    - Exponential backoff retry
    - ETag/Last-Modified caching
    - Duplicate detection via hashing
    """
    
    def __init__(
        self,
        max_concurrent=50,
        default_timeout=10,
        max_retries=2,
        enable_cache=True
    ):
        """
        Initialize async fetcher
        
        Args:
            max_concurrent: Max concurrent connections (default: 50)
            default_timeout: Default timeout in seconds (default: 10)
            max_retries: Max retry attempts (default: 2)
            enable_cache: Enable ETag/Last-Modified caching (default: True)
        """
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.enable_cache = enable_cache
        
        # Cache for ETags and Last-Modified headers
        self.cache = {} if enable_cache else None
        
        # Performance metrics
        self.metrics = {
            'total_sources': 0,
            'successful': 0,
            'failed': 0,
            'timeout': 0,
            'cached': 0,
            'duplicates': 0,
            'total_time': 0
        }
        
        # Headers for requests
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/rss+xml, application/xml, application/xhtml+xml, text/xml;q=0.9, */*;q=0.8',
            'Accept-Language': 'ar,en;q=0.9',
        }
    
    def _get_adaptive_timeout(self, url: str) -> int:
        """
        Get adaptive timeout based on domain patterns
        
        Args:
            url: Feed URL
            
        Returns:
            Timeout in seconds
        """
        # Fast domains (CDN, major news sites)
        fast_domains = ['bbc.co.uk', 'cnn.com', 'reuters.com', 'aljazeera.net']
        # Slow domains (known slow sites)
        slow_domains = ['japantimes.co.jp', 'indianexpress.com']
        
        for domain in fast_domains:
            if domain in url:
                return 5  # 5 seconds for fast sites
        
        for domain in slow_domains:
            if domain in url:
                return 15  # 15 seconds for slow sites
        
        return self.default_timeout  # 10 seconds default
    
    def _create_article_hash(self, title: str, link: str, published_at: Optional[str]) -> str:
        """
        Create unique identifier for article - ONLY uses URL
        
        CRITICAL: Only URL is used for duplicate detection.
        Title and date are NOT used because:
        - Different sources can have articles with same title about same event
        - We want to keep all unique articles from different sources
        - URL is the only truly unique identifier
        
        Args:
            title: Article title (NOT USED for hash)
            link: Article URL (ONLY THIS is used)
            published_at: Published date (NOT USED for hash)
            
        Returns:
            URL string (not hashed - direct comparison is faster)
        """
        # Return URL directly - no need to hash, direct comparison is faster and clearer
        return link
    
    async def _fetch_single_feed(
        self,
        session: aiohttp.ClientSession,
        source: Dict,
        seen_hashes: set,
        semaphore: asyncio.Semaphore
    ) -> Tuple[Dict, List[Dict]]:
        """
        Fetch a single RSS feed with retry logic
        
        Args:
            session: aiohttp session
            source: Source dict with 'url', 'name', 'country_name'
            seen_hashes: Set of seen article hashes for deduplication
            semaphore: Semaphore to limit concurrent connections
            
        Returns:
            Tuple of (source_result, articles)
        """
        async with semaphore:
            url = source['url']
            name = source['name']
            timeout_seconds = self._get_adaptive_timeout(url)
            
            # Prepare headers with cache
            headers = self.headers.copy()
            if self.enable_cache and url in self.cache:
                cache_entry = self.cache[url]
                if 'etag' in cache_entry:
                    headers['If-None-Match'] = cache_entry['etag']
                if 'last_modified' in cache_entry:
                    headers['If-Modified-Since'] = cache_entry['last_modified']
            
            # Try fetching with retries
            for attempt in range(self.max_retries + 1):
                try:
                    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
                    
                    async with session.get(url, headers=headers, timeout=timeout) as response:
                        # Check for 304 Not Modified (cache hit)
                        if response.status == 304:
                            logger.info(f"✅ {name}: Cache hit (304 Not Modified)")
                            self.metrics['cached'] += 1
                            return (
                                {'source': name, 'status': 'cached', 'articles': 0},
                                []
                            )
                        
                        # Get content
                        content = await response.text()
                        
                        # Update cache
                        if self.enable_cache:
                            cache_entry = {}
                            if 'ETag' in response.headers:
                                cache_entry['etag'] = response.headers['ETag']
                            if 'Last-Modified' in response.headers:
                                cache_entry['last_modified'] = response.headers['Last-Modified']
                            if cache_entry:
                                self.cache[url] = cache_entry
                        
                        # Parse feed
                        feed = feedparser.parse(content)
                        
                        if not feed.entries:
                            logger.warning(f"⚠️  {name}: No entries found")
                            return (
                                {'source': name, 'status': 'empty', 'articles': 0},
                                []
                            )
                        
                        # Process articles
                        articles = []
                        duplicates = 0
                        
                        skipped_missing_data = 0
                        
                        for entry in feed.entries[:50]:  # Limit to 50 per source
                            # Extract article data
                            title = entry.get('title', '').strip()
                            link = entry.get('link', '')
                            
                            if not title or not link:
                                skipped_missing_data += 1
                                if not title:
                                    logger.debug(f"      ⏭️  Skipped: missing title")
                                if not link:
                                    logger.debug(f"      ⏭️  Skipped: missing link")
                                continue
                            
                            # Get published date
                            published_at = None
                            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                try:
                                    published_at = datetime(*entry.published_parsed[:6]).isoformat()
                                except:
                                    pass
                            
                            # DUPLICATE FILTERING REMOVED:
                            # Per user request, do NOT filter duplicates in fetch/match phase
                            # Only the DB unique constraint on URL should prevent actual duplicates
                            # This ensures ALL fetched articles flow through to matching
                            article_hash = self._create_article_hash(title, link, published_at)
                            
                            # NOTE: No longer checking seen_hashes or skipping duplicates here
                            # Let all articles through to matching and DB insertion
                            
                            # Get summary/description
                            summary = entry.get('summary', '') or entry.get('description', '')
                            
                            # Get content (full article text if available)
                            # RSS feeds may have content:encoded or content field with full text
                            content = ''
                            if hasattr(entry, 'content') and entry.content:
                                # content is usually a list of dicts
                                if isinstance(entry.content, list) and len(entry.content) > 0:
                                    content = entry.content[0].get('value', '')
                                elif isinstance(entry.content, str):
                                    content = entry.content
                            # Fallback to content_detail or content_encoded
                            if not content and hasattr(entry, 'content_detail'):
                                content = entry.content_detail
                            if not content and hasattr(entry, 'content_encoded'):
                                content = entry.content_encoded
                            
                            # Get image
                            image_url = None
                            if hasattr(entry, 'media_content') and entry.media_content:
                                image_url = entry.media_content[0].get('url')
                            elif hasattr(entry, 'enclosures') and entry.enclosures:
                                image_url = entry.enclosures[0].get('href')
                            
                            articles.append({
                                'title': title,
                                'link': link,
                                'summary': summary,
                                'content': content,  # Added content field for better matching
                                'published_at': published_at,
                                'image_url': image_url,
                                'source_name': name,
                                'country_name': source.get('country_name', ''),
                                'hash': article_hash
                            })
                        
                        # NOTE: duplicates counter no longer used (filtering disabled)
                        # Log without duplicate info
                        logger.info(f"✅ {name}: {len(articles)} articles")
                        self.metrics['successful'] += 1
                        
                        return (
                            {'source': name, 'status': 'success', 'articles': len(articles)},
                            articles
                        )
                
                except asyncio.TimeoutError:
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"⏱️  {name}: Timeout (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"❌ {name}: Timeout after {self.max_retries + 1} attempts")
                        self.metrics['timeout'] += 1
                        return (
                            {'source': name, 'status': 'timeout', 'articles': 0},
                            []
                        )
                
                except Exception as e:
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"⚠️  {name}: Error ({str(e)[:50]}), retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"❌ {name}: Failed - {str(e)[:100]}")
                        self.metrics['failed'] += 1
                        return (
                            {'source': name, 'status': 'error', 'error': str(e)[:200]},
                            []
                        )
    
    async def fetch_all_feeds(self, sources: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Fetch all RSS feeds concurrently
        
        Args:
            sources: List of source dicts with 'url', 'name', 'country_name'
            
        Returns:
            Tuple of (results, all_articles)
                results: List of status dicts per source
                all_articles: List of all articles from all sources
        """
        self.metrics['total_sources'] = len(sources)
        start_time = time.time()
        
        logger.info(f"🚀 Starting async fetch for {len(sources)} sources...")
        logger.info(f"   Max concurrent: {self.max_concurrent}")
        logger.info(f"   Default timeout: {self.default_timeout}s")
        logger.info(f"   Cache enabled: {self.enable_cache}")
        
        # Create semaphore to limit concurrent connections
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # NOTE: Duplicate filtering REMOVED per user request
        # Only DB-level unique constraint on URL should prevent duplicates
        # Do NOT drop articles in the fetch/match phase
        seen_hashes = set()  # Kept for interface compatibility but not used
        
        # Create aiohttp session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=5,  # Max 5 connections per domain
            ttl_dns_cache=300  # DNS cache for 5 minutes
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create tasks for all sources
            tasks = [
                self._fetch_single_feed(session, source, seen_hashes, semaphore)
                for source in sources
            ]
            
            # Execute all tasks concurrently
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        results = []
        all_articles = []
        
        for result in results_list:
            if isinstance(result, Exception):
                logger.error(f"❌ Task exception: {str(result)[:100]}")
                results.append({'status': 'exception', 'error': str(result)[:200]})
            else:
                result_dict, articles = result
                results.append(result_dict)
                all_articles.extend(articles)
        
        # Calculate metrics
        self.metrics['total_time'] = time.time() - start_time
        success_rate = (self.metrics['successful'] / len(sources) * 100) if sources else 0
        
        logger.info("=" * 80)
        logger.info("📊 ASYNC FETCH SUMMARY")
        logger.info("=" * 80)
        logger.info(f"   Total sources: {self.metrics['total_sources']}")
        logger.info(f"   ✅ Successful: {self.metrics['successful']} ({success_rate:.1f}%)")
        logger.info(f"   💾 Cached: {self.metrics['cached']}")
        logger.info(f"   ⏱️  Timeout: {self.metrics['timeout']}")
        logger.info(f"   ❌ Failed: {self.metrics['failed']}")
        logger.info(f"   📝 Total articles: {len(all_articles)}")
        # NOTE: Duplicate filtering disabled - all fetched articles passed through
        logger.info(f"   ⏱️  Total time: {self.metrics['total_time']:.2f}s")
        logger.info(f"   ⚡ Articles/second: {len(all_articles) / self.metrics['total_time']:.1f}")
        logger.info("=" * 80)
        
        return results, all_articles


# Convenience function
async def fetch_feeds_async(sources: List[Dict], max_concurrent=50) -> Tuple[List[Dict], List[Dict]]:
    """
    Convenience function to fetch feeds asynchronously
    
    Args:
        sources: List of source dicts
        max_concurrent: Max concurrent connections
        
    Returns:
        Tuple of (results, articles)
    """
    fetcher = AsyncRSSFetcher(max_concurrent=max_concurrent)
    return await fetcher.fetch_all_feeds(sources)


# Test function
if __name__ == "__main__":
    # Test with sample sources
    test_sources = [
        {'name': 'BBC News', 'url': 'http://feeds.bbci.co.uk/news/rss.xml', 'country_name': 'بريطانيا'},
        {'name': 'CNN', 'url': 'http://rss.cnn.com/rss/edition.rss', 'country_name': 'أمريكا'},
        {'name': 'Al Jazeera', 'url': 'https://aljazeera.net/rss/all', 'country_name': 'قطر'},
    ]
    
    async def test():
        results, articles = await fetch_feeds_async(test_sources)
        print(f"\nTest Results:")
        print(f"Sources: {len(test_sources)}")
        print(f"Articles: {len(articles)}")
        for result in results:
            print(f"  - {result}")
    
    asyncio.run(test())
