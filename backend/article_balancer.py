"""
Article Balancing Module

Implements intelligent article selection when a per-run limit is applied.
Prevents bias toward one language, country, or keyword by distributing
the quota across groups.

Strategy:
1. Group articles by the configured dimension (language, country, or keyword)
2. Allocate quota proportionally to group sizes
3. Ensure minimum representation for each group
4. Select newest articles within each group's quota
"""
from typing import List, Tuple, Dict
from collections import defaultdict
import config
import logging

logger = logging.getLogger(__name__)


def balance_articles(
    matches: List[Tuple],
    limit: int,
    strategy: str = None,
    min_per_group: int = None
) -> List[Tuple]:
    """
    Balance article selection across groups to reduce bias.
    
    Args:
        matches: List of (article, source, matched_keywords) tuples
        limit: Maximum number of articles to select
        strategy: Balancing strategy ('language', 'country', 'keyword', or 'none')
        min_per_group: Minimum articles per group (ensures representation)
        
    Returns:
        List of selected (article, source, matched_keywords) tuples
        
    Examples:
        >>> # 100 English articles, 10 Arabic articles, limit=20
        >>> # Without balancing: 20 English, 0 Arabic
        >>> # With balancing: 18 English, 2 Arabic (proportional with min)
    """
    # Use config defaults if not specified
    if strategy is None:
        strategy = config.BALANCING_STRATEGY
    if min_per_group is None:
        min_per_group = config.MIN_ARTICLES_PER_GROUP
    
    # No balancing needed
    if strategy == 'none' or limit is None or len(matches) <= limit:
        return matches[:limit] if limit else matches
    
    logger.info(f"📊 Balancing {len(matches)} articles → {limit} using '{strategy}' strategy")
    
    # Group articles
    groups = _group_articles(matches, strategy)
    
    if not groups:
        logger.warning("⚠️  No groups created, returning first N articles")
        return matches[:limit]
    
    # Calculate quotas
    quotas = _calculate_quotas(groups, limit, min_per_group)
    
    # Select articles from each group
    selected = []
    for group_key, quota in quotas.items():
        group_articles = groups[group_key]
        
        # Sort by recency (assuming published_at is available)
        # Take newest articles up to quota
        group_selected = _select_newest(group_articles, quota)
        selected.extend(group_selected)
        
        logger.info(f"   • {group_key}: {len(group_selected)}/{len(group_articles)} selected")
    
    logger.info(f"✅ Balanced selection: {len(selected)} articles from {len(groups)} groups")
    
    return selected


def _group_articles(
    matches: List[Tuple],
    strategy: str
) -> Dict[str, List[Tuple]]:
    """
    Group articles by the specified strategy.
    
    Args:
        matches: List of (article, source, matched_keywords) tuples
        strategy: Grouping dimension
        
    Returns:
        Dict mapping group_key -> list of articles
    """
    groups = defaultdict(list)
    
    for match in matches:
        article, source, matched_keywords = match
        
        if strategy == 'language':
            # Group by detected language
            from multilingual_matcher import detect_article_language
            lang = detect_article_language(
                article.get('title', ''),
                article.get('summary', '')
            )
            group_key = f"lang:{lang}"
            
        elif strategy == 'country':
            # Group by source country
            country = source.get('country_name', 'Unknown')
            group_key = f"country:{country}"
            
        elif strategy == 'keyword':
            # Group by primary matched keyword
            if matched_keywords:
                primary_keyword = matched_keywords[0].get('keyword_ar', 'Unknown')
                group_key = f"keyword:{primary_keyword}"
            else:
                group_key = "keyword:Unknown"
                
        else:
            # Fallback: no grouping
            group_key = "all"
        
        groups[group_key].append(match)
    
    return dict(groups)


def _calculate_quotas(
    groups: Dict[str, List],
    total_limit: int,
    min_per_group: int
) -> Dict[str, int]:
    """
    Calculate quota for each group.
    
    Strategy:
    1. Ensure each group gets at least min_per_group articles
    2. Distribute remaining quota proportionally to group sizes
    3. If total minimum exceeds limit, distribute proportionally
    
    Args:
        groups: Dict of group_key -> articles
        total_limit: Total articles to select
        min_per_group: Minimum per group
        
    Returns:
        Dict of group_key -> quota
    """
    num_groups = len(groups)
    total_articles = sum(len(articles) for articles in groups.values())
    
    # Calculate initial quotas
    quotas = {}
    
    # Case 1: Enough quota for minimum per group
    total_minimum = num_groups * min_per_group
    
    if total_minimum <= total_limit:
        # Allocate minimums first
        remaining_quota = total_limit - total_minimum
        
        for group_key, articles in groups.items():
            # Start with minimum
            base_quota = min(min_per_group, len(articles))
            
            # Add proportional share of remaining
            if total_articles > total_minimum:
                proportion = len(articles) / total_articles
                additional = int(remaining_quota * proportion)
            else:
                additional = 0
            
            # Don't exceed group size
            quota = min(base_quota + additional, len(articles))
            quotas[group_key] = quota
    
    else:
        # Case 2: Not enough quota for all minimums
        # Distribute proportionally
        for group_key, articles in groups.items():
            proportion = len(articles) / total_articles
            quota = max(1, int(total_limit * proportion))  # At least 1
            quota = min(quota, len(articles))  # Don't exceed group size
            quotas[group_key] = quota
    
    # Adjust to exactly match limit (handle rounding)
    total_allocated = sum(quotas.values())
    if total_allocated < total_limit:
        # Give extra to largest groups
        sorted_groups = sorted(
            quotas.items(),
            key=lambda x: (len(groups[x[0]]) - x[1], len(groups[x[0]])),
            reverse=True
        )
        for group_key, current_quota in sorted_groups:
            if total_allocated >= total_limit:
                break
            if current_quota < len(groups[group_key]):
                quotas[group_key] += 1
                total_allocated += 1
    
    elif total_allocated > total_limit:
        # Remove from smallest quotas
        sorted_groups = sorted(quotas.items(), key=lambda x: x[1])
        for group_key, current_quota in sorted_groups:
            if total_allocated <= total_limit:
                break
            if current_quota > 1:
                quotas[group_key] -= 1
                total_allocated -= 1
    
    return quotas


def _select_newest(
    articles: List[Tuple],
    quota: int
) -> List[Tuple]:
    """
    Select the newest articles up to quota.
    
    Args:
        articles: List of (article, source, matched_keywords) tuples
        quota: Number to select
        
    Returns:
        Selected articles (newest first)
    """
    # Sort by published date (newest first)
    # Handle missing dates gracefully
    def get_date(match):
        article, _, _ = match
        published = article.get('published_at')
        if published:
            # Try to parse if string
            if isinstance(published, str):
                try:
                    from dateutil import parser as date_parser
                    return date_parser.parse(published)
                except:
                    pass
            return published
        # No date: put at end
        from datetime import datetime
        return datetime.min
    
    try:
        sorted_articles = sorted(articles, key=get_date, reverse=True)
    except Exception as e:
        logger.warning(f"⚠️  Failed to sort by date: {e}, using original order")
        sorted_articles = articles
    
    return sorted_articles[:quota]


def get_balancing_stats(
    original_count: int,
    selected: List[Tuple],
    strategy: str = None
) -> Dict:
    """
    Generate statistics about the balancing operation.
    
    Args:
        original_count: Number of articles before balancing
        selected: Selected articles after balancing
        strategy: Balancing strategy used
        
    Returns:
        Dict with balancing statistics
    """
    if strategy is None:
        strategy = config.BALANCING_STRATEGY
    
    # Group selected articles
    groups = _group_articles(selected, strategy)
    
    return {
        'total_matched': original_count,
        'total_selected': len(selected),
        'strategy': strategy,
        'num_groups': len(groups),
        'groups': {
            group_key: len(articles)
            for group_key, articles in groups.items()
        }
    }


# ==================== Testing Helpers ====================

def _test_balancing():
    """Quick test of balancing logic"""
    print("=" * 80)
    print("ARTICLE BALANCING TEST")
    print("=" * 80)
    
    # Create fake articles
    def make_article(lang, country, keyword, title):
        article = {'title': title, 'summary': '', 'published_at': None}
        source = {'country_name': country}
        matched_keywords = [{'keyword_ar': keyword}]
        return (article, source, matched_keywords)
    
    # Simulate skewed distribution
    matches = []
    # 80 English/US articles
    for i in range(80):
        matches.append(make_article('en', 'United States', 'ترامب', f'US Article {i}'))
    # 15 Arabic/Saudi articles
    for i in range(15):
        matches.append(make_article('ar', 'Saudi Arabia', 'السعودية', f'Saudi Article {i}'))
    # 5 French articles
    for i in range(5):
        matches.append(make_article('fr', 'France', 'فرنسا', f'French Article {i}'))
    
    print(f"\nInput: {len(matches)} articles")
    print("  - 80 English/US")
    print("  - 15 Arabic/Saudi")
    print("  - 5 French/France")
    
    # Test balancing
    limit = 20
    selected = balance_articles(matches, limit, strategy='language', min_per_group=2)
    
    stats = get_balancing_stats(len(matches), selected, 'language')
    print(f"\nBalanced to {limit} articles:")
    for group_key, count in stats['groups'].items():
        print(f"  - {group_key}: {count}")
    
    print("\n✅ Test complete")


if __name__ == "__main__":
    _test_balancing()
