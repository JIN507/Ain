"""
Monitoring System Configuration

Centralized configuration for the news monitoring system.
All configurable limits, thresholds, and settings in one place.
"""
import os


# ==================== Article Save Limits ====================

# Maximum articles to save per monitoring run
# Set to None for unlimited, or an integer to cap the number
MAX_ARTICLES_PER_RUN = int(os.getenv('MAX_ARTICLES_PER_RUN', '300'))  # Default: 300
# Note: Set to 0 or None for unlimited saving

# Balancing strategy when limit is applied
# Options: 'none', 'language', 'country', 'keyword'
BALANCING_STRATEGY = os.getenv('BALANCING_STRATEGY', 'language')  # Default: balance by language

# Minimum articles per group when balancing (ensures representation)
MIN_ARTICLES_PER_GROUP = int(os.getenv('MIN_ARTICLES_PER_GROUP', '3'))  # Default: 3


# ==================== RSS Fetching ====================

# Maximum concurrent RSS connections
MAX_CONCURRENT_FETCHES = int(os.getenv('MAX_CONCURRENT_FETCHES', '50'))

# Maximum articles to take from each RSS source
MAX_ARTICLES_PER_SOURCE = int(os.getenv('MAX_ARTICLES_PER_SOURCE', '30'))

# RSS fetch timeout (seconds)
RSS_FETCH_TIMEOUT = int(os.getenv('RSS_FETCH_TIMEOUT', '10'))

# Maximum retries for failed RSS fetches
RSS_MAX_RETRIES = int(os.getenv('RSS_MAX_RETRIES', '2'))


# ==================== Translation ====================

# Languages to translate keywords into
TRANSLATE_TARGETS = os.getenv(
    'TRANSLATE_TARGETS',
    'en,fr,es,de,ru,zh-cn,ja,hi,id,pt,tr,ar,ko,it,nl,pl,vi,th,uk,ro,el,cs,sv,hu,fi,da,no,sk,bg,hr,ms,fa,ur'
).split(',')

# Translation cache TTL (days)
TRANSLATION_CACHE_TTL_DAYS = int(os.getenv('TRANSLATION_CACHE_TTL_DAYS', '7'))

# Translation timeout (seconds)
TRANSLATION_TIMEOUT_S = int(os.getenv('TRANSLATION_TIMEOUT_S', '8'))


# ==================== Keyword Matching ====================

# Minimum relevance score for keyword matching (0.0 to 1.0)
MIN_RELEVANCE_SCORE = float(os.getenv('MIN_RELEVANCE_SCORE', '0.3'))

# Fields to search for keyword matches
SEARCH_FIELDS = ['title', 'description', 'content']  # Order matters (weighted)


# ==================== Feed Health Tracking ====================

# Number of consecutive empty runs before marking feed as unhealthy
UNHEALTHY_THRESHOLD_EMPTY_RUNS = int(os.getenv('UNHEALTHY_THRESHOLD_EMPTY_RUNS', '5'))

# Enable feed health diagnostics
ENABLE_FEED_HEALTH = os.getenv('ENABLE_FEED_HEALTH', 'true').lower() == 'true'


# ==================== Logging & Debugging ====================

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Enable detailed matching logs
ENABLE_MATCH_DEBUG = os.getenv('ENABLE_MATCH_DEBUG', 'false').lower() == 'true'

# Enable performance metrics
ENABLE_PERFORMANCE_METRICS = os.getenv('ENABLE_PERFORMANCE_METRICS', 'true').lower() == 'true'


# ==================== Helper Functions ====================

def get_effective_save_limit():
    """
    Get the effective save limit for articles per run.
    
    Returns:
        int or None: Number of articles to save, or None for unlimited
    """
    if MAX_ARTICLES_PER_RUN is None or MAX_ARTICLES_PER_RUN == 0:
        return None
    return MAX_ARTICLES_PER_RUN


def is_balancing_enabled():
    """
    Check if balancing strategy is enabled.
    
    Returns:
        bool: True if balancing is active
    """
    return BALANCING_STRATEGY != 'none' and get_effective_save_limit() is not None


def get_config_summary():
    """
    Get a summary of current configuration.
    
    Returns:
        dict: Configuration summary
    """
    return {
        'max_articles_per_run': get_effective_save_limit() or 'unlimited',
        'balancing_strategy': BALANCING_STRATEGY,
        'min_articles_per_group': MIN_ARTICLES_PER_GROUP,
        'max_concurrent_fetches': MAX_CONCURRENT_FETCHES,
        'max_articles_per_source': MAX_ARTICLES_PER_SOURCE,
        'translation_targets': len(TRANSLATE_TARGETS),
        'min_relevance_score': MIN_RELEVANCE_SCORE,
        'feed_health_enabled': ENABLE_FEED_HEALTH,
    }


# ==================== Validation ====================

def validate_config():
    """
    Validate configuration values and warn about issues.
    """
    issues = []
    
    if MAX_ARTICLES_PER_RUN is not None:
        if MAX_ARTICLES_PER_RUN < 0:
            issues.append("MAX_ARTICLES_PER_RUN cannot be negative")
        elif MAX_ARTICLES_PER_RUN < 10 and MAX_ARTICLES_PER_RUN > 0:
            issues.append("MAX_ARTICLES_PER_RUN is very low (< 10), may miss important articles")
    
    if BALANCING_STRATEGY not in ['none', 'language', 'country', 'keyword']:
        issues.append(f"Unknown BALANCING_STRATEGY: {BALANCING_STRATEGY}")
    
    if MIN_ARTICLES_PER_GROUP < 1:
        issues.append("MIN_ARTICLES_PER_GROUP must be at least 1")
    
    if MIN_RELEVANCE_SCORE < 0 or MIN_RELEVANCE_SCORE > 1:
        issues.append("MIN_RELEVANCE_SCORE must be between 0.0 and 1.0")
    
    return issues


# Validate on import
_validation_issues = validate_config()
if _validation_issues:
    import warnings
    for issue in _validation_issues:
        warnings.warn(f"Configuration issue: {issue}")
