"""
Monitoring & Health Check System
Tracks system performance, source health, and generates alerts
"""
import time
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class SourceHealthMonitor:
    """
    Monitor RSS source health and performance
    Tracks success rates, latency, and failures per source
    """
    
    def __init__(self):
        self.source_stats = defaultdict(lambda: {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'timeout': 0,
            'total_latency': 0,
            'last_success': None,
            'last_failure': None,
            'failure_reasons': []
        })
        
        self.country_stats = defaultdict(lambda: {
            'sources': set(),
            'total_articles': 0,
            'successful_sources': 0,
            'failed_sources': 0
        })
    
    def record_fetch(
        self,
        source_name: str,
        country: str,
        status: str,
        latency: float,
        articles_count: int = 0,
        error: Optional[str] = None
    ):
        """
        Record a fetch attempt
        
        Args:
            source_name: Name of the source
            country: Country name
            status: 'success', 'failed', 'timeout'
            latency: Time taken in seconds
            articles_count: Number of articles fetched
            error: Error message if failed
        """
        stats = self.source_stats[source_name]
        stats['total_requests'] += 1
        stats['total_latency'] += latency
        
        if status == 'success':
            stats['successful'] += 1
            stats['last_success'] = datetime.now().isoformat()
            self.country_stats[country]['successful_sources'] += 1
            self.country_stats[country]['total_articles'] += articles_count
        elif status == 'timeout':
            stats['timeout'] += 1
            stats['last_failure'] = datetime.now().isoformat()
            self.country_stats[country]['failed_sources'] += 1
        else:  # failed
            stats['failed'] += 1
            stats['last_failure'] = datetime.now().isoformat()
            if error:
                stats['failure_reasons'].append({
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                })
            self.country_stats[country]['failed_sources'] += 1
        
        # Track country
        self.country_stats[country]['sources'].add(source_name)
    
    def get_source_health(self, source_name: str) -> Dict:
        """Get health metrics for a source"""
        stats = self.source_stats[source_name]
        
        if stats['total_requests'] == 0:
            return {'status': 'unknown', 'message': 'No data'}
        
        success_rate = stats['successful'] / stats['total_requests'] * 100
        avg_latency = stats['total_latency'] / stats['total_requests']
        
        # Determine health status
        if success_rate >= 90:
            status = 'healthy'
        elif success_rate >= 70:
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        return {
            'status': status,
            'success_rate': success_rate,
            'avg_latency': avg_latency,
            'total_requests': stats['total_requests'],
            'successful': stats['successful'],
            'failed': stats['failed'],
            'timeout': stats['timeout'],
            'last_success': stats['last_success'],
            'last_failure': stats['last_failure']
        }
    
    def get_country_health(self, country: str) -> Dict:
        """Get health metrics for a country"""
        stats = self.country_stats[country]
        
        if not stats['sources']:
            return {'status': 'unknown', 'message': 'No sources'}
        
        total_sources = len(stats['sources'])
        success_rate = (
            stats['successful_sources'] / total_sources * 100
            if total_sources > 0 else 0
        )
        
        # Determine health status
        if success_rate >= 80:
            status = 'healthy'
        elif success_rate >= 50:
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        return {
            'status': status,
            'success_rate': success_rate,
            'total_sources': total_sources,
            'successful_sources': stats['successful_sources'],
            'failed_sources': stats['failed_sources'],
            'total_articles': stats['total_articles']
        }
    
    def get_unhealthy_sources(self, threshold: float = 70.0) -> List[Dict]:
        """Get list of sources with success rate below threshold"""
        unhealthy = []
        
        for source_name, stats in self.source_stats.items():
            if stats['total_requests'] == 0:
                continue
            
            success_rate = stats['successful'] / stats['total_requests'] * 100
            
            if success_rate < threshold:
                unhealthy.append({
                    'source': source_name,
                    'success_rate': success_rate,
                    'failures': stats['failed'] + stats['timeout'],
                    'last_failure': stats['last_failure']
                })
        
        return sorted(unhealthy, key=lambda x: x['success_rate'])
    
    def get_system_health(self) -> Dict:
        """Get overall system health"""
        total_sources = len(self.source_stats)
        
        if total_sources == 0:
            return {'status': 'unknown', 'message': 'No data'}
        
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        
        for source_name in self.source_stats:
            health = self.get_source_health(source_name)
            if health['status'] == 'healthy':
                healthy_count += 1
            elif health['status'] == 'degraded':
                degraded_count += 1
            else:
                unhealthy_count += 1
        
        overall_success_rate = healthy_count / total_sources * 100
        
        if overall_success_rate >= 90:
            status = 'healthy'
        elif overall_success_rate >= 70:
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        return {
            'status': status,
            'total_sources': total_sources,
            'healthy': healthy_count,
            'degraded': degraded_count,
            'unhealthy': unhealthy_count,
            'overall_success_rate': overall_success_rate
        }
    
    def generate_report(self) -> str:
        """Generate health report"""
        system_health = self.get_system_health()
        unhealthy = self.get_unhealthy_sources(threshold=70)
        
        report = []
        report.append("=" * 80)
        report.append("📊 SYSTEM HEALTH REPORT")
        report.append("=" * 80)
        report.append(f"Status: {system_health['status'].upper()}")
        report.append(f"Total Sources: {system_health['total_sources']}")
        report.append(f"  ✅ Healthy: {system_health['healthy']} ({system_health['healthy']/system_health['total_sources']*100:.1f}%)")
        report.append(f"  ⚠️  Degraded: {system_health['degraded']}")
        report.append(f"  ❌ Unhealthy: {system_health['unhealthy']}")
        report.append("")
        
        # Country breakdown
        report.append("📍 COUNTRY BREAKDOWN:")
        for country, stats in sorted(self.country_stats.items()):
            health = self.get_country_health(country)
            report.append(f"  {country}:")
            report.append(f"    Sources: {health['total_sources']}")
            report.append(f"    Success: {health['successful_sources']}/{health['total_sources']} ({health['success_rate']:.1f}%)")
            report.append(f"    Articles: {health['total_articles']}")
        
        report.append("")
        
        # Unhealthy sources
        if unhealthy:
            report.append(f"⚠️  UNHEALTHY SOURCES ({len(unhealthy)}):")
            for item in unhealthy[:10]:  # Top 10
                report.append(f"  {item['source']}: {item['success_rate']:.1f}% success")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def print_report(self):
        """Print health report"""
        logger.info("\n" + self.generate_report())


class PerformanceMonitor:
    """
    Monitor system performance metrics
    """
    
    def __init__(self):
        self.metrics = {
            'fetch': {'total_time': 0, 'count': 0},
            'translation': {'total_time': 0, 'count': 0},
            'deduplication': {'total_time': 0, 'count': 0},
            'save': {'total_time': 0, 'count': 0}
        }
    
    def record_operation(self, operation: str, duration: float):
        """
        Record operation duration
        
        Args:
            operation: Operation name ('fetch', 'translation', 'deduplication', 'save')
            duration: Duration in seconds
        """
        if operation in self.metrics:
            self.metrics[operation]['total_time'] += duration
            self.metrics[operation]['count'] += 1
    
    def get_average_time(self, operation: str) -> float:
        """Get average time for operation"""
        if operation in self.metrics and self.metrics[operation]['count'] > 0:
            return self.metrics[operation]['total_time'] / self.metrics[operation]['count']
        return 0.0
    
    def get_report(self) -> Dict:
        """Get performance report"""
        return {
            operation: {
                'avg_time': self.get_average_time(operation),
                'total_time': data['total_time'],
                'count': data['count']
            }
            for operation, data in self.metrics.items()
        }
    
    def print_report(self):
        """Print performance report"""
        report = self.get_report()
        
        logger.info("=" * 80)
        logger.info("⚡ PERFORMANCE REPORT")
        logger.info("=" * 80)
        
        for operation, metrics in report.items():
            logger.info(f"{operation.upper()}:")
            logger.info(f"  Avg time: {metrics['avg_time']:.3f}s")
            logger.info(f"  Total time: {metrics['total_time']:.2f}s")
            logger.info(f"  Count: {metrics['count']}")
        
        logger.info("=" * 80)


# Global instances
_source_health_monitor = SourceHealthMonitor()
_performance_monitor = PerformanceMonitor()


def get_source_health_monitor() -> SourceHealthMonitor:
    """Get source health monitor instance"""
    return _source_health_monitor


def get_performance_monitor() -> PerformanceMonitor:
    """Get performance monitor instance"""
    return _performance_monitor


def generate_health_report() -> str:
    """Generate comprehensive health report"""
    return _source_health_monitor.generate_report()


def generate_performance_report() -> Dict:
    """Generate performance report"""
    return _performance_monitor.get_report()


# Test
if __name__ == "__main__":
    monitor = SourceHealthMonitor()
    
    # Simulate some fetches
    monitor.record_fetch('BBC News', 'بريطانيا', 'success', 2.5, 50)
    monitor.record_fetch('CNN', 'أمريكا', 'success', 3.0, 40)
    monitor.record_fetch('Japan Times', 'اليابان', 'timeout', 10.0, 0)
    monitor.record_fetch('Dead Feed', 'دولة', 'failed', 1.0, 0, 'Connection error')
    
    # Generate report
    monitor.print_report()
    
    # Performance
    perf = PerformanceMonitor()
    perf.record_operation('fetch', 120.5)
    perf.record_operation('translation', 45.2)
    perf.print_report()
