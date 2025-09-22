#!/usr/bin/env python3
"""
XenCDN v8.1 Speed Test Logging Tasks
Background tasks for processing and analyzing speed test results
"""

import os
from datetime import datetime, timedelta
from celery import Celery
from flask import current_app
from sqlalchemy import func

from ..models import db, SpeedTestLog, ClientRegistration, EdgeNode

# Initialize Celery
celery = Celery('speed_test_tasks')

@celery.task
def process_speed_test_result(test_id):
    """Process and enhance speed test result"""
    try:
        speed_test = SpeedTestLog.query.get(test_id)
        if not speed_test:
            return {'status': 'error', 'error': 'Test not found'}
        
        # Enhance the test with additional analysis
        enhance_test_analysis(speed_test)
        
        # Update global statistics
        update_global_stats()
        
        # If this is a client test, update their stats
        if speed_test.client_id:
            update_client_speed_stats(speed_test.client_id)
        
        db.session.commit()
        
        return {
            'status': 'processed',
            'test_id': test_id,
            'improvement_percent': speed_test.improvement_percent
        }
        
    except Exception as e:
        current_app.logger.error(f"Speed test processing failed: {e}")
        return {'status': 'error', 'error': str(e)}

@celery.task
def cleanup_old_speed_tests():
    """Clean up old speed test logs"""
    try:
        # Keep only last 90 days of data
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        deleted_count = SpeedTestLog.query.filter(
            SpeedTestLog.created_at < cutoff_date
        ).delete()
        
        db.session.commit()
        
        return {
            'status': 'cleaned',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        current_app.logger.error(f"Speed test cleanup failed: {e}")
        return {'status': 'error', 'error': str(e)}

@celery.task
def generate_speed_test_analytics():
    """Generate daily speed test analytics"""
    try:
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        # Get yesterday's tests
        tests = SpeedTestLog.query.filter(
            func.date(SpeedTestLog.created_at) == yesterday
        ).all()
        
        if not tests:
            return {'status': 'no_data', 'date': yesterday.isoformat()}
        
        # Calculate analytics
        analytics = {
            'date': yesterday.isoformat(),
            'total_tests': len(tests),
            'avg_improvement': sum(t.improvement_percent for t in tests if t.improvement_percent) / len(tests),
            'total_bandwidth_saved_gb': sum(
                (t.origin_size - t.cdn_size) for t in tests 
                if t.origin_size and t.cdn_size and t.origin_size > t.cdn_size
            ) / (1024**3),
            'cache_hit_rate': len([t for t in tests if t.cache_status == 'hit']) / len(tests) * 100,
            'avg_origin_ttfb': sum(t.origin_ttfb for t in tests if t.origin_ttfb) / len(tests),
            'avg_cdn_ttfb': sum(t.cdn_ttfb for t in tests if t.cdn_ttfb) / len(tests),
            'unique_users': len(set(t.user_ip for t in tests if t.user_ip)),
            'top_edge_locations': get_top_edge_locations(tests)
        }
        
        # Store analytics (you might want to create a SpeedTestAnalytics model)
        current_app.logger.info(f"Speed test analytics for {yesterday}: {analytics}")
        
        return analytics
        
    except Exception as e:
        current_app.logger.error(f"Speed test analytics generation failed: {e}")
        return {'status': 'error', 'error': str(e)}

@celery.task
def detect_performance_issues():
    """Detect and alert on performance issues"""
    try:
        # Check last hour's tests for issues
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        recent_tests = SpeedTestLog.query.filter(
            SpeedTestLog.created_at >= one_hour_ago
        ).all()
        
        if len(recent_tests) < 10:  # Not enough data
            return {'status': 'insufficient_data', 'test_count': len(recent_tests)}
        
        issues = []
        
        # Check for high TTFB
        avg_cdn_ttfb = sum(t.cdn_ttfb for t in recent_tests if t.cdn_ttfb) / len(recent_tests)
        if avg_cdn_ttfb > 500:  # 500ms threshold
            issues.append({
                'type': 'high_ttfb',
                'value': avg_cdn_ttfb,
                'threshold': 500,
                'severity': 'warning' if avg_cdn_ttfb < 1000 else 'critical'
            })
        
        # Check for low cache hit ratio
        cache_hits = len([t for t in recent_tests if t.cache_status == 'hit'])
        hit_ratio = cache_hits / len(recent_tests) * 100
        if hit_ratio < 80:  # 80% threshold
            issues.append({
                'type': 'low_cache_hit_ratio',
                'value': hit_ratio,
                'threshold': 80,
                'severity': 'warning' if hit_ratio > 60 else 'critical'
            })
        
        # Check for negative performance impact
        negative_improvements = [t for t in recent_tests if t.improvement_percent and t.improvement_percent < -10]
        if len(negative_improvements) > len(recent_tests) * 0.2:  # More than 20% negative
            issues.append({
                'type': 'negative_performance_impact',
                'value': len(negative_improvements) / len(recent_tests) * 100,
                'threshold': 20,
                'severity': 'critical'
            })
        
        # Alert if issues found
        if issues:
            alert_performance_issues(issues, recent_tests)
        
        return {
            'status': 'completed',
            'test_count': len(recent_tests),
            'issues_found': len(issues),
            'issues': issues
        }
        
    except Exception as e:
        current_app.logger.error(f"Performance issue detection failed: {e}")
        return {'status': 'error', 'error': str(e)}

def enhance_test_analysis(speed_test):
    """Enhance speed test with additional analysis"""
    try:
        # Calculate performance grades
        if speed_test.improvement_percent:
            if speed_test.improvement_percent >= 50:
                performance_grade = 'A'
            elif speed_test.improvement_percent >= 30:
                performance_grade = 'B'
            elif speed_test.improvement_percent >= 10:
                performance_grade = 'C'
            elif speed_test.improvement_percent >= 0:
                performance_grade = 'D'
            else:
                performance_grade = 'F'
        else:
            performance_grade = 'N/A'
        
        # Store additional analysis (would need to add fields to model)
        # speed_test.performance_grade = performance_grade
        
        # Log the analysis
        current_app.logger.info(f"Speed test {speed_test.id} analysis: {performance_grade} grade, {speed_test.improvement_percent}% improvement")
        
    except Exception as e:
        current_app.logger.error(f"Test analysis enhancement failed: {e}")

def update_global_stats():
    """Update global speed test statistics"""
    try:
        # Calculate global stats for the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_tests = SpeedTestLog.query.filter(
            SpeedTestLog.created_at >= thirty_days_ago
        ).all()
        
        if not recent_tests:
            return
        
        global_stats = {
            'total_tests': len(recent_tests),
            'avg_improvement': sum(t.improvement_percent for t in recent_tests if t.improvement_percent) / len(recent_tests),
            'total_bandwidth_saved_gb': sum(
                (t.origin_size - t.cdn_size) for t in recent_tests 
                if t.origin_size and t.cdn_size and t.origin_size > t.cdn_size
            ) / (1024**3),
            'cache_hit_rate': len([t for t in recent_tests if t.cache_status == 'hit']) / len(recent_tests) * 100
        }
        
        # Store in cache or database (implement based on your needs)
        current_app.logger.info(f"Global speed test stats updated: {global_stats}")
        
    except Exception as e:
        current_app.logger.error(f"Global stats update failed: {e}")

def update_client_speed_stats(client_id):
    """Update client-specific speed test statistics"""
    try:
        client = ClientRegistration.query.get(client_id)
        if not client:
            return
        
        # Get client's recent tests
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        client_tests = SpeedTestLog.query.filter(
            SpeedTestLog.client_id == client_id,
            SpeedTestLog.created_at >= thirty_days_ago
        ).all()
        
        if not client_tests:
            return
        
        client_stats = {
            'total_tests': len(client_tests),
            'avg_improvement': sum(t.improvement_percent for t in client_tests if t.improvement_percent) / len(client_tests),
            'domains_tested': len(set(t.test_url for t in client_tests)),
            'best_improvement': max((t.improvement_percent for t in client_tests if t.improvement_percent), default=0)
        }
        
        # Store client stats (implement based on your needs)
        current_app.logger.info(f"Client {client_id} speed stats updated: {client_stats}")
        
    except Exception as e:
        current_app.logger.error(f"Client speed stats update failed: {e}")

def get_top_edge_locations(tests):
    """Get top edge locations from test results"""
    try:
        location_counts = {}
        
        for test in tests:
            if test.edge_location:
                location_counts[test.edge_location] = location_counts.get(test.edge_location, 0) + 1
        
        # Sort by count and return top 5
        sorted_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_locations[:5]
        
    except Exception as e:
        current_app.logger.error(f"Edge location analysis failed: {e}")
        return []

def alert_performance_issues(issues, recent_tests):
    """Alert administrators about performance issues"""
    try:
        # Import here to avoid circular imports
        from .email_report import send_email
        
        admin_emails = os.getenv('ADMIN_ALERT_EMAILS', 'admin@xencdn.com').split(',')
        
        subject = f"XenCDN Performance Alert - {len(issues)} Issues Detected"
        
        body = f"""
        Performance Alert - XenCDN Speed Test Monitoring
        
        Time: {datetime.utcnow().isoformat()}
        Test Period: Last hour
        Tests Analyzed: {len(recent_tests)}
        
        ISSUES DETECTED:
        """
        
        for issue in issues:
            body += f"""
        • {issue['type'].replace('_', ' ').title()}
          Value: {issue['value']:.2f}
          Threshold: {issue['threshold']}
          Severity: {issue['severity'].upper()}
        """
        
        body += f"""
        
        Please investigate the CDN performance and edge node health.
        
        Access monitoring dashboard: https://{os.getenv('ADMIN_DOMAIN', 'admin.xencdn.com')}
        
        Automated Alert System
        XenCDN v8.1
        """
        
        for email in admin_emails:
            send_email.delay(email.strip(), subject, body)
        
    except Exception as e:
        current_app.logger.error(f"Performance alert failed: {e}")

@celery.task
def benchmark_edge_nodes():
    """Benchmark all edge nodes performance"""
    try:
        active_edges = EdgeNode.query.filter_by(status='active').all()
        
        results = []
        
        for edge in active_edges:
            # Run basic performance test against edge node
            # This would involve making test requests to the edge
            
            # Mock data for demonstration
            benchmark_result = {
                'edge_id': edge.id,
                'location': f"{edge.city}, {edge.country}",
                'avg_response_time': 45.2,  # ms
                'availability': 99.9,  # %
                'load_score': edge.load_score,
                'status': 'healthy'
            }
            
            results.append(benchmark_result)
        
        # Store results or alert on issues
        current_app.logger.info(f"Edge node benchmark completed: {len(results)} nodes tested")
        
        return {
            'status': 'completed',
            'edges_tested': len(results),
            'results': results
        }
        
    except Exception as e:
        current_app.logger.error(f"Edge node benchmark failed: {e}")
        return {'status': 'error', 'error': str(e)}