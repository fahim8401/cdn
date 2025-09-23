#!/usr/bin/env python3
"""
XenCDN v8.2 - Speed Test Logging Tasks
Background tasks for processing speed test results
"""

import os
import logging
from celery import shared_task
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_speed_test_result(self, test_data):
    """Process and analyze speed test result"""
    try:
        from models import db, SpeedTestLog
        
        # Create speed test log entry
        log_entry = SpeedTestLog(
            test_url=test_data['test_url'],
            test_type=test_data.get('test_type', 'comparison'),
            origin_ttfb_ms=test_data.get('origin_ttfb_ms'),
            origin_load_time_ms=test_data.get('origin_load_time_ms'),
            origin_size_bytes=test_data.get('origin_size_bytes'),
            cdn_ttfb_ms=test_data.get('cdn_ttfb_ms'),
            cdn_load_time_ms=test_data.get('cdn_load_time_ms'),
            cdn_size_bytes=test_data.get('cdn_size_bytes'),
            cache_status=test_data.get('cache_status', 'MISS'),
            edge_location=test_data.get('edge_location'),
            user_ip=test_data.get('user_ip'),
            user_agent=test_data.get('user_agent'),
            improvement_percent=test_data.get('improvement_percent', 0)
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        logger.info(f"Speed test result logged: {test_data['test_url']}")
        
        # Trigger analytics update
        update_speed_test_analytics.delay()
        
        return {
            'success': True,
            'log_id': log_entry.id,
            'test_url': test_data['test_url']
        }
        
    except Exception as e:
        logger.error(f"Failed to process speed test result: {str(e)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (self.request.retries + 1), exc=e)
        
        return {'error': str(e)}

@shared_task
def update_speed_test_analytics():
    """Update speed test analytics and statistics"""
    try:
        from models import db, SpeedTestLog
        from urllib.parse import urlparse
        
        # Get recent tests (last 30 days)
        since_date = datetime.utcnow() - timedelta(days=30)
        recent_tests = SpeedTestLog.query.filter(
            SpeedTestLog.created_at >= since_date,
            SpeedTestLog.test_type == 'comparison',
            SpeedTestLog.improvement_percent.isnot(None)
        ).all()
        
        if not recent_tests:
            return {'message': 'No recent tests to analyze'}
        
        # Analyze by domain
        domain_stats = {}
        
        for test in recent_tests:
            try:
                parsed = urlparse(test.test_url)
                domain = parsed.netloc.lower()
                
                if domain not in domain_stats:
                    domain_stats[domain] = {
                        'test_count': 0,
                        'total_improvement': 0,
                        'avg_improvement': 0,
                        'faster_count': 0,
                        'slower_count': 0,
                        'avg_origin_time': 0,
                        'avg_cdn_time': 0,
                        'total_origin_time': 0,
                        'total_cdn_time': 0
                    }
                
                stats = domain_stats[domain]
                stats['test_count'] += 1
                stats['total_improvement'] += test.improvement_percent or 0
                
                if test.improvement_percent and test.improvement_percent > 0:
                    stats['faster_count'] += 1
                elif test.improvement_percent and test.improvement_percent < 0:
                    stats['slower_count'] += 1
                
                if test.origin_load_time_ms:
                    stats['total_origin_time'] += test.origin_load_time_ms
                if test.cdn_load_time_ms:
                    stats['total_cdn_time'] += test.cdn_load_time_ms
                    
            except Exception as e:
                logger.warning(f"Failed to parse test URL {test.test_url}: {str(e)}")
                continue
        
        # Calculate averages
        for domain, stats in domain_stats.items():
            if stats['test_count'] > 0:
                stats['avg_improvement'] = stats['total_improvement'] / stats['test_count']
                stats['avg_origin_time'] = stats['total_origin_time'] / stats['test_count']
                stats['avg_cdn_time'] = stats['total_cdn_time'] / stats['test_count']
                stats['faster_percentage'] = (stats['faster_count'] / stats['test_count']) * 100
        
        # Store analytics (in production, you might want a separate analytics table)
        logger.info(f"Updated speed test analytics for {len(domain_stats)} domains")
        
        return {
            'success': True,
            'domains_analyzed': len(domain_stats),
            'total_tests': len(recent_tests),
            'top_domains': sorted(domain_stats.items(), key=lambda x: x[1]['test_count'], reverse=True)[:10]
        }
        
    except Exception as e:
        logger.error(f"Failed to update speed test analytics: {str(e)}")
        return {'error': str(e)}

@shared_task
def cleanup_old_speed_tests():
    """Clean up old speed test logs to save space"""
    try:
        from models import db, SpeedTestLog
        
        # Keep logs for 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        old_tests = SpeedTestLog.query.filter(
            SpeedTestLog.created_at < cutoff_date
        ).all()
        
        deleted_count = len(old_tests)
        
        for test in old_tests:
            db.session.delete(test)
        
        db.session.commit()
        
        logger.info(f"Cleaned up {deleted_count} old speed test logs")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old speed tests: {str(e)}")
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def generate_speed_test_report(self, domain_filter=None, days=30):
    """Generate detailed speed test performance report"""
    try:
        from models import SpeedTestLog
        from urllib.parse import urlparse
        import json
        
        # Get tests for the period
        since_date = datetime.utcnow() - timedelta(days=days)
        query = SpeedTestLog.query.filter(
            SpeedTestLog.created_at >= since_date,
            SpeedTestLog.test_type == 'comparison',
            SpeedTestLog.improvement_percent.isnot(None)
        )
        
        if domain_filter:
            query = query.filter(SpeedTestLog.test_url.ilike(f'%{domain_filter}%'))
        
        tests = query.all()
        
        if not tests:
            return {'message': 'No tests found for the specified criteria'}
        
        # Calculate overall statistics
        total_tests = len(tests)
        improvements = [test.improvement_percent for test in tests if test.improvement_percent is not None]
        
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0
        faster_tests = len([i for i in improvements if i > 0])
        slower_tests = len([i for i in improvements if i < 0])
        
        # Performance distribution
        performance_buckets = {
            'much_faster': len([i for i in improvements if i >= 50]),  # 50%+ faster
            'faster': len([i for i in improvements if 10 <= i < 50]),  # 10-50% faster
            'similar': len([i for i in improvements if -10 < i < 10]), # Within 10%
            'slower': len([i for i in improvements if -50 < i <= -10]), # 10-50% slower
            'much_slower': len([i for i in improvements if i <= -50])   # 50%+ slower
        }
        
        # Cache performance analysis
        cache_hits = len([test for test in tests if test.cache_status == 'HIT'])
        cache_misses = len([test for test in tests if test.cache_status == 'MISS'])
        cache_hit_ratio = (cache_hits / total_tests * 100) if total_tests > 0 else 0
        
        # Size analysis
        origin_sizes = [test.origin_size_bytes for test in tests if test.origin_size_bytes]
        cdn_sizes = [test.cdn_size_bytes for test in tests if test.cdn_size_bytes]
        
        avg_origin_size = sum(origin_sizes) / len(origin_sizes) if origin_sizes else 0
        avg_cdn_size = sum(cdn_sizes) / len(cdn_sizes) if cdn_sizes else 0
        size_reduction = ((avg_origin_size - avg_cdn_size) / avg_origin_size * 100) if avg_origin_size > 0 else 0
        
        # Time analysis
        origin_times = [test.origin_load_time_ms for test in tests if test.origin_load_time_ms]
        cdn_times = [test.cdn_load_time_ms for test in tests if test.cdn_load_time_ms]
        
        avg_origin_time = sum(origin_times) / len(origin_times) if origin_times else 0
        avg_cdn_time = sum(cdn_times) / len(cdn_times) if cdn_times else 0
        
        # TTFB analysis
        origin_ttfb = [test.origin_ttfb_ms for test in tests if test.origin_ttfb_ms]
        cdn_ttfb = [test.cdn_ttfb_ms for test in tests if test.cdn_ttfb_ms]
        
        avg_origin_ttfb = sum(origin_ttfb) / len(origin_ttfb) if origin_ttfb else 0
        avg_cdn_ttfb = sum(cdn_ttfb) / len(cdn_ttfb) if cdn_ttfb else 0
        ttfb_improvement = ((avg_origin_ttfb - avg_cdn_ttfb) / avg_origin_ttfb * 100) if avg_origin_ttfb > 0 else 0
        
        # Top tested domains
        domain_counts = {}
        for test in tests:
            try:
                parsed = urlparse(test.test_url)
                domain = parsed.netloc.lower()
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            except:
                continue
        
        top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        report = {
            'report_period': {
                'start_date': since_date.isoformat(),
                'end_date': datetime.utcnow().isoformat(),
                'days': days
            },
            'overview': {
                'total_tests': total_tests,
                'avg_improvement': round(avg_improvement, 1),
                'faster_tests': faster_tests,
                'slower_tests': slower_tests,
                'faster_percentage': round((faster_tests / total_tests * 100), 1) if total_tests > 0 else 0
            },
            'performance_distribution': performance_buckets,
            'cache_performance': {
                'cache_hit_ratio': round(cache_hit_ratio, 1),
                'cache_hits': cache_hits,
                'cache_misses': cache_misses
            },
            'size_analysis': {
                'avg_origin_size_kb': round(avg_origin_size / 1024, 1),
                'avg_cdn_size_kb': round(avg_cdn_size / 1024, 1),
                'size_reduction_percent': round(size_reduction, 1)
            },
            'time_analysis': {
                'avg_origin_load_time_ms': round(avg_origin_time, 1),
                'avg_cdn_load_time_ms': round(avg_cdn_time, 1),
                'avg_origin_ttfb_ms': round(avg_origin_ttfb, 1),
                'avg_cdn_ttfb_ms': round(avg_cdn_ttfb, 1),
                'ttfb_improvement_percent': round(ttfb_improvement, 1)
            },
            'top_domains': [{'domain': domain, 'test_count': count} for domain, count in top_domains]
        }
        
        logger.info(f"Generated speed test report for {total_tests} tests over {days} days")
        
        return {
            'success': True,
            'report': report
        }
        
    except Exception as e:
        logger.error(f"Failed to generate speed test report: {str(e)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=e)
        
        return {'error': str(e)}

@shared_task
def monitor_speed_test_performance():
    """Monitor overall speed test performance and alert if issues"""
    try:
        from models import SpeedTestLog
        
        # Check recent tests (last 24 hours)
        since_date = datetime.utcnow() - timedelta(hours=24)
        recent_tests = SpeedTestLog.query.filter(
            SpeedTestLog.created_at >= since_date,
            SpeedTestLog.test_type == 'comparison',
            SpeedTestLog.improvement_percent.isnot(None)
        ).all()
        
        if len(recent_tests) < 10:  # Not enough data
            return {'message': 'Insufficient test data for monitoring'}
        
        # Calculate performance metrics
        improvements = [test.improvement_percent for test in recent_tests if test.improvement_percent is not None]
        avg_improvement = sum(improvements) / len(improvements)
        slower_tests = len([i for i in improvements if i < -10])  # More than 10% slower
        slower_percentage = (slower_tests / len(improvements)) * 100
        
        # Alert conditions
        alerts = []
        
        if avg_improvement < 0:
            alerts.append(f"Average CDN performance is slower than origin ({avg_improvement:.1f}%)")
        
        if slower_percentage > 30:  # More than 30% of tests are significantly slower
            alerts.append(f"High percentage of slower tests: {slower_percentage:.1f}%")
        
        # Check for consistent failures
        failed_tests = len([test for test in recent_tests if test.improvement_percent is None])
        if failed_tests > len(recent_tests) * 0.1:  # More than 10% failed
            alerts.append(f"High test failure rate: {failed_tests} out of {len(recent_tests)} tests failed")
        
        if alerts:
            logger.warning(f"Speed test performance alerts: {'; '.join(alerts)}")
            
            # In production, you might want to send alerts to monitoring systems
            # or notify administrators
            
        return {
            'success': True,
            'total_tests': len(recent_tests),
            'avg_improvement': round(avg_improvement, 1),
            'slower_percentage': round(slower_percentage, 1),
            'alerts': alerts
        }
        
    except Exception as e:
        logger.error(f"Failed to monitor speed test performance: {str(e)}")
        return {'error': str(e)}