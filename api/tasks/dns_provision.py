#!/usr/bin/env python3
"""
Cachenet CDN Platform DNS Provisioning Tasks
PowerDNS integration for domain DNS management
"""

import os
import logging
import requests
from datetime import datetime
from celery import shared_task
from models import db, Domain, EdgeNode, DNSRecord

logger = logging.getLogger(__name__)

PDNS_API_URL = os.getenv('PDNS_API_URL', 'http://powerdns:8081/api/v1/servers/localhost')
PDNS_API_KEY = os.getenv('PDNS_API_KEY')

def get_pdns_headers():
    """Get PowerDNS API headers"""
    return {
        'X-API-Key': PDNS_API_KEY,
        'Content-Type': 'application/json'
    }

@shared_task(bind=True, max_retries=3)
def provision_domain_dns(self, domain_id):
    """Provision DNS records for a domain across all edge nodes"""
    try:
        logger.info(f"Starting DNS provisioning for domain ID: {domain_id}")
        
        # Get domain
        domain = Domain.query.get(domain_id)
        if not domain:
            logger.error(f"Domain not found: {domain_id}")
            return {'error': 'Domain not found'}
        
        domain_name = domain.domain_name
        
        # Create zone in PowerDNS
        zone_data = {
            'name': domain_name,
            'kind': 'Native',
            'nameservers': [
                f'ns1.{os.getenv("CDN_DOMAIN", "cachenet.local")}',
                f'ns2.{os.getenv("CDN_DOMAIN", "cachenet.local")}'
            ],
            'records': []
        }
        
        # Create zone
        response = requests.post(
            f'{PDNS_API_URL}/zones',
            json=zone_data,
            headers=get_pdns_headers(),
            timeout=30
        )
        
        if response.status_code not in [201, 409]:  # 409 = zone already exists
            logger.error(f"Failed to create zone: {response.text}")
            raise Exception(f"Failed to create DNS zone: {response.status_code}")
        
        # Get active edge nodes
        edge_nodes = EdgeNode.query.filter_by(status='active').all()
        
        if not edge_nodes:
            logger.warning("No active edge nodes found")
            domain.status = 'error'
            db.session.commit()
            return {'error': 'No active edge nodes available'}
        
        # Create geo-distributed DNS records
        records_to_create = []
        dns_records_created = []
        
        for edge_node in edge_nodes:
            # Create A record for the edge node
            record_data = {
                'name': domain_name,
                'type': 'A',
                'content': edge_node.ip_address,
                'ttl': 300
            }
            records_to_create.append(record_data)
            
            # Create DNS record in database
            dns_record = DNSRecord(
                domain_id=domain.id,
                edge_node_id=edge_node.id,
                record_type='A',
                record_name=domain_name,
                record_value=edge_node.ip_address,
                ttl=300,
                geo_location=edge_node.region
            )
            db.session.add(dns_record)
            dns_records_created.append(dns_record)
        
        # Add CNAME for www subdomain
        www_record = {
            'name': f'www.{domain_name}',
            'type': 'CNAME',
            'content': domain_name,
            'ttl': 300
        }
        records_to_create.append(www_record)
        
        # Create CDN subdomain pointing to edge nodes (round-robin)
        for edge_node in edge_nodes:
            cdn_record = {
                'name': f'cdn.{domain_name}',
                'type': 'A',
                'content': edge_node.ip_address,
                'ttl': 60  # Lower TTL for faster failover
            }
            records_to_create.append(cdn_record)
        
        # Update zone with records
        zone_update_data = {
            'records': records_to_create
        }
        
        response = requests.patch(
            f'{PDNS_API_URL}/zones/{domain_name}',
            json=zone_update_data,
            headers=get_pdns_headers(),
            timeout=30
        )
        
        if response.status_code != 204:
            logger.error(f"Failed to update zone records: {response.text}")
            raise Exception(f"Failed to update DNS records: {response.status_code}")
        
        # Commit DNS records to database
        db.session.commit()
        
        # Update domain status
        domain.status = 'active'
        domain.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"DNS provisioning completed for domain: {domain_name}")
        
        return {
            'success': True,
            'domain': domain_name,
            'records_created': len(records_to_create),
            'edge_nodes': len(edge_nodes)
        }
        
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
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def update_domain_dns(self, domain_id, edge_node_id=None):
    """Update DNS records for a domain"""
    try:
        logger.info(f"Updating DNS records for domain ID: {domain_id}")
        
        domain = Domain.query.get(domain_id)
        if not domain:
            logger.error(f"Domain not found: {domain_id}")
            return {'error': 'Domain not found'}
        
        domain_name = domain.domain_name
        
        # Get current DNS records
        current_records = DNSRecord.query.filter_by(domain_id=domain.id).all()
        
        # Get active edge nodes
        if edge_node_id:
            edge_nodes = [EdgeNode.query.get(edge_node_id)]
        else:
            edge_nodes = EdgeNode.query.filter_by(status='active').all()
        
        # Build new record set
        new_records = []
        
        for edge_node in edge_nodes:
            if edge_node and edge_node.status == 'active':
                record_data = {
                    'name': domain_name,
                    'type': 'A',
                    'content': edge_node.ip_address,
                    'ttl': 300
                }
                new_records.append(record_data)
        
        # Update PowerDNS zone
        zone_update_data = {
            'records': new_records
        }
        
        response = requests.patch(
            f'{PDNS_API_URL}/zones/{domain_name}',
            json=zone_update_data,
            headers=get_pdns_headers(),
            timeout=30
        )
        
        if response.status_code != 204:
            logger.error(f"Failed to update DNS zone: {response.text}")
            raise Exception(f"Failed to update DNS zone: {response.status_code}")
        
        # Update database records
        if not edge_node_id:
            # Remove old records
            DNSRecord.query.filter_by(domain_id=domain.id).delete()
            
            # Add new records
            for edge_node in edge_nodes:
                if edge_node and edge_node.status == 'active':
                    dns_record = DNSRecord(
                        domain_id=domain.id,
                        edge_node_id=edge_node.id,
                        record_type='A',
                        record_name=domain_name,
                        record_value=edge_node.ip_address,
                        ttl=300,
                        geo_location=edge_node.region
                    )
                    db.session.add(dns_record)
        
        db.session.commit()
        
        logger.info(f"DNS records updated for domain: {domain_name}")
        
        return {
            'success': True,
            'domain': domain_name,
            'records_updated': len(new_records)
        }
        
    except Exception as e:
        logger.error(f"DNS update error for domain {domain_id}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying DNS update for domain {domain_id}")
            raise self.retry(countdown=30 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def remove_domain_dns(self, domain_name):
    """Remove DNS zone for a domain"""
    try:
        logger.info(f"Removing DNS zone for domain: {domain_name}")
        
        # Delete zone from PowerDNS
        response = requests.delete(
            f'{PDNS_API_URL}/zones/{domain_name}',
            headers=get_pdns_headers(),
            timeout=30
        )
        
        if response.status_code not in [204, 404]:  # 404 = zone doesn't exist
            logger.error(f"Failed to delete DNS zone: {response.text}")
            raise Exception(f"Failed to delete DNS zone: {response.status_code}")
        
        logger.info(f"DNS zone removed for domain: {domain_name}")
        
        return {
            'success': True,
            'domain': domain_name
        }
        
    except Exception as e:
        logger.error(f"DNS removal error for domain {domain_name}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying DNS removal for domain {domain_name}")
            raise self.retry(countdown=30 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task
def add_edge_node_to_dns(edge_node_id):
    """Add new edge node to all domain DNS records"""
    try:
        logger.info(f"Adding edge node to DNS: {edge_node_id}")
        
        edge_node = EdgeNode.query.get(edge_node_id)
        if not edge_node or edge_node.status != 'active':
            logger.error(f"Edge node not found or not active: {edge_node_id}")
            return {'error': 'Edge node not found or not active'}
        
        # Get all active domains
        domains = Domain.query.filter_by(status='active', cdn_enabled=True).all()
        
        for domain in domains:
            # Add DNS record for this edge node
            dns_record = DNSRecord(
                domain_id=domain.id,
                edge_node_id=edge_node.id,
                record_type='A',
                record_name=domain.domain_name,
                record_value=edge_node.ip_address,
                ttl=300,
                geo_location=edge_node.region
            )
            db.session.add(dns_record)
            
            # Update PowerDNS zone
            update_domain_dns.delay(domain.id)
        
        db.session.commit()
        
        logger.info(f"Edge node added to DNS for {len(domains)} domains")
        
        return {
            'success': True,
            'edge_node': edge_node.hostname,
            'domains_updated': len(domains)
        }
        
    except Exception as e:
        logger.error(f"Add edge node to DNS error: {str(e)}")
        return {'error': str(e)}

@shared_task
def remove_edge_node_from_dns(edge_node_id):
    """Remove edge node from all domain DNS records"""
    try:
        logger.info(f"Removing edge node from DNS: {edge_node_id}")
        
        # Get domains with this edge node
        dns_records = DNSRecord.query.filter_by(edge_node_id=edge_node_id).all()
        domain_ids = list(set([record.domain_id for record in dns_records]))
        
        # Remove DNS records
        DNSRecord.query.filter_by(edge_node_id=edge_node_id).delete()
        db.session.commit()
        
        # Update PowerDNS zones
        for domain_id in domain_ids:
            update_domain_dns.delay(domain_id)
        
        logger.info(f"Edge node removed from DNS for {len(domain_ids)} domains")
        
        return {
            'success': True,
            'domains_updated': len(domain_ids)
        }
        
    except Exception as e:
        logger.error(f"Remove edge node from DNS error: {str(e)}")
        return {'error': str(e)}