#!/usr/bin/env python3
"""
XenCDN v8.1 Speed Test API Routes
Routes for public speed testing tool
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
import requests
import time
import ipaddress
from urllib.parse import urlparse

from ..models import db, SpeedTestLog, ClientRegistration, EdgeNode

speed_test_bp = Blueprint('speed_test', __name__, url_prefix='/api/speed-test')

# Rate limiting storage (in production, use Redis)
rate_limit_storage = {}

@speed_test_bp.route('/test', methods=['POST'])
def run_speed_test():
    """Run speed test comparing origin vs CDN performance"""
    try:
        data = request.get_json()
        test_url = data.get('test_url')
        
        if not test_url:
            return jsonify({'error': 'test_url required'}), 400
        
        # Validate URL format
        try:
            parsed_url = urlparse(test_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return jsonify({'error': 'Invalid URL format'}), 400
            
            if parsed_url.scheme not in ['http', 'https']:
                return jsonify({'error': 'Only HTTP and HTTPS URLs are supported'}), 400
        except Exception:
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Get client IP for rate limiting
        client_ip = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', '127.0.0.1')
        
        # Rate limiting check
        if not check_rate_limit(client_ip):
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        
        # Security checks
        if not is_url_safe(test_url):
            return jsonify({'error': 'URL not allowed for testing'}), 403
        
        # Run the speed test
        origin_result = test_url_performance(test_url, use_cdn=False)
        cdn_result = test_url_performance(test_url, use_cdn=True)
        
        # Calculate improvement
        improvement_percent = 0
        if origin_result['load_time'] > 0 and cdn_result['load_time'] > 0:
            improvement_percent = ((origin_result['load_time'] - cdn_result['load_time']) / origin_result['load_time']) * 100
        
        # Get user agent and edge location
        user_agent = request.headers.get('User-Agent', '')
        edge_location = get_nearest_edge_location(client_ip)
        
        # Store test result
        speed_test = SpeedTestLog(
            test_url=test_url,
            origin_ttfb=origin_result['ttfb'],
            origin_load_time=origin_result['load_time'],
            origin_size=origin_result['size'],
            cdn_ttfb=cdn_result['ttfb'],
            cdn_load_time=cdn_result['load_time'],
            cdn_size=cdn_result['size'],
            cache_status=cdn_result['cache_status'],
            improvement_percent=improvement_percent,
            user_ip=client_ip,
            user_agent=user_agent,
            edge_location=edge_location
        )
        
        # Associate with client if authenticated
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt
            verify_jwt_in_request(optional=True)
            claims = get_jwt()
            if claims and claims.get('role') == 'client':
                speed_test.client_id = get_jwt_identity()
        except Exception:
            pass  # Not authenticated, that's fine
        
        db.session.add(speed_test)
        db.session.commit()
        
        return jsonify({
            'test_id': speed_test.id,
            'test_url': test_url,
            'origin': {
                'ttfb': origin_result['ttfb'],
                'load_time': origin_result['load_time'],
                'size': origin_result['size'],
                'status': origin_result['status']
            },
            'cdn': {
                'ttfb': cdn_result['ttfb'],
                'load_time': cdn_result['load_time'],
                'size': cdn_result['size'],
                'cache_status': cdn_result['cache_status'],
                'status': cdn_result['status']
            },
            'improvement': {
                'percent': round(improvement_percent, 2),
                'ttfb_saved_ms': round(origin_result['ttfb'] - cdn_result['ttfb'], 2),
                'load_time_saved_ms': round(origin_result['load_time'] - cdn_result['load_time'], 2),
                'bandwidth_saved_bytes': origin_result['size'] - cdn_result['size']
            },
            'edge_location': edge_location,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Speed test error: {e}")
        return jsonify({'error': 'Speed test failed'}), 500

@speed_test_bp.route('/history', methods=['GET'])
@jwt_required()
def get_test_history():
    """Get speed test history for authenticated client"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'client':
            return jsonify({'error': 'Client access required'}), 403
        
        client_id = get_jwt_identity()
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Get tests for this client
        tests_query = SpeedTestLog.query.filter_by(client_id=client_id).order_by(SpeedTestLog.created_at.desc())
        tests_paginated = tests_query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'tests': [test.to_dict() for test in tests_paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': tests_paginated.total,
                'pages': tests_paginated.pages,
                'has_next': tests_paginated.has_next,
                'has_prev': tests_paginated.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get test history error: {e}")
        return jsonify({'error': 'Failed to get test history'}), 500

@speed_test_bp.route('/stats', methods=['GET'])
def get_global_stats():
    """Get global speed test statistics (public)"""
    try:
        # Get overall statistics
        total_tests = SpeedTestLog.query.count()
        
        if total_tests == 0:
            return jsonify({
                'total_tests': 0,
                'avg_improvement': 0,
                'total_bandwidth_saved_gb': 0,
                'total_time_saved_hours': 0
            }), 200
        
        # Calculate averages
        tests = SpeedTestLog.query.all()
        
        total_improvement = sum(test.improvement_percent for test in tests if test.improvement_percent)
        avg_improvement = total_improvement / len(tests) if tests else 0
        
        total_bandwidth_saved = sum(
            (test.origin_size - test.cdn_size) for test in tests 
            if test.origin_size and test.cdn_size and test.origin_size > test.cdn_size
        )
        total_bandwidth_saved_gb = total_bandwidth_saved / (1024**3)
        
        total_time_saved_ms = sum(
            (test.origin_load_time - test.cdn_load_time) for test in tests
            if test.origin_load_time and test.cdn_load_time and test.origin_load_time > test.cdn_load_time
        )
        total_time_saved_hours = total_time_saved_ms / (1000 * 60 * 60)
        
        return jsonify({
            'total_tests': total_tests,
            'avg_improvement': round(avg_improvement, 2),
            'total_bandwidth_saved_gb': round(total_bandwidth_saved_gb, 2),
            'total_time_saved_hours': round(total_time_saved_hours, 2)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get global stats error: {e}")
        return jsonify({'error': 'Failed to get stats'}), 500

def test_url_performance(url, use_cdn=False):
    """Test URL performance with or without CDN"""
    try:
        # Construct the URL to test
        if use_cdn:
            # Replace domain with CDN domain
            parsed_url = urlparse(url)
            cdn_domain = f"cdn.{parsed_url.netloc}"  # Simple CDN domain construction
            test_url = f"{parsed_url.scheme}://{cdn_domain}{parsed_url.path}"
            if parsed_url.query:
                test_url += f"?{parsed_url.query}"
        else:
            test_url = url
        
        # Measure performance
        start_time = time.time()
        
        # Set headers
        headers = {
            'User-Agent': 'XenCDN-SpeedTest/1.0',
            'Accept': '*/*',
            'Cache-Control': 'no-cache' if not use_cdn else 'max-age=3600'
        }
        
        # Make request with timeout
        response = requests.get(test_url, headers=headers, timeout=30, allow_redirects=True)
        
        end_time = time.time()
        load_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Extract TTFB (approximate from response time)
        ttfb = load_time * 0.3  # Rough estimate
        
        # Get cache status for CDN requests
        cache_status = 'unknown'
        if use_cdn:
            cache_headers = ['X-Cache', 'X-Cache-Status', 'CF-Cache-Status']
            for header in cache_headers:
                if header in response.headers:
                    cache_value = response.headers[header].lower()
                    if 'hit' in cache_value:
                        cache_status = 'hit'
                    elif 'miss' in cache_value:
                        cache_status = 'miss'
                    elif 'bypass' in cache_value:
                        cache_status = 'bypass'
                    break
        
        return {
            'ttfb': ttfb,
            'load_time': load_time,
            'size': len(response.content),
            'status': response.status_code,
            'cache_status': cache_status
        }
        
    except requests.RequestException as e:
        current_app.logger.error(f"URL test error for {url}: {e}")
        return {
            'ttfb': 0,
            'load_time': 0,
            'size': 0,
            'status': 0,
            'cache_status': 'error'
        }
    except Exception as e:
        current_app.logger.error(f"Unexpected error testing {url}: {e}")
        return {
            'ttfb': 0,
            'load_time': 0,
            'size': 0,
            'status': 0,
            'cache_status': 'error'
        }

def check_rate_limit(client_ip):
    """Check if client IP is within rate limits"""
    current_time = datetime.utcnow()
    hour_key = current_time.strftime('%Y%m%d%H')
    minute_key = current_time.strftime('%Y%m%d%H%M')
    
    # Clean old entries
    for key in list(rate_limit_storage.keys()):
        if key < hour_key:
            del rate_limit_storage[key]
    
    # Check hourly limit
    hourly_key = f"{client_ip}_{hour_key}"
    hourly_count = rate_limit_storage.get(hourly_key, 0)
    
    max_tests_per_hour = int(os.getenv('SPEED_TEST_MAX_TESTS_PER_HOUR', 100))
    if hourly_count >= max_tests_per_hour:
        return False
    
    # Check per-minute limit for burst protection
    minute_key_full = f"{client_ip}_{minute_key}"
    minute_count = rate_limit_storage.get(minute_key_full, 0)
    
    max_tests_per_minute = int(os.getenv('SPEED_TEST_MAX_TESTS_PER_MINUTE', 10))
    if minute_count >= max_tests_per_minute:
        return False
    
    # Update counters
    rate_limit_storage[hourly_key] = hourly_count + 1
    rate_limit_storage[minute_key_full] = minute_count + 1
    
    return True

def is_url_safe(url):
    """Check if URL is safe for testing"""
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        
        if not hostname:
            return False
        
        # Block private/internal IP ranges
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            pass  # Not an IP address, continue with hostname checks
        
        # Block localhost and internal domains
        blocked_domains = [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            'internal',
            'local',
            'test',
            'staging'
        ]
        
        for blocked in blocked_domains:
            if blocked in hostname.lower():
                return False
        
        # Block URLs to gaming/proprietary platforms
        blocked_patterns = [
            'epicgames.com',
            'garena.com',
            'pubg.com',
            'freefire.com',
            'roblox.com',
            'steam.com',
            'origin.com',
            'uplay.com',
            'battle.net',
            'blizzard.com'
        ]
        
        for pattern in blocked_patterns:
            if pattern in hostname.lower():
                return False
        
        # Only allow specific file types for testing
        allowed_extensions = [
            '.html', '.htm', '.php', '.asp', '.aspx', '.jsp',
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
            '.css', '.js', '.json', '.xml',
            '.pdf', '.txt', '.ico'
        ]
        
        path = parsed_url.path.lower()
        if path and '.' in path:
            extension = '.' + path.split('.')[-1]
            if extension not in allowed_extensions:
                return False
        
        return True
        
    except Exception:
        return False

def get_nearest_edge_location(client_ip):
    """Get nearest edge location for client IP"""
    try:
        # In a real implementation, this would use GeoIP lookup
        # For now, return a mock edge location
        
        # Simple mock based on IP ranges
        if client_ip.startswith('192.168.') or client_ip == '127.0.0.1':
            return 'Local'
        
        # Get active edge nodes
        edge_nodes = EdgeNode.query.filter_by(status='active').all()
        
        if not edge_nodes:
            return 'Unknown'
        
        # For demo purposes, return first available edge location
        return f"{edge_nodes[0].city}, {edge_nodes[0].country}"
        
    except Exception:
        return 'Unknown'