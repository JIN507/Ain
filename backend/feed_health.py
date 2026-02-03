"""
RSS Feed Health Tracking

Tracks the health status of RSS feeds across monitoring runs.
Helps diagnose issues with empty or failing feeds.

Features:
- Per-source success/failure/empty tracking
- Consecutive empty run counting
- Health status categorization
- Persistent storage (optional)
"""
from typing import Dict, List
from collections import defaultdict
from datetime import datetime
import json
import os
import logging

logger = logging.getLogger(__name__)


class FeedHealthTracker:
    """
    Track health metrics for RSS feeds.
    PHASE 3: Added size limit to prevent RAM overflow
    """
    
    MAX_SOURCES = 50  # Limit tracked sources to prevent RAM overflow
    
    def __init__(self, persistence_file=None):
        """
        Initialize health tracker.
        
        Args:
            persistence_file: Optional file path for persistent storage
        """
        self.persistence_file = persistence_file
        self.stats = {
            'total_sources': 0,
            'successful': 0,
            'failed': 0,
            'empty': 0,
            'per_source': {}  # source_name -> metrics (limited to MAX_SOURCES)
        }
        
        # Load previous data if available
        if persistence_file and os.path.exists(persistence_file):
            self._load()
    
    def record_fetch_result(
        self,
        source_name: str,
        status: str,
        articles_count: int = 0,
        error: str = None
    ):
        """
        Record the result of a feed fetch.
        
        Args:
            source_name: Name of the RSS source
            status: 'success', 'failed', or 'empty'
            articles_count: Number of articles fetched
            error: Error message if failed
        """
        # Initialize source if new (with size limit)
        if source_name not in self.stats['per_source']:
            # PHASE 3: Enforce size limit to prevent RAM overflow
            if len(self.stats['per_source']) >= self.MAX_SOURCES:
                # Remove oldest entry (by total_runs)
                oldest = min(self.stats['per_source'].keys(),
                    key=lambda k: self.stats['per_source'][k].get('total_runs', 0))
                del self.stats['per_source'][oldest]
            
            self.stats['per_source'][source_name] = {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'empty_runs': 0,
                'consecutive_empty': 0,
                'last_success': None,
                'last_failure': None,
                'last_error': None,
                'total_articles_fetched': 0
            }
        
        source_stats = self.stats['per_source'][source_name]
        source_stats['total_runs'] += 1
        
        now = datetime.utcnow().isoformat()
        
        if status == 'success':
            source_stats['successful_runs'] += 1
            source_stats['last_success'] = now
            source_stats['consecutive_empty'] = 0
            source_stats['total_articles_fetched'] += articles_count
            
        elif status == 'empty':
            source_stats['empty_runs'] += 1
            source_stats['consecutive_empty'] += 1
            source_stats['last_success'] = now  # Empty but successful fetch
            
        elif status == 'failed':
            source_stats['failed_runs'] += 1
            source_stats['last_failure'] = now
            source_stats['last_error'] = error
            source_stats['consecutive_empty'] += 1  # Count as empty too
    
    def process_fetch_results(self, results: List[Dict]):
        """
        Process a batch of fetch results.
        
        DEFENSIVE: This function must NEVER raise exceptions that crash monitoring.
        Any processing errors are logged and a safe default is returned.
        
        Args:
            results: List of result dicts from async_rss_fetcher
                Expected format: {'source': str, 'status': str, 'articles': int}
                - 'articles' is an INTEGER count, not a list
                - 'source' is the source name (not 'name')
        """
        try:
            self.stats['total_sources'] = len(results)
            self.stats['successful'] = 0
            self.stats['failed'] = 0
            self.stats['empty'] = 0
            
            for result in results:
                try:
                    # Get source name (field is 'source', not 'name')
                    source_name = result.get('source', result.get('name', 'Unknown'))
                    status = result.get('status', 'failed')
                    
                    # IMPORTANT: 'articles' is an INTEGER count, not a list!
                    articles_count = result.get('articles', 0)
                    
                    # Handle case where articles might be a list (defensive)
                    if isinstance(articles_count, list):
                        articles_count = len(articles_count)
                    elif not isinstance(articles_count, int):
                        logger.warning(f"⚠️  Unexpected articles type for {source_name}: {type(articles_count)}")
                        articles_count = 0
                    
                    error = result.get('error')
                    
                    # Categorize based on status
                    if status == 'success':
                        if articles_count > 0:
                            self.stats['successful'] += 1
                            self.record_fetch_result(source_name, 'success', articles_count)
                        else:
                            self.stats['empty'] += 1
                            self.record_fetch_result(source_name, 'empty', 0)
                    elif status in ['cached', 'empty']:
                        # Cached or explicitly empty (but successful fetch)
                        self.stats['empty'] += 1
                        self.record_fetch_result(source_name, 'empty', 0)
                    else:
                        # Failed, timeout, or other errors
                        self.stats['failed'] += 1
                        self.record_fetch_result(source_name, 'failed', 0, error)
                
                except Exception as e:
                    # Per-source error should not crash entire health tracking
                    logger.warning(f"⚠️  Error processing health for one source: {e}")
                    continue
            
            # Persist if configured
            if self.persistence_file:
                try:
                    self._save()
                except Exception as e:
                    logger.warning(f"⚠️  Failed to persist health data: {e}")
        
        except Exception as e:
            # CRITICAL: Health tracking must never crash the monitoring pipeline
            logger.exception("❌ Feed health tracking failed, continuing without health summary")
            # Reset to safe defaults
            self.stats['total_sources'] = len(results) if results else 0
            self.stats['successful'] = 0
            self.stats['failed'] = 0
            self.stats['empty'] = 0
    
    def get_summary(self) -> Dict:
        """
        Get health summary for current run.
        
        Returns:
            Dict with health metrics
        """
        return {
            'total_sources': self.stats['total_sources'],
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'empty': self.stats['empty'],
            'success_rate': (
                self.stats['successful'] / self.stats['total_sources'] * 100
                if self.stats['total_sources'] > 0 else 0
            )
        }
    
    def get_unhealthy_sources(self, threshold: int = 5) -> List[Dict]:
        """
        Get sources that are consistently empty or failing.
        
        Args:
            threshold: Number of consecutive empty runs to mark unhealthy
            
        Returns:
            List of unhealthy source info dicts
        """
        unhealthy = []
        
        for source_name, stats in self.stats['per_source'].items():
            if stats['consecutive_empty'] >= threshold:
                unhealthy.append({
                    'name': source_name,
                    'consecutive_empty': stats['consecutive_empty'],
                    'total_runs': stats['total_runs'],
                    'successful_runs': stats['successful_runs'],
                    'last_success': stats['last_success'],
                    'last_error': stats['last_error']
                })
        
        return unhealthy
    
    def get_source_health(self, source_name: str) -> Dict:
        """
        Get detailed health info for a specific source.
        
        Args:
            source_name: Name of the source
            
        Returns:
            Dict with source health metrics
        """
        if source_name not in self.stats['per_source']:
            return {'status': 'unknown', 'message': 'No data for this source'}
        
        stats = self.stats['per_source'][source_name]
        
        # Determine health status
        if stats['consecutive_empty'] >= 5:
            status = 'unhealthy'
            message = f"{stats['consecutive_empty']} consecutive empty runs"
        elif stats['consecutive_empty'] >= 3:
            status = 'warning'
            message = f"{stats['consecutive_empty']} consecutive empty runs"
        elif stats['successful_runs'] > 0:
            status = 'healthy'
            message = f"{stats['successful_runs']}/{stats['total_runs']} successful runs"
        else:
            status = 'unknown'
            message = 'No successful runs yet'
        
        return {
            'name': source_name,
            'status': status,
            'message': message,
            **stats
        }
    
    def get_all_sources_health(self) -> List[Dict]:
        """
        Get health info for all sources.
        
        Returns:
            List of source health dicts
        """
        return [
            self.get_source_health(name)
            for name in self.stats['per_source'].keys()
        ]
    
    def print_health_report(self):
        """
        Print a formatted health report to console.
        """
        summary = self.get_summary()
        
        print("\n" + "="*80)
        print("RSS FEED HEALTH REPORT")
        print("="*80)
        
        print(f"\n📊 Overall Summary:")
        print(f"   Total sources: {summary['total_sources']}")
        print(f"   ✅ Successful: {summary['successful']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   📭 Empty: {summary['empty']}")
        print(f"   Success rate: {summary['success_rate']:.1f}%")
        
        # Show unhealthy sources
        unhealthy = self.get_unhealthy_sources(threshold=3)
        if unhealthy:
            print(f"\n⚠️  Unhealthy Sources ({len(unhealthy)}):")
            for source in unhealthy[:10]:  # Show top 10
                print(f"   • {source['name']}: {source['consecutive_empty']} consecutive empty runs")
        else:
            print(f"\n✅ No unhealthy sources detected")
        
        print("="*80 + "\n")
    
    def _save(self):
        """Save health data to persistent storage."""
        try:
            with open(self.persistence_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save health data: {e}")
    
    def _load(self):
        """Load health data from persistent storage."""
        try:
            with open(self.persistence_file, 'r', encoding='utf-8') as f:
                self.stats = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load health data: {e}")
    
    def reset(self):
        """Reset all health tracking data."""
        self.stats = {
            'total_sources': 0,
            'successful': 0,
            'failed': 0,
            'empty': 0,
            'per_source': {}
        }
        if self.persistence_file and os.path.exists(self.persistence_file):
            os.remove(self.persistence_file)


# Global tracker instance
_tracker = None


def get_tracker(persistence_file='feed_health.json'):
    """
    Get the global feed health tracker instance.
    
    Args:
        persistence_file: File for persistent storage
        
    Returns:
        FeedHealthTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = FeedHealthTracker(persistence_file)
    return _tracker


def reset_tracker():
    """Reset the global tracker."""
    global _tracker
    if _tracker:
        _tracker.reset()
    _tracker = None


# ==================== Testing ====================

def _test_health_tracking():
    """Test health tracking functionality"""
    print("=" * 80)
    print("FEED HEALTH TRACKING TEST")
    print("=" * 80)
    
    tracker = FeedHealthTracker()
    
    # Simulate some fetch results
    test_results = [
        {'name': 'BBC News', 'status': 'success', 'articles': [1, 2, 3]},
        {'name': 'CNN', 'status': 'success', 'articles': [1, 2]},
        {'name': 'RT Arabic', 'status': 'empty', 'articles': []},
        {'name': 'Al Jazeera', 'status': 'success', 'articles': [1]},
        {'name': 'Broken Feed', 'status': 'failed', 'error': 'Connection timeout'},
    ]
    
    tracker.process_fetch_results(test_results)
    tracker.print_health_report()
    
    # Simulate consecutive empty runs
    print("\nSimulating 5 consecutive empty runs for RT Arabic...")
    for i in range(5):
        tracker.record_fetch_result('RT Arabic', 'empty', 0)
    
    tracker.print_health_report()
    
    print("✅ Test complete")


if __name__ == "__main__":
    _test_health_tracking()
