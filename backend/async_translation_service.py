"""
Async Translation Service with Caching
Handles translations in background with Redis/SQLite caching for speed
"""
import asyncio
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple
from deep_translator import GoogleTranslator
import sqlite3
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class TranslationCache:
    """SQLite-based translation cache"""
    
    def __init__(self, cache_file='translation_cache.db'):
        self.cache_file = cache_file
        self._init_db()
    
    def _init_db(self):
        """Initialize cache database"""
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                hash TEXT PRIMARY KEY,
                source_lang TEXT,
                target_lang TEXT,
                source_text TEXT,
                translated_text TEXT,
                created_at INTEGER
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON translations(hash)")
        conn.commit()
        conn.close()
    
    def _create_hash(self, text: str, source_lang: str, target_lang: str) -> str:
        """Create hash for cache key"""
        content = f"{text}|{source_lang}|{target_lang}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get translation from cache"""
        hash_key = self._create_hash(text, source_lang, target_lang)
        
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT translated_text FROM translations WHERE hash = ?",
            (hash_key,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def set(self, text: str, source_lang: str, target_lang: str, translated: str):
        """Save translation to cache"""
        hash_key = self._create_hash(text, source_lang, target_lang)
        
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO translations 
            (hash, source_lang, target_lang, source_text, translated_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (hash_key, source_lang, target_lang, text[:500], translated, int(time.time())))
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM translations")
        total = cursor.fetchone()[0]
        conn.close()
        
        return {'total_cached': total}


class AsyncTranslationService:
    """
    Async translation service with:
    - Batch translation (multiple texts in one call)
    - SQLite caching (instant cache hits)
    - Thread pool for blocking Google Translate API
    - Background task queue support
    """
    
    def __init__(self, max_workers=10, enable_cache=True):
        """
        Initialize translation service
        
        Args:
            max_workers: Max concurrent translation threads
            enable_cache: Enable caching (default: True)
        """
        self.max_workers = max_workers
        self.enable_cache = enable_cache
        self.cache = TranslationCache() if enable_cache else None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Metrics
        self.metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'total_time': 0
        }
    
    def _translate_sync(self, text: str, src_lang: str, dest_lang: str) -> str:
        """
        Synchronous translation (called in thread pool)
        
        Args:
            text: Text to translate
            src_lang: Source language
            dest_lang: Destination language
            
        Returns:
            Translated text
        """
        try:
            return GoogleTranslator(source=src_lang, target=dest_lang).translate(text)
        except Exception as e:
            logger.error(f"Translation error: {str(e)[:100]}")
            return text  # Return original on error
    
    async def translate(self, text: str, src_lang: str = 'en', dest_lang: str = 'ar') -> str:
        """
        Translate text asynchronously with caching
        
        Args:
            text: Text to translate
            src_lang: Source language (default: 'en')
            dest_lang: Destination language (default: 'ar')
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return ""
        
        self.metrics['total_requests'] += 1
        
        # Check cache first
        if self.enable_cache:
            cached = self.cache.get(text, src_lang, dest_lang)
            if cached:
                self.metrics['cache_hits'] += 1
                logger.debug(f"✅ Cache hit: {text[:50]}...")
                return cached
            self.metrics['cache_misses'] += 1
        
        # Translate in thread pool (to avoid blocking)
        start_time = time.time()
        loop = asyncio.get_event_loop()
        translated = await loop.run_in_executor(
            self.executor,
            self._translate_sync,
            text, src_lang, dest_lang
        )
        
        self.metrics['api_calls'] += 1
        self.metrics['total_time'] += time.time() - start_time
        
        # Save to cache
        if self.enable_cache and translated:
            self.cache.set(text, src_lang, dest_lang, translated)
        
        return translated
    
    async def translate_batch(
        self,
        texts: List[str],
        src_lang: str = 'en',
        dest_lang: str = 'ar'
    ) -> List[str]:
        """
        Translate multiple texts concurrently
        
        Args:
            texts: List of texts to translate
            src_lang: Source language
            dest_lang: Destination language
            
        Returns:
            List of translated texts
        """
        tasks = [self.translate(text, src_lang, dest_lang) for text in texts]
        return await asyncio.gather(*tasks)
    
    async def translate_article(
        self,
        title: str,
        summary: str,
        src_lang: str = 'en',
        dest_lang: str = 'ar'
    ) -> Dict[str, str]:
        """
        Translate article title and summary concurrently
        
        Args:
            title: Article title
            summary: Article summary
            src_lang: Source language
            dest_lang: Destination language
            
        Returns:
            Dict with 'title' and 'summary' translated
        """
        title_task = self.translate(title, src_lang, dest_lang)
        summary_task = self.translate(summary, src_lang, dest_lang)
        
        title_ar, summary_ar = await asyncio.gather(title_task, summary_task)
        
        return {
            'title': title_ar,
            'summary': summary_ar,
            'original_title': title,
            'original_summary': summary
        }
    
    async def translate_articles_batch(
        self,
        articles: List[Dict],
        src_lang: str = 'en',
        dest_lang: str = 'ar'
    ) -> List[Dict]:
        """
        Translate multiple articles concurrently
        
        Args:
            articles: List of article dicts with 'title' and 'summary'
            src_lang: Source language
            dest_lang: Destination language
            
        Returns:
            List of articles with translations added
        """
        tasks = [
            self.translate_article(
                article.get('title', ''),
                article.get('summary', ''),
                src_lang,
                dest_lang
            )
            for article in articles
        ]
        
        translations = await asyncio.gather(*tasks)
        
        # Merge translations back into articles
        for article, translation in zip(articles, translations):
            article['title_ar'] = translation['title']
            article['summary_ar'] = translation['summary']
        
        return articles
    
    def get_metrics(self) -> Dict:
        """Get translation metrics"""
        cache_hit_rate = (
            self.metrics['cache_hits'] / self.metrics['total_requests'] * 100
            if self.metrics['total_requests'] > 0 else 0
        )
        
        avg_time = (
            self.metrics['total_time'] / self.metrics['api_calls']
            if self.metrics['api_calls'] > 0 else 0
        )
        
        return {
            **self.metrics,
            'cache_hit_rate': cache_hit_rate,
            'avg_translation_time': avg_time,
            'cache_stats': self.cache.get_stats() if self.cache else {}
        }
    
    def print_metrics(self):
        """Print translation metrics"""
        metrics = self.get_metrics()
        
        logger.info("=" * 80)
        logger.info("📊 TRANSLATION METRICS")
        logger.info("=" * 80)
        logger.info(f"   Total requests: {metrics['total_requests']}")
        logger.info(f"   ✅ Cache hits: {metrics['cache_hits']} ({metrics['cache_hit_rate']:.1f}%)")
        logger.info(f"   ❌ Cache misses: {metrics['cache_misses']}")
        logger.info(f"   🌐 API calls: {metrics['api_calls']}")
        logger.info(f"   ⏱️  Avg time/call: {metrics['avg_translation_time']:.3f}s")
        logger.info(f"   💾 Total cached: {metrics['cache_stats'].get('total_cached', 0)}")
        logger.info("=" * 80)


# Singleton instance
_translation_service = None


def get_translation_service(max_workers=10, enable_cache=True) -> AsyncTranslationService:
    """Get or create singleton translation service"""
    global _translation_service
    if _translation_service is None:
        _translation_service = AsyncTranslationService(max_workers, enable_cache)
    return _translation_service


# Convenience functions
async def translate_text(text: str, src='en', dest='ar') -> str:
    """Translate single text"""
    service = get_translation_service()
    return await service.translate(text, src, dest)


async def translate_article_async(title: str, summary: str, src='en', dest='ar') -> Dict:
    """Translate article"""
    service = get_translation_service()
    return await service.translate_article(title, summary, src, dest)


async def translate_articles_async(articles: List[Dict], src='en', dest='ar') -> List[Dict]:
    """Translate multiple articles"""
    service = get_translation_service()
    return await service.translate_articles_batch(articles, src, dest)


# Test function
if __name__ == "__main__":
    async def test():
        service = AsyncTranslationService(max_workers=5)
        
        # Test single translation
        result = await service.translate("Hello world", "en", "ar")
        print(f"Translation: {result}")
        
        # Test article translation
        article = await service.translate_article(
            "Breaking News: Major Event",
            "This is a test summary for the article",
            "en", "ar"
        )
        print(f"Article: {article}")
        
        # Test batch translation
        articles = [
            {'title': 'Article 1', 'summary': 'Summary 1'},
            {'title': 'Article 2', 'summary': 'Summary 2'},
            {'title': 'Article 3', 'summary': 'Summary 3'},
        ]
        translated = await service.translate_articles_batch(articles, "en", "ar")
        print(f"\nTranslated {len(translated)} articles")
        
        # Print metrics
        service.print_metrics()
    
    asyncio.run(test())
