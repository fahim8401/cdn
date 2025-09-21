#!/usr/bin/env python3
"""
Cachenet CDN Platform Cache Management Routes
Cache purging and statistics
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Domain, CacheStats, EdgeNode
from tasks.purge_cache import purge_domain_cache, purge_url_cache

logger = logging.getLogger(__name__)
cache_bp = Blueprint('cache', __name__)

@cache_bp.route('/purge/domain', methods=['POST'])
@jwt_required()
def purge_domain():
    """Purge entire domain cache"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data or not data.get('domain_id'):
            return jsonify({'error': 'Domain ID required'}), 400
        
        domain_id = data['domain_id']
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        # Trigger async cache purge
        task = purge_domain_cache.delay(domain.id)
        
        logger.info(f"Domain cache purge initiated for: {domain.domain_name}")
        
        return jsonify({
            'message': 'Cache purge initiated',
            'task_id': task.id,
            'domain': domain.domain_name
        }), 200
        
    except Exception as e:
        logger.error(f"Purge domain cache error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_bp.route('/purge/url', methods=['POST'])
@jwt_required()
def purge_url():
    """Purge specific URL from cache"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data or not data.get('domain_id') or not data.get('url_path'):
            return jsonify({'error': 'Domain ID and URL path required'}), 400
        
        domain_id = data['domain_id']
        url_path = data['url_path'].strip()
        
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        # Validate URL path
        if not url_path.startswith('/'):
            url_path = '/' + url_path
        
        # Trigger async URL cache purge
        task = purge_url_cache.delay(domain.id, url_path)
        
        logger.info(f"URL cache purge initiated for: {domain.domain_name}{url_path}")
        
        return jsonify({
            'message': 'URL cache purge initiated',
            'task_id': task.id,
            'domain': domain.domain_name,
            'url_path': url_path
        }), 200
        
    except Exception as e:
        logger.error(f"Purge URL cache error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_bp.route('/purge/wildcard', methods=['POST'])
@jwt_required()
def purge_wildcard():
    """Purge cache using wildcard pattern"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data or not data.get('domain_id') or not data.get('pattern'):
            return jsonify({'error': 'Domain ID and pattern required'}), 400
        
        domain_id = data['domain_id']
        pattern = data['pattern'].strip()
        
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        # Trigger async wildcard cache purge
        task = purge_url_cache.delay(domain.id, pattern, wildcard=True)
        
        logger.info(f"Wildcard cache purge initiated for: {domain.domain_name} pattern: {pattern}")
        
        return jsonify({
            'message': 'Wildcard cache purge initiated',
            'task_id': task.id,
            'domain': domain.domain_name,
            'pattern': pattern
        }), 200
        
    except Exception as e:
        logger.error(f"Purge wildcard cache error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_bp.route('/stats/domain/<int:domain_id>', methods=['GET'])
@jwt_required()
def get_domain_cache_stats():
    """Get cache statistics for a domain"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        # Get date range from query parameters
        days = request.args.get('days', 7, type=int)
        days = min(days, 90)  # Max 90 days
        
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        # Get cache stats
        stats = CacheStats.query.filter(
            CacheStats.domain_id == domain_id,
            CacheStats.date >= start_date
        ).order_by(CacheStats.date.desc()).all()
        
        # Calculate totals
        total_requests = sum(stat.requests for stat in stats)
        total_cache_hits = sum(stat.cache_hits for stat in stats)
        total_bandwidth_saved = sum(stat.bandwidth_saved for stat in stats)
        total_bandwidth = sum(stat.bandwidth_total for stat in stats)
        
        cache_hit_ratio = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        bandwidth_saved_gb = total_bandwidth_saved / (1024**3) if total_bandwidth_saved > 0 else 0
        bandwidth_total_gb = total_bandwidth / (1024**3) if total_bandwidth > 0 else 0
        
        # Group stats by date
        daily_stats = {}
        for stat in stats:
            date_str = stat.date.isoformat()
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    'date': date_str,
                    'requests': 0,
                    'cache_hits': 0,
                    'cache_misses': 0,
                    'bandwidth_saved': 0,
                    'bandwidth_total': 0,
                    'response_time_avg': 0
                }
            
            daily_stats[date_str]['requests'] += stat.requests
            daily_stats[date_str]['cache_hits'] += stat.cache_hits
            daily_stats[date_str]['cache_misses'] += stat.cache_misses
            daily_stats[date_str]['bandwidth_saved'] += stat.bandwidth_saved
            daily_stats[date_str]['bandwidth_total'] += stat.bandwidth_total
            daily_stats[date_str]['response_time_avg'] = stat.response_time_avg
        
        # Convert to list and sort by date
        daily_stats_list = list(daily_stats.values())
        daily_stats_list.sort(key=lambda x: x['date'])
        
        return jsonify({
            'domain': domain.domain_name,
            'period_days': days,
            'summary': {
                'total_requests': total_requests,
                'total_cache_hits': total_cache_hits,
                'cache_hit_ratio': round(cache_hit_ratio, 2),
                'bandwidth_saved_gb': round(bandwidth_saved_gb, 2),
                'bandwidth_total_gb': round(bandwidth_total_gb, 2),
                'bandwidth_saved_percentage': round((total_bandwidth_saved / total_bandwidth * 100), 2) if total_bandwidth > 0 else 0
            },
            'daily_stats': daily_stats_list
        }), 200
        
    except Exception as e:
        logger.error(f"Get domain cache stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_bp.route('/stats/overview', methods=['GET'])
@jwt_required()
def get_cache_overview():
    """Get cache statistics overview for all user domains"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's domains
        domains = Domain.query.filter_by(user_id=user_id).all()
        domain_ids = [domain.id for domain in domains]
        
        if not domain_ids:
            return jsonify({
                'total_domains': 0,
                'total_requests': 0,
                'cache_hit_ratio': 0,
                'bandwidth_saved_gb': 0,
                'top_domains': []
            }), 200
        
        # Get date range
        days = request.args.get('days', 7, type=int)
        days = min(days, 90)
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        # Get aggregated stats
        stats = CacheStats.query.filter(
            CacheStats.domain_id.in_(domain_ids),
            CacheStats.date >= start_date
        ).all()
        
        # Calculate totals
        total_requests = sum(stat.requests for stat in stats)
        total_cache_hits = sum(stat.cache_hits for stat in stats)
        total_bandwidth_saved = sum(stat.bandwidth_saved for stat in stats)
        
        cache_hit_ratio = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        bandwidth_saved_gb = total_bandwidth_saved / (1024**3) if total_bandwidth_saved > 0 else 0
        
        # Get top domains by requests
        domain_stats = {}
        for stat in stats:
            domain_id = stat.domain_id
            if domain_id not in domain_stats:
                domain_stats[domain_id] = {
                    'requests': 0,
                    'cache_hits': 0,
                    'bandwidth_saved': 0
                }
            domain_stats[domain_id]['requests'] += stat.requests
            domain_stats[domain_id]['cache_hits'] += stat.cache_hits
            domain_stats[domain_id]['bandwidth_saved'] += stat.bandwidth_saved
        
        # Convert to list with domain names
        top_domains = []
        for domain in domains:
            if domain.id in domain_stats:
                stats_data = domain_stats[domain.id]
                top_domains.append({
                    'domain_name': domain.domain_name,
                    'requests': stats_data['requests'],
                    'cache_hit_ratio': round((stats_data['cache_hits'] / stats_data['requests'] * 100), 2) if stats_data['requests'] > 0 else 0,
                    'bandwidth_saved_gb': round(stats_data['bandwidth_saved'] / (1024**3), 2)
                })
        
        # Sort by requests and take top 10
        top_domains.sort(key=lambda x: x['requests'], reverse=True)
        top_domains = top_domains[:10]
        
        return jsonify({
            'period_days': days,
            'total_domains': len(domains),
            'total_requests': total_requests,
            'cache_hit_ratio': round(cache_hit_ratio, 2),
            'bandwidth_saved_gb': round(bandwidth_saved_gb, 2),
            'top_domains': top_domains
        }), 200
        
    except Exception as e:
        logger.error(f"Get cache overview error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_bp.route('/stats/edge/<int:edge_id>', methods=['GET'])
@jwt_required()
def get_edge_cache_stats():
    """Get cache statistics for a specific edge node"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        edge_node = EdgeNode.query.get(edge_id)
        if not edge_node:
            return jsonify({'error': 'Edge node not found'}), 404
        
        # Get date range
        days = request.args.get('days', 7, type=int)
        days = min(days, 90)
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        # Get stats for this edge node
        stats = CacheStats.query.filter(
            CacheStats.edge_node_id == edge_id,
            CacheStats.date >= start_date
        ).order_by(CacheStats.date.desc()).all()
        
        # Calculate totals
        total_requests = sum(stat.requests for stat in stats)
        total_cache_hits = sum(stat.cache_hits for stat in stats)
        total_bandwidth_saved = sum(stat.bandwidth_saved for stat in stats)
        
        cache_hit_ratio = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        bandwidth_saved_gb = total_bandwidth_saved / (1024**3) if total_bandwidth_saved > 0 else 0
        
        return jsonify({
            'edge_node': edge_node.to_dict(),
            'period_days': days,
            'total_requests': total_requests,
            'cache_hit_ratio': round(cache_hit_ratio, 2),
            'bandwidth_saved_gb': round(bandwidth_saved_gb, 2),
            'daily_stats': [stat.to_dict() for stat in stats]
        }), 200
        
    except Exception as e:
        logger.error(f"Get edge cache stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_bp.route('/purge/by-key', methods=['POST'])
def purge_by_key():
    """Purge cache using purge key (for WordPress/WHMCS plugins)"""
    try:
        data = request.get_json()
        if not data or not data.get('purge_key'):
            return jsonify({'error': 'Purge key required'}), 400
        
        purge_key = data['purge_key']
        url_path = data.get('url_path', '*')  # Default to purge all
        
        # Find domain by purge key
        domain = Domain.query.filter_by(purge_key=purge_key).first()
        if not domain:
            return jsonify({'error': 'Invalid purge key'}), 401
        
        if not domain.cdn_enabled:
            return jsonify({'error': 'CDN is disabled for this domain'}), 400
        
        # Trigger cache purge
        if url_path == '*' or url_path == '':
            task = purge_domain_cache.delay(domain.id)
        else:
            task = purge_url_cache.delay(domain.id, url_path)
        
        logger.info(f"Cache purge via key for domain: {domain.domain_name}, path: {url_path}")
        
        return jsonify({
            'message': 'Cache purge initiated',
            'task_id': task.id,
            'domain': domain.domain_name
        }), 200
        
    except Exception as e:
        logger.error(f"Purge by key error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500