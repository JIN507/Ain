"""
Async Monitor Wrapper for Flask Integration
Bridges sync Flask routes with async RSS fetching

Memory-optimized: Processes sources in batches to stay under 512MB RAM limit.
"""
import json
import re
import sys
import os
import gc
import asyncio
from typing import List, Dict, Tuple, Optional
from async_rss_fetcher import AsyncRSSFetcher
from multilingual_matcher import match_article_against_keywords, detect_article_language
from translation_cache import translate_article_to_arabic
from match_context_extractor import extract_all_match_contexts, translate_snippet_preserve_keyword
from models import Article
from datetime import datetime
import json
from dateutil import parser as date_parser
import config
from article_balancer import balance_articles, get_balancing_stats
from feed_health import get_tracker as get_health_tracker


def parse_published_date(date_value) -> Optional[datetime]:
    """
    Convert various date formats to Python datetime object
    
    Args:
        date_value: Can be string (ISO), datetime, or None
        
    Returns:
        Python datetime object or None
    """
    if not date_value:
        return None
    
    # Already a datetime object
    if isinstance(date_value, datetime):
        return date_value
    
    # String - try to parse
    if isinstance(date_value, str):
        try:
            return date_parser.parse(date_value)
        except:
            return None
    
    return None


def fetch_feeds_sync(sources: List[Dict], max_concurrent=50) -> Tuple[List[Dict], List[Dict]]:
    """
    Synchronous wrapper for async RSS fetching
    Suitable for use in Flask routes
    
    Args:
        sources: List of source dicts with 'url', 'name', 'country_name'
        max_concurrent: Max concurrent connections
        
    Returns:
        Tuple of (results, articles)
    """
    async def _fetch():
        fetcher = AsyncRSSFetcher(max_concurrent=max_concurrent)
        return await fetcher.fetch_all_feeds(sources)
    
    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results, articles = loop.run_until_complete(_fetch())
        return results, articles
    finally:
        # Cancel all pending tasks to avoid 'Task was destroyed' warnings
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def match_articles_with_keywords(
    articles: List[Dict],
    keyword_expansions: List[Dict],
    max_per_source: int = 30
) -> List[Tuple[Dict, Dict, List]]:
    """
    Match articles against expanded keywords
    
    Args:
        articles: List of article dicts
        keyword_expansions: List of keyword expansion dicts
        max_per_source: Max articles to process (already limited by fetcher)
        
    Returns:
        List of (article, source, matched_keywords) tuples
    """
    matches = []
    
    # Group articles by source for processing
    articles_by_source = {}
    for article in articles:
        source_name = article.get('source_name', 'Unknown')
        if source_name not in articles_by_source:
            articles_by_source[source_name] = {
                'source': {
                    'name': source_name,
                    'country_name': article.get('country_name', 'غير محدد')
                },
                'articles': []
            }
        articles_by_source[source_name]['articles'].append(article)
    
    # Process each source's articles
    for source_name, data in articles_by_source.items():
        source = data['source']
        source_articles = data['articles'][:max_per_source]
        
        for article_data in source_articles:
            # Clean HTML from summary (remove ads, navigation, social links, etc.)
            from utils import clean_html_content
            summary_raw = article_data.get('summary', '')
            summary_clean = clean_html_content(summary_raw) if summary_raw else ''
            
            # Create article dict for matching
            # IMPORTANT: Include content field for strict lexical matching
            article = {
                'title': article_data.get('title', ''),
                'summary': summary_clean,
                'content': article_data.get('content', ''),  # Added for strict matching
                'url': article_data.get('link', ''),
                'published_at': article_data.get('published_at'),
                'image_url': article_data.get('image_url')
            }
            
            # Match against keywords
            matched = match_article_against_keywords(
                article,
                keyword_expansions,
                source_name=source_name
            )
            
            if matched:
                matches.append((article, source, matched))
    
    return matches


def match_articles_with_keywords_with_stats(
    articles: List[Dict],
    keyword_expansions: List[Dict],
    max_per_source: int = 30
) -> Tuple[List[Tuple[Dict, Dict, List]], Dict[str, int]]:
    """
    Match articles against expanded keywords WITH per-keyword statistics
    
    Args:
        articles: List of article dicts
        keyword_expansions: List of keyword expansion dicts
        max_per_source: Max articles to process (already limited by fetcher)
        
    Returns:
        Tuple of:
        - List of (article, source, matched_keywords) tuples
        - Dict of keyword_ar -> match_count
    """
    matches = []
    keyword_stats = {exp.get('original_ar', exp.get('keyword_ar', 'Unknown')): 0 
                     for exp in keyword_expansions}
    
    # Group articles by source for processing
    articles_by_source = {}
    for article in articles:
        source_name = article.get('source_name', 'Unknown')
        if source_name not in articles_by_source:
            articles_by_source[source_name] = {
                'source': {
                    'name': source_name,
                    'country_name': article.get('country_name', 'غير محدد')
                },
                'articles': []
            }
        articles_by_source[source_name]['articles'].append(article)
    
    # Process each source's articles
    for source_name, data in articles_by_source.items():
        source = data['source']
        source_articles = data['articles'][:max_per_source]
        
        for article_data in source_articles:
            # Clean HTML from summary (remove ads, navigation, social links, etc.)
            from utils import clean_html_content
            summary_raw = article_data.get('summary', '')
            summary_clean = clean_html_content(summary_raw) if summary_raw else ''
            
            # Create article dict for matching
            # IMPORTANT: Include content field for strict lexical matching
            article = {
                'title': article_data.get('title', ''),
                'summary': summary_clean,
                'content': article_data.get('content', ''),  # Added for strict matching
                'url': article_data.get('link', ''),
                'published_at': article_data.get('published_at'),
                'image_url': article_data.get('image_url')
            }
            
            # Match against keywords
            matched = match_article_against_keywords(
                article,
                keyword_expansions,
                source_name=source_name
            )
            
            if matched:
                matches.append((article, source, matched))
                
                # Update statistics for each matched keyword
                for match_info in matched:
                    keyword_ar = match_info.get('keyword_ar', 'Unknown')
                    if keyword_ar in keyword_stats:
                        keyword_stats[keyword_ar] += 1
    
    return matches, keyword_stats


def save_matched_articles_sync(
    db,
    matches: List[Tuple],
    apply_limit: bool = True,
    save_all: bool = False,
    user_id: Optional[int] = None,
) -> Tuple[List[int], Dict]:
    """
    Save matched articles to database with translations.
    
    Applies balancing strategy if configured and limit is active.
    
    Args:
        db: Database session
        matches: List of (article, source, matched_keywords) tuples
        apply_limit: Whether to apply MAX_ARTICLES_PER_RUN limit
        save_all: Override to save all matches regardless of limit
        
    Returns:
        Tuple of (saved_ids, stats_dict)
    """
    original_count = len(matches)
    saved_ids = []
    duplicates = 0
    
    # Determine if we should limit and balance
    limit = config.get_effective_save_limit() if (apply_limit and not save_all) else None
    
    # Apply balancing if limit is active
    if limit and original_count > limit:
        print(f"\n⚖️  Applying save limit: {limit} (from {original_count} matches)")
        print(f"   Strategy: {config.BALANCING_STRATEGY}")
        
        # Balance articles
        matches = balance_articles(matches, limit)
        
        # Get balancing stats
        balance_stats = get_balancing_stats(original_count, matches)
        print(f"   Balanced into {balance_stats['num_groups']} groups")
    elif limit:
        print(f"\n💾 Saving {len(matches)} matched articles (limit: {limit}, no balancing needed)...")
        balance_stats = None
    else:
        print(f"\n💾 Saving all {len(matches)} matched articles (no limit)...")
        balance_stats = None
    
    print()
    
    for article, source, matched_keywords in matches:
        print(f"   📝 Processing: {article['title'][:60]}...")
        
        # Detect language
        detected_lang = detect_article_language(article['title'], article['summary'])
        print(f"      🌍 Language: {detected_lang}")
        
        # Translate to Arabic FIRST (before duplicate check)
        translation_result = translate_article_to_arabic(
            article['title'],
            article['summary'],
            detected_lang
        )
        
        title_ar = translation_result['title_ar']
        summary_ar = translation_result['summary_ar']
        translation_status = translation_result['overall_status']
        
        print(f"      🔄 Translation: {translation_status}")
        
        # STRICT duplicate check: URL + user_id (composite unique constraint)
        # Rule: If URL exists for this user → skip (true duplicate)
        #       If URL is new for this user → save
        dup_filter = [Article.url == article['url']]
        if user_id is not None:
            dup_filter.append(Article.user_id == user_id)
        url_duplicate = db.query(Article).filter(*dup_filter).first()
        
        if url_duplicate:
            # True duplicate - same URL already in database
            duplicates += 1
            print(f"      ⏭️  SKIPPED (duplicate URL: already in database)")
            print(f"         Original ID: {url_duplicate.id}, Date: {url_duplicate.published_at}")
            continue
        
        # If we reach here: URL is unique → SAVE IT (even if title similar to other articles)
        
        # Get primary keyword
        primary_keyword = matched_keywords[0]['keyword_ar']
        
        # Extract match context (for display in UI)
        # Using 20 words before and after (~2 lines of context)
        match_contexts = extract_all_match_contexts(article, matched_keywords, words_before=20, words_after=20)
        
        # Translate match contexts to Arabic while replacing keyword with Arabic version
        for context in match_contexts:
            snippet = context.get('full_snippet', '')
            preserve_text = context.get('preserve_text', '')  # The actual matched keyword (original language)
            keyword_arabic = context.get('keyword_ar', '')  # The Arabic version of the keyword
            
            if snippet and detected_lang != 'ar':
                try:
                    # Use special translation that replaces **keyword** with **Arabic keyword**
                    translated_snippet = translate_snippet_preserve_keyword(
                        snippet, 
                        preserve_text, 
                        detected_lang, 
                        'ar',
                        keyword_ar=keyword_arabic  # Pass Arabic keyword to replace English one
                    )
                    
                    context['full_snippet_ar'] = translated_snippet
                    context['original_matched_text'] = preserve_text
                    
                    print(f"      🔄 Translated context: **{preserve_text}** → **{keyword_arabic}**")
                    
                except Exception as e:
                    print(f"      ⚠️  Failed to translate context snippet: {e}")
                    context['full_snippet_ar'] = snippet  # Use original if translation fails
            else:
                context['full_snippet_ar'] = snippet  # Already Arabic or empty
        
        # Prepare keywords info with match context
        keywords_info = json.dumps({
            'primary': primary_keyword,
            'all_matched': [m['keyword_ar'] for m in matched_keywords],
            'match_details': matched_keywords,
            'match_contexts': match_contexts  # Added: context snippets (original + Arabic) for UI display
        }, ensure_ascii=False)
        
        # Parse published date (convert from ISO string to datetime object)
        published_datetime = parse_published_date(article.get('published_at'))
        
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
            keyword=primary_keyword,  # Arabic keyword for filtering
            keyword_original=primary_keyword,
            keywords_translations=keywords_info,
            sentiment_label="محايد",
            sentiment_score=None,
            published_at=published_datetime,  # ← Now it's a datetime object!
            fetched_at=datetime.utcnow(),
            user_id=user_id,
        )
        
        db.add(new_article)
        db.commit()
        
        saved_ids.append(new_article.id)
        print(f"      ✅ SAVED (ID: {new_article.id})")
        print()
    
    print(f"\n{'='*80}")
    print(f"Summary: Saved {len(saved_ids)} new articles")
    if duplicates > 0:
        print(f"         Skipped {duplicates} duplicates (URL already in database)")
    print(f"{'='*80}\n")
    
    # Build stats dict
    stats = {
        'total_matched': original_count,
        'total_saved': len(saved_ids),
        'duplicates_skipped': duplicates,
        'limit_applied': limit is not None,
        'save_limit': limit,
        'balancing_stats': balance_stats
    }
    
    return saved_ids, stats


def run_optimized_monitoring(
    sources: List[Dict],
    keyword_expansions: List[Dict],
    max_concurrent: int = 50,
    max_per_source: int = 30
) -> Dict:
    """
    Run complete monitoring pipeline with async fetching, health tracking, and full stats.
    
    MEMORY OPTIMIZED: Processes sources in batches of 25 to stay under 512MB RAM.
    
    Args:
        sources: List of enabled sources
        keyword_expansions: List of keyword expansions
        max_concurrent: Max concurrent RSS fetches
        max_per_source: Max articles per source
        
    Returns:
        Comprehensive stats dict including:
        - Fetch results and feed health
        - Keyword matching statistics
        - Save statistics with balancing info
    """
    # MEMORY OPTIMIZATION: Process in batches of 70 sources
    # Balances speed vs memory: ~3500 articles / 70 sources ≈ 50 articles/source
    BATCH_SIZE = 70
    
    print(f"\n{'='*80}")
    print(f"🚀 Starting MEMORY-OPTIMIZED monitoring run")
    print(f"📊 {len(sources)} sources, {len(keyword_expansions)} keywords")
    print(f"📦 Batch size: {BATCH_SIZE} sources per batch")
    print(f"⚡ Max concurrent per batch: {max_concurrent}")
    
    # Show config
    limit = config.get_effective_save_limit()
    if limit:
        print(f"💾 Save limit: {limit} articles per run")
        print(f"⚖️  Balancing: {config.BALANCING_STRATEGY}")
    else:
        print(f"💾 Save limit: Unlimited")
    
    print(f"{'='*80}\n")
    
    # DEBUG: Log all keywords being used
    print("🔑 Active keywords for this run:")
    for i, exp in enumerate(keyword_expansions, 1):
        keyword_ar = exp.get('original_ar', exp.get('keyword_ar', 'Unknown'))
        print(f"   {i}. {keyword_ar}")
    print()
    
    # Initialize aggregated results
    all_results = []
    all_matches = []
    total_fetched = 0
    keyword_stats = {exp.get('original_ar', exp.get('keyword_ar', 'Unknown')): 0 
                     for exp in keyword_expansions}
    
    # Health tracker
    health_tracker = get_health_tracker() if config.ENABLE_FEED_HEALTH else None
    
    # Split sources into batches
    num_batches = (len(sources) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"📦 Processing {len(sources)} sources in {num_batches} batches...\n")
    
    for batch_num in range(num_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(sources))
        batch_sources = sources[batch_start:batch_end]
        
        print(f"\n{'─'*60}")
        print(f"📦 Batch {batch_num + 1}/{num_batches}: sources {batch_start + 1}-{batch_end}")
        print(f"{'─'*60}")
        
        # Step 1: Fetch this batch of RSS feeds
        print(f"📡 Fetching {len(batch_sources)} sources...")
        results, articles = fetch_feeds_sync(batch_sources, max_concurrent=max_concurrent)
        
        # Track feed health
        if health_tracker:
            try:
                health_tracker.process_fetch_results(results)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️  Feed health tracking failed for batch {batch_num + 1}")
        
        all_results.extend(results)
        batch_fetched = len(articles)
        total_fetched += batch_fetched
        
        print(f"✅ Batch {batch_num + 1}: Fetched {batch_fetched} articles")
        
        if articles:
            # Step 2: Match articles with keywords for this batch
            print(f"🔍 Matching batch articles against keywords...")
            batch_matches, batch_stats = match_articles_with_keywords_with_stats(
                articles, keyword_expansions, max_per_source
            )
            
            all_matches.extend(batch_matches)
            
            # Aggregate keyword stats
            for kw, count in batch_stats.items():
                if kw in keyword_stats:
                    keyword_stats[kw] += count
            
            print(f"✅ Batch {batch_num + 1}: Found {len(batch_matches)} matches")
        
        # MEMORY CLEANUP: Force garbage collection between batches
        del articles
        del results
        gc.collect()
        print(f"🧹 Memory cleaned after batch {batch_num + 1}")
    
    # Print health report at end
    if health_tracker:
        try:
            health_tracker.print_health_report()
        except:
            pass
    
    print(f"\n{'='*80}")
    print(f"✅ TOTAL: Fetched {total_fetched} articles, Found {len(all_matches)} matches")
    print(f"{'='*80}")
    
    if not all_matches:
        print("⚠️  No matching articles found!")
        return {
            'success': False,
            'total_fetched': total_fetched,
            'total_matches': 0,
            'total_saved': 0,
            'articles_saved': 0,
            'feed_health': health_tracker.get_summary() if health_tracker else None
        }
    
    # Log per-keyword statistics
    print(f"\n📊 Per-keyword match statistics:")
    total_matches_check = 0
    for keyword_ar, count in keyword_stats.items():
        print(f"   • {keyword_ar}: {count} matches")
        total_matches_check += count
    
    print(f"\n📈 Total unique articles matched: {len(all_matches)}")
    print(f"📈 Total keyword matches (can be > articles): {total_matches_check}")
    
    # Acceptance rate check
    acceptance_rate = (len(all_matches) / total_fetched * 100) if total_fetched else 0
    print(f"📈 Acceptance rate: {acceptance_rate:.1f}% ({len(all_matches)}/{total_fetched})")
    
    # Warning if suspiciously low
    if acceptance_rate < 1.0 and total_fetched > 100:
        print(f"\n⚠️  WARNING: Suspiciously low acceptance rate ({acceptance_rate:.2f}%)")
        print(f"   Total articles: {total_fetched}")
        print(f"   Matched: {len(all_matches)}")
        print(f"   Expected: At least 2-5% for typical keywords")
        print(f"   This might indicate a keyword matching issue!")
    
    return {
        'success': True,
        'total_fetched': total_fetched,
        'total_matches': len(all_matches),
        'matches': all_matches,
        'fetch_results': all_results,
        'keyword_stats': keyword_stats,
        'acceptance_rate': acceptance_rate,
        'feed_health': health_tracker.get_summary() if health_tracker else None,
        'config': config.get_config_summary()
    }
