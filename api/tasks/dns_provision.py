#!/usr/bin/env python3
"""
XenCDN v8.2 - DNS Provisioning Tasks
PowerDNS integration for complete DNS zone management and automation
"""

import json
import requests
import os
import logging
from celery import shared_task
from datetime import datetime

# Logger setup
logger = logging.getLogger(__name__)

# PowerDNS Configuration
PDNS_API_URL = os.getenv('PDNS_API_URL', 'http://powerdns:8081/api/v1/servers/localhost')
PDNS_API_KEY = os.getenv('PDNS_API_KEY')
DNS_SERVER_NAME = os.getenv('DNS_SERVER_NAME', 'ns1.xencdn.com')
DNS_SERVER_NAME2 = os.getenv('DNS_SERVER_NAME2', 'ns2.xencdn.com')

def get_pdns_headers():
    """Get PowerDNS API headers"""
    return {
        'X-API-Key': PDNS_API_KEY,
        'Content-Type': 'application/json'
    }

def create_zone_in_powerdns(zone_name, ns_records):
    """Create a DNS zone in PowerDNS"""
    try:
        headers = get_pdns_headers()
        
        # Prepare zone data
        zone_data = {
            'name': zone_name,
            'kind': 'Native',
            'nameservers': ns_records,
            'rrsets': [
                {
                    'name': zone_name,
                    'type': 'NS',
                    'records': [{'content': ns, 'disabled': False} for ns in ns_records]
                },
                {
                    'name': zone_name,
                    'type': 'SOA',
                    'records': [{
                        'content': f"{DNS_SERVER_NAME} hostmaster.{zone_name} 1 10800 3600 604800 3600",
                        'disabled': False
                    }]
                }
            ]
        }
        
        # Create zone
        response = requests.post(
            f"{PDNS_API_URL}/zones",
            headers=headers,
            json=zone_data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"Zone {zone_name} created successfully in PowerDNS")
            return {'success': True, 'message': 'Zone created successfully'}
        elif response.status_code == 409:
            logger.info(f"Zone {zone_name} already exists in PowerDNS")
            return {'success': True, 'message': 'Zone already exists'}
        else:
            error_msg = f"PowerDNS API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Failed to create zone in PowerDNS: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

def delete_zone_from_powerdns(zone_name):
    """Delete a DNS zone from PowerDNS"""
    try:
        headers = get_pdns_headers()
        
        # Delete zone
        response = requests.delete(
            f"{PDNS_API_URL}/zones/{zone_name}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 204, 404]:  # 404 = zone doesn't exist
            logger.info(f"Zone {zone_name} deleted successfully from PowerDNS")
            return {'success': True, 'message': 'Zone deleted successfully'}
        else:
            error_msg = f"PowerDNS API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Failed to delete zone from PowerDNS: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

def create_record_in_powerdns(zone_name, record_data):
    """Create or update a DNS record in PowerDNS"""
    try:
        headers = get_pdns_headers()
        
        # Prepare record data for PowerDNS
        rrsets_data = {
            'rrsets': [
                {
                    'name': record_data['name'],
                    'type': record_data['type'],
                    'changetype': 'REPLACE',
                    'records': [
                        {
                            'content': record_data['content'],
                            'disabled': record_data.get('disabled', False)
                        }
                    ],
                    'ttl': record_data.get('ttl', 3600)
                }
            ]
        }
        
        # Add priority for MX records
        if record_data['type'] == 'MX' and 'priority' in record_data:
            rrsets_data['rrsets'][0]['records'][0]['content'] = f"{record_data['priority']} {record_data['content']}"
        
        # Update zone records
        response = requests.patch(
            f"{PDNS_API_URL}/zones/{zone_name}",
            headers=headers,
            json=rrsets_data,
            timeout=30
        )
        
        if response.status_code in [200, 204]:
            logger.info(f"Record {record_data['name']} created/updated successfully in PowerDNS")
            return {'success': True, 'message': 'Record created/updated successfully'}
        else:
            error_msg = f"PowerDNS API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Failed to create/update record in PowerDNS: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

def delete_record_from_powerdns(zone_name, record_name, record_type):
    """Delete a DNS record from PowerDNS"""
    try:
        headers = get_pdns_headers()
        
        # Prepare delete data
        rrsets_data = {
            'rrsets': [
                {
                    'name': record_name,
                    'type': record_type,
                    'changetype': 'DELETE'
                }
            ]
        }
        
        # Delete record
        response = requests.patch(
            f"{PDNS_API_URL}/zones/{zone_name}",
            headers=headers,
            json=rrsets_data,
            timeout=30
        )
        
        if response.status_code in [200, 204]:
            logger.info(f"Record {record_name} deleted successfully from PowerDNS")
            return {'success': True, 'message': 'Record deleted successfully'}
        else:
            error_msg = f"PowerDNS API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Failed to delete record from PowerDNS: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

@shared_task(bind=True, max_retries=3)
def create_zone_task(self, zone_name, ns_records):
    """Celery task to create DNS zone"""
    try:
        result = create_zone_in_powerdns(zone_name, ns_records)
        return result
    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {'success': False, 'error': str(e)}

@shared_task(bind=True, max_retries=3)
def create_record_task(self, zone_name, record_data):
    """Celery task to create DNS record"""
    try:
        result = create_record_in_powerdns(zone_name, record_data)
        return result
    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {'success': False, 'error': str(e)}

@shared_task(bind=True, max_retries=3)
def auto_provision_domain_task(self, domain_name, origin_ip, user_id):
    """Celery task to auto-provision domain with DNS and CDN"""
    try:
        from models import db, DNSZone, DNSRecord, Domain, User
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Create or get DNS zone
        zone = DNSZone.query.filter_by(name=domain_name).first()
        if not zone:
            # Create zone
            ns_records = [DNS_SERVER_NAME, DNS_SERVER_NAME2]
            powerdns_result = create_zone_in_powerdns(domain_name, ns_records)
            
            if not powerdns_result['success']:
                return powerdns_result
            
            # Create in database
            zone = DNSZone(
                name=domain_name,
                kind='Native',
                ns_records=json.dumps(ns_records),
                status='active'
            )
            db.session.add(zone)
            db.session.flush()  # Get the ID
        
        # Determine IP to use (anycast or origin)
        edge_mode = os.getenv('EDGE_MODE', 'single_ip')
        if edge_mode == 'bgp_anycast':
            anycast_ip = os.getenv('BGP_IP_BLOCK', '203.0.113.1').split('/')[0]
            target_ip = anycast_ip
        else:
            target_ip = origin_ip
        
        # Create A record pointing to target IP
        record_result = create_record_in_powerdns(domain_name, {
            'name': domain_name,
            'type': 'A',
            'content': target_ip,
            'ttl': 300
        })
        
        if record_result['success']:
            # Create record in database
            a_record = DNSRecord(
                zone_id=zone.id,
                name=domain_name,
                type='A',
                content=target_ip,
                ttl=300
            )
            db.session.add(a_record)
            
            # Create www CNAME
            create_record_in_powerdns(domain_name, {
                'name': f"www.{domain_name}",
                'type': 'CNAME',
                'content': domain_name,
                'ttl': 300
            })
            
            www_record = DNSRecord(
                zone_id=zone.id,
                name=f"www.{domain_name}",
                type='CNAME',
                content=domain_name,
                ttl=300
            )
            db.session.add(www_record)
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Domain {domain_name} auto-provisioned successfully',
            'nameservers': [DNS_SERVER_NAME, DNS_SERVER_NAME2],
            'target_ip': target_ip,
            'edge_mode': edge_mode
        }
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Auto-provision failed: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {'success': False, 'error': str(e)}

@shared_task(bind=True, max_retries=3)
def provision_domain_dns(self, domain_id):
    """Enhanced DNS provisioning for XenCDN v8.2"""
    try:
        from models import db, Domain, EdgeNode, DNSZone, DNSRecord
        
        logger.info(f"Starting DNS provisioning for domain ID: {domain_id}")
        
        # Get domain
        domain = Domain.query.get(domain_id)
        if not domain:
            logger.error(f"Domain not found: {domain_id}")
            return {'error': 'Domain not found'}
        
        domain_name = domain.domain_name
        
        # Auto-provision via the new task
        result = auto_provision_domain_task(domain_name, domain.origin_server, domain.user_id)
        
        if result['success']:
            # Update domain status
            domain.status = 'active'
            domain.updated_at = datetime.utcnow()
            db.session.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"DNS provisioning error for domain {domain_id}: {str(e)}")
        
        # Update domain status to error
        try:
            domain = Domain.query.get(domain_id)
            if domain:
                domain.status = 'error'
                domain.updated_at = datetime.utcnow()
                db.session.commit()
        except:
            pass
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying DNS provisioning for domain {domain_id}")
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=e)
        
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def remove_domain_dns(self, domain_name):
    """Remove DNS zone for a domain"""
    try:
        from models import db, DNSZone, DNSRecord
        
        logger.info(f"Removing DNS zone for domain: {domain_name}")
        
        # Delete zone from PowerDNS
        powerdns_result = delete_zone_from_powerdns(domain_name)
        
        if powerdns_result['success']:
            # Remove from database
            zone = DNSZone.query.filter_by(name=domain_name).first()
            if zone:
                db.session.delete(zone)  # Cascade will remove records
                db.session.commit()
        
        logger.info(f"DNS zone removed for domain: {domain_name}")
        return powerdns_result
        
    except Exception as e:
        logger.error(f"DNS removal error for domain {domain_name}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying DNS removal for domain {domain_name}")
            raise self.retry(countdown=30 * (self.request.retries + 1), exc=e)
        
        return {'error': str(e)}

@shared_task
def sync_zones_with_powerdns():
    """Sync all database zones with PowerDNS (maintenance task)"""
    try:
        from models import DNSZone
        
        zones = DNSZone.query.filter_by(status='active').all()
        synced_count = 0
        
        for zone in zones:
            try:
                # Get zone from PowerDNS
                headers = get_pdns_headers()
                response = requests.get(
                    f"{PDNS_API_URL}/zones/{zone.name}",
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    synced_count += 1
                    logger.info(f"Zone {zone.name} is in sync")
                else:
                    logger.warning(f"Zone {zone.name} not found in PowerDNS, recreating...")
                    # Recreate zone
                    ns_records = json.loads(zone.ns_records) if zone.ns_records else [DNS_SERVER_NAME, DNS_SERVER_NAME2]
                    create_zone_in_powerdns(zone.name, ns_records)
                    
            except Exception as e:
                logger.error(f"Failed to sync zone {zone.name}: {str(e)}")
        
        return {
            'success': True,
            'zones_processed': len(zones),
            'zones_synced': synced_count
        }
        
    except Exception as e:
        logger.error(f"Zone sync error: {str(e)}")
        return {'error': str(e)}