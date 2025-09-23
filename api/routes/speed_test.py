#!/usr/bin/env python3
"""
XenCDN v8.2 - Speed Test API Routes
Public speed test tool for comparing origin vs CDN performance
"""

import os
import time
import requests
import json
from flask import Blueprint, request, jsonify
from datetime import datetime
from urllib.parse import urlparse
import ipaddress

from models import db, SpeedTestLog

speed_test_bp = Blueprint('speed_test', __name__)

# Speed test configuration
MAX_TEST_SIZE_MB = 10  # Maximum file size to test
TIMEOUT_SECONDS = 30   # Request timeout
ALLOWED_SCHEMES = ['http', 'https']

def validate_url(url):
    """Validate test URL for security"""
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False, "Only HTTP and HTTPS URLs are allowed"
        
        # Check for localhost/private IPs
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback:
                return False, "Private and localhost URLs are not allowed"
        except:
            # It's a domain name, which is fine
            pass
        
        # Block certain domains/patterns
        blocked_domains = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
        if parsed.hostname in blocked_domains:
            return False, "Blocked domain"
        
        return True, "URL is valid"
    
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"

def perform_speed_test(url, use_cdn=False):
    """Perform speed test on a URL"""
    try:
        headers = {
            'User-Agent': 'XenCDN-SpeedTest/1.0',
            'Accept': '*/*',
            'Cache-Control': 'no-cache' if not use_cdn else 'max-age=0'
        }
        
        # Add CDN headers if testing CDN
        if use_cdn:
            headers['X-CDN-Test'] = 'true'
            
        # Record start time
        start_time = time.time()
        
        # Make request
        response = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
            stream=True,
            allow_redirects=True
        )
        
        # Record TTFB (Time to First Byte)
        ttfb = time.time() - start_time
        
        # Check content size
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > MAX_TEST_SIZE_MB * 1024 * 1024:
            return {
                'success': False,
                'error': f'File too large (max {MAX_TEST_SIZE_MB}MB)'
            }
        
        # Download content (with size limit)
        content = b''
        downloaded_size = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            downloaded_size += len(chunk)
            
            # Stop if too large
            if downloaded_size > MAX_TEST_SIZE_MB * 1024 * 1024:
                break
        
        # Record total time
        total_time = time.time() - start_time
        
        # Get cache status from headers
        cache_status = 'MISS'
        if use_cdn:
            cache_status = response.headers.get('X-Cache', 'MISS').upper()
            if 'HIT' in cache_status:
                cache_status = 'HIT'
            elif 'MISS' in cache_status:
                cache_status = 'MISS'
            else:
                cache_status = 'BYPASS'
        
        return {
            'success': True,
            'status_code': response.status_code,
            'ttfb_ms': round(ttfb * 1000, 2),
            'total_time_ms': round(total_time * 1000, 2),
            'size_bytes': len(content),
            'cache_status': cache_status,
            'headers': dict(response.headers)
        }
    
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': 'Request timeout'
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Request failed: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Test failed: {str(e)}'
        }

@speed_test_bp.route('/api/speed-test/test', methods=['POST'])
def run_speed_test():
    """Run speed test comparing origin vs CDN"""
    try:
        data = request.get_json()
        test_url = data.get('url', '').strip()
        test_type = data.get('type', 'comparison')  # 'comparison' or 'single'
        
        if not test_url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Validate URL
        is_valid, validation_message = validate_url(test_url)
        if not is_valid:
            return jsonify({'error': validation_message}), 400
        
        # Get client info
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        results = {
            'test_url': test_url,
            'test_type': test_type,
            'timestamp': datetime.utcnow().isoformat(),
            'client_ip': client_ip
        }
        
        if test_type == 'comparison':
            # Test origin server
            origin_result = perform_speed_test(test_url, use_cdn=False)
            
            # Test via CDN (construct CDN URL)
            cdn_url = test_url
            # In production, you'd convert to your CDN domain
            # cdn_url = test_url.replace(parsed_url.netloc, f'{parsed_url.netloc}.cdn.xencdn.com')
            
            cdn_result = perform_speed_test(cdn_url, use_cdn=True)
            
            results['origin'] = origin_result
            results['cdn'] = cdn_result
            
            # Calculate improvement
            if origin_result['success'] and cdn_result['success']:
                origin_time = origin_result['total_time_ms']
                cdn_time = cdn_result['total_time_ms']
                
                if origin_time > 0:
                    improvement = ((origin_time - cdn_time) / origin_time) * 100
                    results['improvement_percent'] = round(improvement, 1)
                    results['faster_by_ms'] = round(origin_time - cdn_time, 1)
                    
                    # Determine which is faster
                    if improvement > 0:
                        results['winner'] = 'cdn'
                        results['summary'] = f'CDN is {abs(improvement):.1f}% faster'
                    else:
                        results['winner'] = 'origin'
                        results['summary'] = f'Origin is {abs(improvement):.1f}% faster'
                else:
                    results['winner'] = 'tie'
                    results['summary'] = 'Performance is similar'
            
        else:
            # Single test
            single_result = perform_speed_test(test_url, use_cdn=data.get('use_cdn', False))
            results['result'] = single_result
        
        # Log the test
        try:
            log_entry = SpeedTestLog(
                test_url=test_url,
                test_type=test_type,
                user_ip=client_ip,
                user_agent=user_agent
            )
            
            if test_type == 'comparison' and results.get('origin', {}).get('success') and results.get('cdn', {}).get('success'):
                log_entry.origin_ttfb_ms = results['origin']['ttfb_ms']
                log_entry.origin_load_time_ms = results['origin']['total_time_ms']
                log_entry.origin_size_bytes = results['origin']['size_bytes']
                log_entry.cdn_ttfb_ms = results['cdn']['ttfb_ms']
                log_entry.cdn_load_time_ms = results['cdn']['total_time_ms']
                log_entry.cdn_size_bytes = results['cdn']['size_bytes']
                log_entry.cache_status = results['cdn']['cache_status']
                log_entry.improvement_percent = results.get('improvement_percent', 0)
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            # Don't fail the test if logging fails
            print(f"Failed to log speed test: {e}")
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@speed_test_bp.route('/api/speed-test/validate-url', methods=['POST'])
def validate_test_url():
    """Validate URL before testing"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        is_valid, message = validate_url(url)
        
        if is_valid:
            # Try to fetch headers to check if URL is accessible
            try:
                response = requests.head(url, timeout=10, allow_redirects=True)
                content_length = response.headers.get('content-length')
                content_type = response.headers.get('content-type', '')
                
                return jsonify({
                    'valid': True,
                    'message': 'URL is valid and accessible',
                    'info': {
                        'status_code': response.status_code,
                        'content_type': content_type,
                        'content_length': content_length,
                        'redirected': response.url != url,
                        'final_url': response.url
                    }
                })
            
            except Exception as e:
                return jsonify({
                    'valid': False,
                    'message': f'URL is not accessible: {str(e)}'
                })
        else:
            return jsonify({
                'valid': False,
                'message': message
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@speed_test_bp.route('/api/speed-test/stats', methods=['GET'])
def get_speed_test_stats():
    """Get speed test statistics"""
    try:
        # Get query parameters
        days = int(request.args.get('days', 7))
        
        # Get recent tests
        from datetime import timedelta
        since_date = datetime.utcnow() - timedelta(days=days)
        
        tests = SpeedTestLog.query.filter(
            SpeedTestLog.created_at >= since_date,
            SpeedTestLog.test_type == 'comparison',
            SpeedTestLog.improvement_percent.isnot(None)
        ).all()
        
        if not tests:
            return jsonify({
                'stats': {
                    'total_tests': 0,
                    'avg_improvement': 0,
                    'tests_faster': 0,
                    'tests_slower': 0,
                    'avg_ttfb_improvement': 0,
                    'daily_stats': []
                }
            })
        
        # Calculate statistics
        total_tests = len(tests)
        improvements = [test.improvement_percent for test in tests if test.improvement_percent is not None]
        
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0
        tests_faster = len([i for i in improvements if i > 0])
        tests_slower = len([i for i in improvements if i < 0])
        
        # TTFB improvement
        ttfb_improvements = []
        for test in tests:
            if test.origin_ttfb_ms and test.cdn_ttfb_ms:
                ttfb_imp = ((test.origin_ttfb_ms - test.cdn_ttfb_ms) / test.origin_ttfb_ms) * 100
                ttfb_improvements.append(ttfb_imp)
        
        avg_ttfb_improvement = sum(ttfb_improvements) / len(ttfb_improvements) if ttfb_improvements else 0
        
        # Daily breakdown
        daily_stats = {}
        for test in tests:
            date_str = test.created_at.date().isoformat()
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    'date': date_str,
                    'tests': 0,
                    'avg_improvement': 0,
                    'improvements': []
                }
            
            daily_stats[date_str]['tests'] += 1
            if test.improvement_percent is not None:
                daily_stats[date_str]['improvements'].append(test.improvement_percent)
        
        # Calculate daily averages
        for date_str, day_data in daily_stats.items():
            if day_data['improvements']:
                day_data['avg_improvement'] = sum(day_data['improvements']) / len(day_data['improvements'])
            del day_data['improvements']  # Remove raw data
        
        stats = {
            'total_tests': total_tests,
            'avg_improvement': round(avg_improvement, 1),
            'tests_faster': tests_faster,
            'tests_slower': tests_slower,
            'faster_percentage': round((tests_faster / total_tests) * 100, 1) if total_tests > 0 else 0,
            'avg_ttfb_improvement': round(avg_ttfb_improvement, 1),
            'daily_stats': list(daily_stats.values())
        }
        
        return jsonify({'stats': stats})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@speed_test_bp.route('/api/speed-test/top-domains', methods=['GET'])
def get_top_tested_domains():
    """Get most tested domains"""
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 10)), 50)
        days = int(request.args.get('days', 30))
        
        # Get recent tests
        from datetime import timedelta
        since_date = datetime.utcnow() - timedelta(days=days)
        
        tests = SpeedTestLog.query.filter(
            SpeedTestLog.created_at >= since_date
        ).all()
        
        # Count by domain
        domain_counts = {}
        domain_improvements = {}
        
        for test in tests:
            try:
                parsed = urlparse(test.test_url)
                domain = parsed.netloc.lower()
                
                if domain not in domain_counts:
                    domain_counts[domain] = 0
                    domain_improvements[domain] = []
                
                domain_counts[domain] += 1
                
                if test.improvement_percent is not None:
                    domain_improvements[domain].append(test.improvement_percent)
            
            except:
                continue
        
        # Sort by count and calculate averages
        top_domains = []
        for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:limit]:
            improvements = domain_improvements[domain]
            avg_improvement = sum(improvements) / len(improvements) if improvements else 0
            
            top_domains.append({
                'domain': domain,
                'test_count': count,
                'avg_improvement': round(avg_improvement, 1),
                'total_improvements': len(improvements)
            })
        
        return jsonify({'top_domains': top_domains})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@speed_test_bp.route('/api/speed-test/recent', methods=['GET'])
def get_recent_tests():
    """Get recent speed tests"""
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 20)), 100)
        
        tests = SpeedTestLog.query.filter(
            SpeedTestLog.test_type == 'comparison',
            SpeedTestLog.improvement_percent.isnot(None)
        ).order_by(SpeedTestLog.created_at.desc()).limit(limit).all()
        
        recent_tests = []
        for test in tests:
            recent_tests.append({
                'test_url': test.test_url,
                'improvement_percent': test.improvement_percent,
                'origin_load_time_ms': test.origin_load_time_ms,
                'cdn_load_time_ms': test.cdn_load_time_ms,
                'cache_status': test.cache_status,
                'created_at': test.created_at.isoformat()
            })
        
        return jsonify({'recent_tests': recent_tests})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500