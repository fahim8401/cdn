#!/usr/bin/env python3
"""
XenCDN v8.2 - DNS Zone Management API Routes
PowerDNS integration for complete DNS control
"""

import json
import requests
import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import or_

from models import db, DNSZone, DNSRecord, User
from tasks.dns_provision import create_zone_in_powerdns, create_record_in_powerdns, delete_zone_from_powerdns, delete_record_from_powerdns

dns_zones_bp = Blueprint('dns_zones', __name__)

# PowerDNS API Configuration
PDNS_API_URL = os.getenv('PDNS_API_URL', 'http://powerdns:8081/api/v1/servers/localhost')
PDNS_API_KEY = os.getenv('PDNS_API_KEY')
DNS_SERVER_NAME = os.getenv('DNS_SERVER_NAME', 'ns1.xencdn.com')
DNS_SERVER_NAME2 = os.getenv('DNS_SERVER_NAME2', 'ns2.xencdn.com')

def validate_domain_name(domain):
    """Validate domain name format"""
    import re
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return re.match(pattern, domain) is not None

@dns_zones_bp.route('/api/dns/zones', methods=['GET'])
@jwt_required()
def list_dns_zones():
    """List all DNS zones"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        # Get query parameters
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 25)), 100)
        
        # Build query
        query = DNSZone.query
        
        if search:
            query = query.filter(DNSZone.name.ilike(f'%{search}%'))
        
        # Paginate results
        zones = query.order_by(DNSZone.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'zones': [zone.to_dict() for zone in zones.items],
            'pagination': {
                'page': page,
                'pages': zones.pages,
                'per_page': per_page,
                'total': zones.total
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dns_zones_bp.route('/api/dns/zones', methods=['POST'])
@jwt_required()
def create_dns_zone():
    """Create a new DNS zone"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        domain_name = data.get('name', '').strip().lower()
        
        if not domain_name:
            return jsonify({'error': 'Domain name is required'}), 400
        
        if not validate_domain_name(domain_name):
            return jsonify({'error': 'Invalid domain name format'}), 400
        
        # Check if zone already exists
        existing_zone = DNSZone.query.filter_by(name=domain_name).first()
        if existing_zone:
            return jsonify({'error': 'DNS zone already exists'}), 409
        
        # Create zone in PowerDNS first
        ns_records = [DNS_SERVER_NAME, DNS_SERVER_NAME2]
        powerdns_result = create_zone_in_powerdns(domain_name, ns_records)
        
        if not powerdns_result['success']:
            return jsonify({'error': f'Failed to create zone in PowerDNS: {powerdns_result["error"]}'}), 500
        
        # Create zone in database
        zone = DNSZone(
            name=domain_name,
            kind='Native',
            ns_records=json.dumps(ns_records),
            status='active'
        )
        
        db.session.add(zone)
        db.session.commit()
        
        # Create default NS records in database
        for i, ns in enumerate(ns_records):
            ns_record = DNSRecord(
                zone_id=zone.id,
                name=domain_name,
                type='NS',
                content=ns,
                ttl=3600,
                priority=i + 1
            )
            db.session.add(ns_record)
        
        # Create default SOA record
        soa_content = f"{DNS_SERVER_NAME} hostmaster.{domain_name} 1 10800 3600 604800 3600"
        soa_record = DNSRecord(
            zone_id=zone.id,
            name=domain_name,
            type='SOA',
            content=soa_content,
            ttl=3600
        )
        db.session.add(soa_record)
        
        db.session.commit()
        
        return jsonify({
            'message': 'DNS zone created successfully',
            'zone': zone.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@dns_zones_bp.route('/api/dns/zones/<int:zone_id>', methods=['DELETE'])
@jwt_required()
def delete_dns_zone(zone_id):
    """Delete a DNS zone and all its records"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        zone = DNSZone.query.get_or_404(zone_id)
        
        # Delete zone from PowerDNS first
        powerdns_result = delete_zone_from_powerdns(zone.name)
        
        if not powerdns_result['success']:
            return jsonify({'error': f'Failed to delete zone from PowerDNS: {powerdns_result["error"]}'}), 500
        
        # Delete zone and all records from database (cascade)
        db.session.delete(zone)
        db.session.commit()
        
        return jsonify({'message': 'DNS zone deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@dns_zones_bp.route('/api/dns/zones/<int:zone_id>/records', methods=['GET'])
@jwt_required()
def list_zone_records(zone_id):
    """List all records in a DNS zone"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        zone = DNSZone.query.get_or_404(zone_id)
        
        # Get query parameters
        record_type = request.args.get('type', '')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        # Build query
        query = DNSRecord.query.filter_by(zone_id=zone_id)
        
        if record_type:
            query = query.filter_by(type=record_type.upper())
        
        # Paginate results
        records = query.order_by(DNSRecord.type, DNSRecord.name).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'zone': zone.to_dict(),
            'records': [record.to_dict() for record in records.items],
            'pagination': {
                'page': page,
                'pages': records.pages,
                'per_page': per_page,
                'total': records.total
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dns_zones_bp.route('/api/dns/zones/<int:zone_id>/records', methods=['POST'])
@jwt_required()
def create_dns_record(zone_id):
    """Create a new DNS record in a zone"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        zone = DNSZone.query.get_or_404(zone_id)
        data = request.get_json()
        
        # Validate input
        record_name = data.get('name', '').strip()
        record_type = data.get('type', '').strip().upper()
        record_content = data.get('content', '').strip()
        record_ttl = int(data.get('ttl', 3600))
        record_priority = int(data.get('priority', 0))
        
        if not all([record_name, record_type, record_content]):
            return jsonify({'error': 'Name, type, and content are required'}), 400
        
        # Validate record type
        valid_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA']
        if record_type not in valid_types:
            return jsonify({'error': f'Invalid record type. Must be one of: {", ".join(valid_types)}'}), 400
        
        # Process record name (handle @ for root domain)
        if record_name == '@':
            full_record_name = zone.name
        elif record_name.endswith('.'):
            full_record_name = record_name[:-1]  # Remove trailing dot
        elif '.' in record_name and not record_name.endswith(zone.name):
            full_record_name = record_name  # Already fully qualified
        else:
            full_record_name = f"{record_name}.{zone.name}"
        
        # Create record in PowerDNS first
        powerdns_result = create_record_in_powerdns(zone.name, {
            'name': full_record_name,
            'type': record_type,
            'content': record_content,
            'ttl': record_ttl,
            'priority': record_priority if record_type == 'MX' else 0
        })
        
        if not powerdns_result['success']:
            return jsonify({'error': f'Failed to create record in PowerDNS: {powerdns_result["error"]}'}), 500
        
        # Create record in database
        record = DNSRecord(
            zone_id=zone_id,
            name=full_record_name,
            type=record_type,
            content=record_content,
            ttl=record_ttl,
            priority=record_priority if record_type == 'MX' else 0
        )
        
        db.session.add(record)
        db.session.commit()
        
        return jsonify({
            'message': 'DNS record created successfully',
            'record': record.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@dns_zones_bp.route('/api/dns/zones/<int:zone_id>/records/<int:record_id>', methods=['PUT'])
@jwt_required()
def update_dns_record(zone_id, record_id):
    """Update a DNS record"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        zone = DNSZone.query.get_or_404(zone_id)
        record = DNSRecord.query.filter_by(id=record_id, zone_id=zone_id).first_or_404()
        
        data = request.get_json()
        
        # Update fields if provided
        if 'content' in data:
            record.content = data['content'].strip()
        if 'ttl' in data:
            record.ttl = int(data['ttl'])
        if 'priority' in data and record.type == 'MX':
            record.priority = int(data['priority'])
        if 'disabled' in data:
            record.disabled = bool(data['disabled'])
        
        record.updated_at = datetime.utcnow()
        
        # Update record in PowerDNS
        powerdns_result = create_record_in_powerdns(zone.name, {
            'name': record.name,
            'type': record.type,
            'content': record.content,
            'ttl': record.ttl,
            'priority': record.priority,
            'disabled': record.disabled
        })
        
        if not powerdns_result['success']:
            return jsonify({'error': f'Failed to update record in PowerDNS: {powerdns_result["error"]}'}), 500
        
        db.session.commit()
        
        return jsonify({
            'message': 'DNS record updated successfully',
            'record': record.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@dns_zones_bp.route('/api/dns/zones/<int:zone_id>/records/<int:record_id>', methods=['DELETE'])
@jwt_required()
def delete_dns_record(zone_id, record_id):
    """Delete a DNS record"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        zone = DNSZone.query.get_or_404(zone_id)
        record = DNSRecord.query.filter_by(id=record_id, zone_id=zone_id).first_or_404()
        
        # Prevent deletion of essential records
        if record.type in ['SOA', 'NS'] and record.name == zone.name:
            return jsonify({'error': 'Cannot delete essential SOA or NS records'}), 400
        
        # Delete record from PowerDNS first
        powerdns_result = delete_record_from_powerdns(zone.name, record.name, record.type)
        
        if not powerdns_result['success']:
            return jsonify({'error': f'Failed to delete record from PowerDNS: {powerdns_result["error"]}'}), 500
        
        # Delete record from database
        db.session.delete(record)
        db.session.commit()
        
        return jsonify({'message': 'DNS record deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@dns_zones_bp.route('/api/dns/zones/<int:zone_id>/provision', methods=['POST'])
@jwt_required()
def auto_provision_cdn(zone_id):
    """Auto-provision CDN for a domain zone"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        zone = DNSZone.query.get_or_404(zone_id)
        data = request.get_json()
        
        # Get anycast IP or generate one
        anycast_ip = data.get('anycast_ip', '203.0.113.1')  # Default anycast IP
        
        # Check if A record for root domain already exists
        existing_a_record = DNSRecord.query.filter_by(
            zone_id=zone_id, 
            name=zone.name, 
            type='A'
        ).first()
        
        if existing_a_record:
            # Update existing record
            existing_a_record.content = anycast_ip
            existing_a_record.updated_at = datetime.utcnow()
            
            # Update in PowerDNS
            powerdns_result = create_record_in_powerdns(zone.name, {
                'name': zone.name,
                'type': 'A',
                'content': anycast_ip,
                'ttl': 300  # Short TTL for CDN
            })
            
            message = 'CDN A record updated successfully'
        else:
            # Create new A record for root domain
            a_record = DNSRecord(
                zone_id=zone_id,
                name=zone.name,
                type='A',
                content=anycast_ip,
                ttl=300  # Short TTL for CDN
            )
            
            db.session.add(a_record)
            
            # Create in PowerDNS
            powerdns_result = create_record_in_powerdns(zone.name, {
                'name': zone.name,
                'type': 'A',
                'content': anycast_ip,
                'ttl': 300
            })
            
            message = 'CDN A record created successfully'
        
        if not powerdns_result['success']:
            return jsonify({'error': f'Failed to provision CDN record: {powerdns_result["error"]}'}), 500
        
        # Also create www CNAME if it doesn't exist
        www_name = f"www.{zone.name}"
        existing_www = DNSRecord.query.filter_by(
            zone_id=zone_id,
            name=www_name,
            type='CNAME'
        ).first()
        
        if not existing_www:
            www_record = DNSRecord(
                zone_id=zone_id,
                name=www_name,
                type='CNAME',
                content=zone.name,
                ttl=300
            )
            db.session.add(www_record)
            
            # Create in PowerDNS
            create_record_in_powerdns(zone.name, {
                'name': www_name,
                'type': 'CNAME',
                'content': zone.name,
                'ttl': 300
            })
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'anycast_ip': anycast_ip,
            'instructions': f'Domain {zone.name} is now provisioned for CDN. Update your nameservers to {DNS_SERVER_NAME} and {DNS_SERVER_NAME2}'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@dns_zones_bp.route('/api/dns/zones/search', methods=['GET'])
@jwt_required()
def search_dns_zones():
    """Search DNS zones by name or records"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        # Search zones by name
        zones = DNSZone.query.filter(
            or_(
                DNSZone.name.ilike(f'%{query}%'),
                DNSZone.ns_records.ilike(f'%{query}%')
            )
        ).limit(50).all()
        
        # Search records by name or content
        records = DNSRecord.query.join(DNSZone).filter(
            or_(
                DNSRecord.name.ilike(f'%{query}%'),
                DNSRecord.content.ilike(f'%{query}%'),
                DNSZone.name.ilike(f'%{query}%')
            )
        ).limit(50).all()
        
        return jsonify({
            'query': query,
            'zones': [zone.to_dict() for zone in zones],
            'records': [record.to_dict() for record in records]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500