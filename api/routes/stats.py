#!/usr/bin/env python3
"""
Cachenet CDN Platform Statistics Routes
Analytics and usage statistics for domains and edge nodes
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_
from models import db, User, Domain, EdgeNode, CacheStats, SSLCertificate

logger = logging.getLogger(__name__)
stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Date range for statistics
        days = request.args.get('days', 30, type=int)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Get user's domains
        if user.is_admin:
            domains = Domain.query.all()
        else:
            domains = Domain.query.filter_by(user_id=user_id).all()
        
        domain_ids = [d.id for d in domains]
        
        # Calculate total statistics
        total_requests = 0
        total_cache_hits = 0
        total_bandwidth_saved = 0
        total_bandwidth_total = 0
        
        if domain_ids:
            stats_query = CacheStats.query.filter(
                and_(
                    CacheStats.domain_id.in_(domain_ids),
                    CacheStats.date >= start_date,
                    CacheStats.date <= end_date
                )
            )
            
            # Aggregate statistics
            aggregate = stats_query.with_entities(
                func.sum(CacheStats.requests).label('total_requests'),
                func.sum(CacheStats.cache_hits).label('total_cache_hits'),
                func.sum(CacheStats.bandwidth_saved).label('total_bandwidth_saved'),
                func.sum(CacheStats.bandwidth_total).label('total_bandwidth_total'),
                func.avg(CacheStats.response_time_avg).label('avg_response_time')
            ).first()
            
            total_requests = aggregate.total_requests or 0
            total_cache_hits = aggregate.total_cache_hits or 0
            total_bandwidth_saved = aggregate.total_bandwidth_saved or 0
            total_bandwidth_total = aggregate.total_bandwidth_total or 0
            avg_response_time = aggregate.avg_response_time or 0
        
        # Calculate cache hit ratio
        cache_hit_ratio = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate bandwidth savings
        bandwidth_savings_ratio = (total_bandwidth_saved / total_bandwidth_total * 100) if total_bandwidth_total > 0 else 0
        
        # Get edge node statistics
        if user.is_admin:
            active_edges = EdgeNode.query.filter_by(status='active').count()
            total_edges = EdgeNode.query.count()
        else:
            # For non-admin users, show relevant edge node info
            active_edges = EdgeNode.query.filter_by(status='active').count()
            total_edges = active_edges
        
        # Get SSL certificate statistics
        ssl_stats = {}
        if user.is_admin:
            ssl_certs = SSLCertificate.query.all()
        else:
            ssl_certs = SSLCertificate.query.filter_by(user_id=user_id).all()
        
        ssl_total = len(ssl_certs)
        ssl_active = len([cert for cert in ssl_certs if cert.status == 'active'])
        ssl_expiring_soon = len([cert for cert in ssl_certs 
                                if cert.expires_at and 
                                (cert.expires_at - datetime.utcnow()).days <= 30])
        
        ssl_stats = {
            'total': ssl_total,
            'active': ssl_active,
            'expiring_soon': ssl_expiring_soon
        }
        
        return jsonify({
            'period': f'{days} days',
            'domains': {
                'total': len(domains),
                'active': len([d for d in domains if d.cdn_enabled and d.status == 'active']),
                'pending': len([d for d in domains if d.status == 'pending'])
            },
            'edge_nodes': {
                'active': active_edges,
                'total': total_edges
            },
            'ssl_certificates': ssl_stats,
            'traffic': {
                'total_requests': total_requests,
                'cache_hit_ratio': round(cache_hit_ratio, 2),
                'bandwidth_saved_gb': round(total_bandwidth_saved / (1024**3), 2),
                'bandwidth_total_gb': round(total_bandwidth_total / (1024**3), 2),
                'bandwidth_savings_ratio': round(bandwidth_savings_ratio, 2),
                'avg_response_time_ms': round(avg_response_time, 2) if total_requests > 0 else 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@stats_bp.route('/domains/<int:domain_id>/analytics', methods=['GET'])
@jwt_required()
def get_domain_analytics():
    """Get detailed analytics for a specific domain"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify domain ownership
        if user.is_admin:
            domain = Domain.query.get(domain_id)
        else:
            domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        # Date range for analytics
        days = request.args.get('days', 30, type=int)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Get domain statistics
        stats = CacheStats.query.filter(
            and_(
                CacheStats.domain_id == domain_id,
                CacheStats.date >= start_date,
                CacheStats.date <= end_date
            )
        ).order_by(CacheStats.date.desc()).all()
        
        # Daily analytics
        daily_stats = []
        for stat in stats:
            cache_hit_ratio = (stat.cache_hits / stat.requests * 100) if stat.requests > 0 else 0
            daily_stats.append({
                'date': stat.date.isoformat(),
                'requests': stat.requests,
                'cache_hits': stat.cache_hits,
                'cache_misses': stat.cache_misses,
                'cache_hit_ratio': round(cache_hit_ratio, 2),
                'bandwidth_saved_gb': round(stat.bandwidth_saved / (1024**3), 2),
                'bandwidth_total_gb': round(stat.bandwidth_total / (1024**3), 2),
                'response_time_avg': stat.response_time_avg,
                'edge_node_id': stat.edge_node_id
            })
        
        # Aggregate totals
        total_requests = sum(s.requests for s in stats)
        total_cache_hits = sum(s.cache_hits for s in stats)
        total_bandwidth_saved = sum(s.bandwidth_saved for s in stats)
        total_bandwidth_total = sum(s.bandwidth_total for s in stats)
        
        # Calculate ratios
        overall_cache_hit_ratio = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        bandwidth_savings_ratio = (total_bandwidth_saved / total_bandwidth_total * 100) if total_bandwidth_total > 0 else 0
        
        # Get top performing edge nodes for this domain
        edge_performance = db.session.query(
            EdgeNode.name,
            EdgeNode.region,
            func.sum(CacheStats.requests).label('requests'),
            func.avg(CacheStats.response_time_avg).label('avg_response_time')
        ).join(CacheStats).filter(
            and_(
                CacheStats.domain_id == domain_id,
                CacheStats.date >= start_date,
                CacheStats.date <= end_date
            )
        ).group_by(EdgeNode.id, EdgeNode.name, EdgeNode.region).order_by(
            func.sum(CacheStats.requests).desc()
        ).limit(10).all()
        
        top_edges = []
        for edge in edge_performance:
            top_edges.append({
                'name': edge.name,
                'region': edge.region,
                'requests': edge.requests,
                'avg_response_time': round(edge.avg_response_time, 2)
            })
        
        return jsonify({
            'domain': domain.to_dict(),
            'period': f'{days} days',
            'summary': {
                'total_requests': total_requests,
                'cache_hit_ratio': round(overall_cache_hit_ratio, 2),
                'bandwidth_saved_gb': round(total_bandwidth_saved / (1024**3), 2),
                'bandwidth_savings_ratio': round(bandwidth_savings_ratio, 2)
            },
            'daily_analytics': daily_stats,
            'top_edge_nodes': top_edges
        }), 200
        
    except Exception as e:
        logger.error(f"Domain analytics error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@stats_bp.route('/edge-nodes/<int:edge_id>/metrics', methods=['GET'])
@jwt_required()
def get_edge_node_metrics():
    """Get metrics for a specific edge node (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        edge_node = EdgeNode.query.get(edge_id)
        if not edge_node:
            return jsonify({'error': 'Edge node not found'}), 404
        
        # Date range for metrics
        days = request.args.get('days', 7, type=int)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Get edge node statistics
        stats = CacheStats.query.filter(
            and_(
                CacheStats.edge_node_id == edge_id,
                CacheStats.date >= start_date,
                CacheStats.date <= end_date
            )
        ).order_by(CacheStats.date.desc()).all()
        
        # Daily metrics
        daily_metrics = []
        for stat in stats:
            cache_hit_ratio = (stat.cache_hits / stat.requests * 100) if stat.requests > 0 else 0
            daily_metrics.append({
                'date': stat.date.isoformat(),
                'requests': stat.requests,
                'cache_hit_ratio': round(cache_hit_ratio, 2),
                'bandwidth_gb': round(stat.bandwidth_total / (1024**3), 2),
                'response_time_avg': stat.response_time_avg
            })
        
        # Performance summary
        total_requests = sum(s.requests for s in stats)
        total_cache_hits = sum(s.cache_hits for s in stats)
        avg_response_time = sum(s.response_time_avg for s in stats) / len(stats) if stats else 0
        
        return jsonify({
            'edge_node': edge_node.to_dict(),
            'period': f'{days} days',
            'summary': {
                'total_requests': total_requests,
                'cache_hit_ratio': round((total_cache_hits / total_requests * 100) if total_requests > 0 else 0, 2),
                'avg_response_time': round(avg_response_time, 2),
                'load_score': edge_node.load_score,
                'client_count': edge_node.client_count
            },
            'daily_metrics': daily_metrics
        }), 200
        
    except Exception as e:
        logger.error(f"Edge node metrics error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@stats_bp.route('/bandwidth-report', methods=['GET'])
@jwt_required()
def get_bandwidth_report():
    """Get detailed bandwidth usage report"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Date range for report
        days = request.args.get('days', 30, type=int)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Get user's domains or all domains for admin
        if user.is_admin:
            domains = Domain.query.all()
        else:
            domains = Domain.query.filter_by(user_id=user_id).all()
        
        domain_ids = [d.id for d in domains]
        
        # Get bandwidth usage by domain
        domain_bandwidth = []
        if domain_ids:
            bandwidth_by_domain = db.session.query(
                Domain.domain_name,
                func.sum(CacheStats.bandwidth_total).label('total_bandwidth'),
                func.sum(CacheStats.bandwidth_saved).label('saved_bandwidth'),
                func.sum(CacheStats.requests).label('total_requests')
            ).join(CacheStats).filter(
                and_(
                    CacheStats.domain_id.in_(domain_ids),
                    CacheStats.date >= start_date,
                    CacheStats.date <= end_date
                )
            ).group_by(Domain.id, Domain.domain_name).order_by(
                func.sum(CacheStats.bandwidth_total).desc()
            ).all()
            
            for domain_data in bandwidth_by_domain:
                total_gb = domain_data.total_bandwidth / (1024**3) if domain_data.total_bandwidth else 0
                saved_gb = domain_data.saved_bandwidth / (1024**3) if domain_data.saved_bandwidth else 0
                savings_ratio = (domain_data.saved_bandwidth / domain_data.total_bandwidth * 100) if domain_data.total_bandwidth > 0 else 0
                
                domain_bandwidth.append({
                    'domain_name': domain_data.domain_name,
                    'total_bandwidth_gb': round(total_gb, 2),
                    'saved_bandwidth_gb': round(saved_gb, 2),
                    'savings_ratio': round(savings_ratio, 2),
                    'total_requests': domain_data.total_requests
                })
        
        # Calculate overall totals
        total_bandwidth = sum(d['total_bandwidth_gb'] for d in domain_bandwidth)
        total_saved = sum(d['saved_bandwidth_gb'] for d in domain_bandwidth)
        overall_savings_ratio = (total_saved / total_bandwidth * 100) if total_bandwidth > 0 else 0
        
        return jsonify({
            'period': f'{days} days',
            'summary': {
                'total_bandwidth_gb': round(total_bandwidth, 2),
                'saved_bandwidth_gb': round(total_saved, 2),
                'overall_savings_ratio': round(overall_savings_ratio, 2),
                'domains_count': len(domain_bandwidth)
            },
            'domain_breakdown': domain_bandwidth
        }), 200
        
    except Exception as e:
        logger.error(f"Bandwidth report error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@stats_bp.route('/real-time', methods=['GET'])
@jwt_required()
def get_real_time_stats():
    """Get real-time statistics for the last hour"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get stats for the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        today = datetime.utcnow().date()
        
        # Get user's domains
        if user.is_admin:
            domains = Domain.query.all()
        else:
            domains = Domain.query.filter_by(user_id=user_id).all()
        
        domain_ids = [d.id for d in domains]
        
        # Get recent cache stats (today's stats as proxy for real-time)
        real_time_data = {
            'active_domains': len([d for d in domains if d.cdn_enabled and d.status == 'active']),
            'active_edge_nodes': EdgeNode.query.filter_by(status='active').count(),
            'current_requests_per_second': 0,  # Would be calculated from real-time monitoring
            'current_cache_hit_ratio': 0,
            'alerts': []
        }
        
        # Check for any alerts
        alerts = []
        
        # Check SSL certificates expiring soon
        expiring_certs = SSLCertificate.query.filter(
            and_(
                SSLCertificate.expires_at.isnot(None),
                SSLCertificate.expires_at <= datetime.utcnow() + timedelta(days=7)
            )
        )
        
        if user.is_admin:
            expiring_certs = expiring_certs.all()
        else:
            expiring_certs = expiring_certs.filter_by(user_id=user_id).all()
        
        for cert in expiring_certs:
            days_left = (cert.expires_at - datetime.utcnow()).days
            alerts.append({
                'type': 'ssl_expiring',
                'severity': 'warning' if days_left > 3 else 'critical',
                'message': f'SSL certificate for {cert.domain_name} expires in {days_left} days',
                'domain': cert.domain_name,
                'expires_at': cert.expires_at.isoformat()
            })
        
        # Check edge nodes with high load
        overloaded_edges = EdgeNode.query.filter(
            and_(
                EdgeNode.status == 'active',
                EdgeNode.load_score > 0.8
            )
        ).all()
        
        for edge in overloaded_edges:
            alerts.append({
                'type': 'high_load',
                'severity': 'warning',
                'message': f'Edge node {edge.name} has high load ({edge.load_score:.1%})',
                'edge_node': edge.name,
                'region': edge.region,
                'load_score': edge.load_score
            })
        
        real_time_data['alerts'] = alerts
        
        return jsonify(real_time_data), 200
        
    except Exception as e:
        logger.error(f"Real-time stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500