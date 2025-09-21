#!/usr/bin/env python3
"""
Cachenet CDN Platform Auto-scaling Routes
Edge node management and auto-scaling
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, EdgeNode, DNSRecord
from tasks.auto_scale import scale_up_edge_nodes, scale_down_edge_nodes, deploy_edge_node

logger = logging.getLogger(__name__)
auto_scale_bp = Blueprint('auto_scale', __name__)

@auto_scale_bp.route('/edge-nodes', methods=['GET'])
@jwt_required()
def list_edge_nodes():
    """List all edge nodes (admin only for full list, users see limited info)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        region_filter = request.args.get('region')
        status_filter = request.args.get('status')
        
        # Build query
        query = EdgeNode.query
        
        if region_filter:
            query = query.filter_by(region=region_filter)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        edge_nodes = query.order_by(EdgeNode.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # For non-admin users, filter sensitive information
        if user.is_admin:
            nodes_data = [node.to_dict() for node in edge_nodes.items]
        else:
            nodes_data = []
            for node in edge_nodes.items:
                node_data = node.to_dict()
                # Remove sensitive fields for non-admin users
                node_data.pop('instance_id', None)
                node_data.pop('provider', None)
                nodes_data.append(node_data)
        
        return jsonify({
            'edge_nodes': nodes_data,
            'total': edge_nodes.total,
            'pages': edge_nodes.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        logger.error(f"List edge nodes error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auto_scale_bp.route('/edge-nodes', methods=['POST'])
@jwt_required()
def create_edge_node():
    """Create new edge node (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['name', 'hostname', 'ip_address', 'region', 'provider']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if hostname already exists
        existing_node = EdgeNode.query.filter_by(hostname=data['hostname']).first()
        if existing_node:
            return jsonify({'error': 'Hostname already exists'}), 409
        
        # Create edge node
        edge_node = EdgeNode(
            name=data['name'].strip(),
            hostname=data['hostname'].strip().lower(),
            ip_address=data['ip_address'].strip(),
            region=data['region'].strip(),
            country=data.get('country', '').strip().upper()[:2],
            city=data.get('city', '').strip(),
            provider=data['provider'].strip(),
            instance_id=data.get('instance_id', '').strip(),
            max_clients=data.get('max_clients', int(os.getenv('EDGE_MAX_CLIENTS_PER_NODE', 25))),
            status='pending'
        )
        
        db.session.add(edge_node)
        db.session.commit()
        
        # Trigger async edge node deployment
        task = deploy_edge_node.delay(edge_node.id)
        
        logger.info(f"Edge node created: {edge_node.name} ({edge_node.hostname})")
        
        return jsonify({
            'message': 'Edge node created successfully',
            'task_id': task.id,
            'edge_node': edge_node.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Create edge node error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auto_scale_bp.route('/edge-nodes/<int:node_id>', methods=['GET'])
@jwt_required()
def get_edge_node():
    """Get edge node details"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        edge_node = EdgeNode.query.get(node_id)
        if not edge_node:
            return jsonify({'error': 'Edge node not found'}), 404
        
        node_data = edge_node.to_dict()
        
        # For non-admin users, filter sensitive information
        if not user.is_admin:
            node_data.pop('instance_id', None)
            node_data.pop('provider', None)
        
        # Add DNS records for this edge node
        dns_records = DNSRecord.query.filter_by(edge_node_id=edge_node.id).all()
        node_data['dns_records'] = [record.to_dict() for record in dns_records]
        
        return jsonify({'edge_node': node_data}), 200
        
    except Exception as e:
        logger.error(f"Get edge node error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auto_scale_bp.route('/edge-nodes/<int:node_id>', methods=['PUT'])
@jwt_required()
def update_edge_node():
    """Update edge node (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        edge_node = EdgeNode.query.get(node_id)
        if not edge_node:
            return jsonify({'error': 'Edge node not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed fields
        allowed_fields = ['name', 'region', 'country', 'city', 'max_clients', 'status']
        for field in allowed_fields:
            if field in data:
                if field == 'max_clients':
                    value = int(data[field])
                    if value < 1 or value > 100:
                        return jsonify({'error': 'Max clients must be between 1 and 100'}), 400
                elif field == 'country':
                    value = data[field].strip().upper()[:2]
                else:
                    value = data[field].strip()
                
                setattr(edge_node, field, value)
        
        edge_node.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Edge node updated: {edge_node.name}")
        
        return jsonify({
            'message': 'Edge node updated successfully',
            'edge_node': edge_node.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Update edge node error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auto_scale_bp.route('/edge-nodes/<int:node_id>', methods=['DELETE'])
@jwt_required()
def delete_edge_node():
    """Delete edge node (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        edge_node = EdgeNode.query.get(node_id)
        if not edge_node:
            return jsonify({'error': 'Edge node not found'}), 404
        
        node_name = edge_node.name
        
        # Delete associated DNS records
        DNSRecord.query.filter_by(edge_node_id=edge_node.id).delete()
        
        # Delete edge node
        db.session.delete(edge_node)
        db.session.commit()
        
        logger.info(f"Edge node deleted: {node_name}")
        
        return jsonify({'message': 'Edge node deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Delete edge node error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auto_scale_bp.route('/scale-up', methods=['POST'])
@jwt_required()
def trigger_scale_up():
    """Trigger manual scale up (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        region = data.get('region', os.getenv('EDGE_DEFAULT_REGION', 'nyc1'))
        provider = data.get('provider', 'digitalocean')
        
        # Trigger async scale up
        task = scale_up_edge_nodes.delay(region, provider)
        
        logger.info(f"Manual scale up triggered for region: {region}, provider: {provider}")
        
        return jsonify({
            'message': 'Scale up initiated',
            'task_id': task.id,
            'region': region,
            'provider': provider
        }), 200
        
    except Exception as e:
        logger.error(f"Trigger scale up error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auto_scale_bp.route('/scale-down', methods=['POST'])
@jwt_required()
def trigger_scale_down():
    """Trigger manual scale down (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        region = data.get('region')
        
        # Trigger async scale down
        task = scale_down_edge_nodes.delay(region)
        
        logger.info(f"Manual scale down triggered for region: {region}")
        
        return jsonify({
            'message': 'Scale down initiated',
            'task_id': task.id,
            'region': region
        }), 200
        
    except Exception as e:
        logger.error(f"Trigger scale down error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auto_scale_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_scaling_stats():
    """Get auto-scaling statistics"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get edge node statistics
        total_nodes = EdgeNode.query.count()
        active_nodes = EdgeNode.query.filter_by(status='active').count()
        pending_nodes = EdgeNode.query.filter_by(status='pending').count()
        error_nodes = EdgeNode.query.filter_by(status='error').count()
        
        # Get regional distribution
        regions = db.session.query(
            EdgeNode.region,
            db.func.count(EdgeNode.id).label('count'),
            db.func.avg(EdgeNode.client_count).label('avg_clients'),
            db.func.avg(EdgeNode.load_score).label('avg_load')
        ).filter_by(status='active').group_by(EdgeNode.region).all()
        
        regional_stats = []
        for region_data in regions:
            regional_stats.append({
                'region': region_data.region,
                'node_count': region_data.count,
                'avg_clients': round(region_data.avg_clients or 0, 1),
                'avg_load': round(region_data.avg_load or 0, 2)
            })
        
        # Get provider distribution
        providers = db.session.query(
            EdgeNode.provider,
            db.func.count(EdgeNode.id).label('count')
        ).filter_by(status='active').group_by(EdgeNode.provider).all()
        
        provider_stats = []
        for provider_data in providers:
            provider_stats.append({
                'provider': provider_data.provider,
                'node_count': provider_data.count
            })
        
        # Get recent scaling events (last 24 hours)
        recent_nodes = EdgeNode.query.filter(
            EdgeNode.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(EdgeNode.created_at.desc()).limit(10).all()
        
        auto_scale_enabled = os.getenv('AUTO_SCALE_ENABLED', 'true').lower() == 'true'
        max_clients_per_node = int(os.getenv('EDGE_MAX_CLIENTS_PER_NODE', 25))
        min_nodes = int(os.getenv('AUTO_SCALE_MIN_NODES', 2))
        max_nodes = int(os.getenv('AUTO_SCALE_MAX_NODES', 50))
        
        return jsonify({
            'total_nodes': total_nodes,
            'active_nodes': active_nodes,
            'pending_nodes': pending_nodes,
            'error_nodes': error_nodes,
            'regional_stats': regional_stats,
            'provider_stats': provider_stats,
            'recent_nodes': [node.to_dict() for node in recent_nodes],
            'auto_scale_config': {
                'enabled': auto_scale_enabled,
                'max_clients_per_node': max_clients_per_node,
                'min_nodes': min_nodes,
                'max_nodes': max_nodes
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get scaling stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auto_scale_bp.route('/edge-nodes/<int:node_id>/heartbeat', methods=['POST'])
def edge_node_heartbeat():
    """Receive heartbeat from edge node"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        edge_node = EdgeNode.query.get(node_id)
        if not edge_node:
            return jsonify({'error': 'Edge node not found'}), 404
        
        # Update node status and metrics
        edge_node.last_seen = datetime.utcnow()
        edge_node.client_count = data.get('client_count', 0)
        edge_node.load_score = data.get('load_score', 0.0)
        edge_node.bandwidth_usage_gb = data.get('bandwidth_usage_gb', 0.0)
        
        # Update status based on health
        if data.get('status') == 'healthy':
            edge_node.status = 'active'
        elif data.get('status') == 'unhealthy':
            edge_node.status = 'error'
        
        edge_node.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Heartbeat received',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Edge node heartbeat error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auto_scale_bp.route('/regions', methods=['GET'])
@jwt_required()
def list_regions():
    """List available regions for edge nodes"""
    try:
        # Predefined regions for different providers
        regions = {
            'digitalocean': [
                {'code': 'nyc1', 'name': 'New York 1', 'country': 'US'},
                {'code': 'nyc3', 'name': 'New York 3', 'country': 'US'},
                {'code': 'ams3', 'name': 'Amsterdam 3', 'country': 'NL'},
                {'code': 'sgp1', 'name': 'Singapore 1', 'country': 'SG'},
                {'code': 'lon1', 'name': 'London 1', 'country': 'GB'},
                {'code': 'fra1', 'name': 'Frankfurt 1', 'country': 'DE'},
                {'code': 'tor1', 'name': 'Toronto 1', 'country': 'CA'},
                {'code': 'sfo3', 'name': 'San Francisco 3', 'country': 'US'},
                {'code': 'blr1', 'name': 'Bangalore 1', 'country': 'IN'},
                {'code': 'syd1', 'name': 'Sydney 1', 'country': 'AU'}
            ],
            'linode': [
                {'code': 'us-east', 'name': 'Newark, NJ', 'country': 'US'},
                {'code': 'us-central', 'name': 'Dallas, TX', 'country': 'US'},
                {'code': 'us-west', 'name': 'Fremont, CA', 'country': 'US'},
                {'code': 'eu-west', 'name': 'London, UK', 'country': 'GB'},
                {'code': 'eu-central', 'name': 'Frankfurt, DE', 'country': 'DE'},
                {'code': 'ap-south', 'name': 'Singapore', 'country': 'SG'},
                {'code': 'ap-northeast', 'name': 'Tokyo, JP', 'country': 'JP'}
            ],
            'vultr': [
                {'code': 'ewr', 'name': 'New Jersey', 'country': 'US'},
                {'code': 'ord', 'name': 'Chicago', 'country': 'US'},
                {'code': 'dfw', 'name': 'Dallas', 'country': 'US'},
                {'code': 'sea', 'name': 'Seattle', 'country': 'US'},
                {'code': 'lax', 'name': 'Los Angeles', 'country': 'US'},
                {'code': 'ams', 'name': 'Amsterdam', 'country': 'NL'},
                {'code': 'lhr', 'name': 'London', 'country': 'GB'},
                {'code': 'fra', 'name': 'Frankfurt', 'country': 'DE'},
                {'code': 'nrt', 'name': 'Tokyo', 'country': 'JP'},
                {'code': 'sgp', 'name': 'Singapore', 'country': 'SG'}
            ],
            'hetzner': [
                {'code': 'nbg1', 'name': 'Nuremberg', 'country': 'DE'},
                {'code': 'fsn1', 'name': 'Falkenstein', 'country': 'DE'},
                {'code': 'hel1', 'name': 'Helsinki', 'country': 'FI'},
                {'code': 'ash', 'name': 'Ashburn, VA', 'country': 'US'}
            ]
        }
        
        return jsonify({'regions': regions}), 200
        
    except Exception as e:
        logger.error(f"List regions error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500