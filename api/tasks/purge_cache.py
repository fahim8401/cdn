#!/usr/bin/env python3
"""
Cachenet CDN Platform Cache Purging Tasks
Nginx cache purging across edge nodes
"""

import os
import logging
import requests
import paramiko
from datetime import datetime
from celery import shared_task
from models import db, Domain, EdgeNode, DNSRecord

logger = logging.getLogger(__name__)

SSH_USER = os.getenv('EDGE_SSH_USER', 'root')
SSH_KEY_PATH = os.getenv('EDGE_SSH_KEY', '/app/ansible/keys/cachenet-ed25519')

def execute_ssh_command(hostname, command, timeout=30):
    """Execute SSH command on edge node"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load SSH key
        key = paramiko.Ed25519Key.from_private_key_file(SSH_KEY_PATH)
        
        # Connect to edge node
        ssh.connect(
            hostname=hostname,
            username=SSH_USER,
            pkey=key,
            timeout=timeout,
            banner_timeout=30
        )
        
        # Execute command
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        
        # Get output
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        
        ssh.close()
        
        return {
            'success': exit_code == 0,
            'output': output,
            'error': error,
            'exit_code': exit_code
        }
        
    except Exception as e:
        logger.error(f"SSH command execution error on {hostname}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'exit_code': -1
        }

@shared_task(bind=True, max_retries=3)
def purge_domain_cache(self, domain_id):
    """Purge entire domain cache across all edge nodes"""
    try:
        logger.info(f"Starting domain cache purge for domain ID: {domain_id}")
        
        # Get domain
        domain = Domain.query.get(domain_id)
        if not domain:
            logger.error(f"Domain not found: {domain_id}")
            return {'error': 'Domain not found'}
        
        domain_name = domain.domain_name
        
        # Get edge nodes serving this domain
        dns_records = DNSRecord.query.filter_by(domain_id=domain.id).all()
        edge_node_ids = [record.edge_node_id for record in dns_records]
        edge_nodes = EdgeNode.query.filter(
            EdgeNode.id.in_(edge_node_ids),
            EdgeNode.status == 'active'
        ).all()
        
        if not edge_nodes:
            logger.warning(f"No active edge nodes found for domain: {domain_name}")
            return {'error': 'No active edge nodes found'}
        
        purge_results = []
        successful_purges = 0
        
        for edge_node in edge_nodes:
            try:
                # Nginx cache purge command
                purge_command = f"""
                # Purge Nginx cache for domain
                find /var/cache/nginx -name "*{domain_name}*" -type f -delete
                
                # Reload Nginx to clear any in-memory cache
                nginx -s reload
                
                # Log purge event
                echo "$(date): Cache purged for {domain_name}" >> /var/log/cachenet-purge.log
                """
                
                result = execute_ssh_command(edge_node.ip_address, purge_command)
                
                if result['success']:
                    logger.info(f"Cache purged successfully on {edge_node.hostname}")
                    successful_purges += 1
                else:
                    logger.error(f"Cache purge failed on {edge_node.hostname}: {result['error']}")
                
                purge_results.append({
                    'edge_node': edge_node.hostname,
                    'success': result['success'],
                    'error': result.get('error')
                })
                
            except Exception as e:
                logger.error(f"Error purging cache on {edge_node.hostname}: {str(e)}")
                purge_results.append({
                    'edge_node': edge_node.hostname,
                    'success': False,
                    'error': str(e)
                })
        
        # Log purge event
        logger.info(f"Domain cache purge completed: {domain_name} ({successful_purges}/{len(edge_nodes)} nodes)")
        
        return {
            'success': successful_purges > 0,
            'domain': domain_name,
            'total_nodes': len(edge_nodes),
            'successful_purges': successful_purges,
            'results': purge_results
        }
        
    except Exception as e:
        logger.error(f"Domain cache purge error for domain {domain_id}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying domain cache purge for domain {domain_id}")
            raise self.retry(countdown=30 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def purge_url_cache(self, domain_id, url_path, wildcard=False):
    """Purge specific URL from cache across all edge nodes"""
    try:
        logger.info(f"Starting URL cache purge for domain ID: {domain_id}, path: {url_path}")
        
        # Get domain
        domain = Domain.query.get(domain_id)
        if not domain:
            logger.error(f"Domain not found: {domain_id}")
            return {'error': 'Domain not found'}
        
        domain_name = domain.domain_name
        
        # Get edge nodes serving this domain
        dns_records = DNSRecord.query.filter_by(domain_id=domain.id).all()
        edge_node_ids = [record.edge_node_id for record in dns_records]
        edge_nodes = EdgeNode.query.filter(
            EdgeNode.id.in_(edge_node_ids),
            EdgeNode.status == 'active'
        ).all()
        
        if not edge_nodes:
            logger.warning(f"No active edge nodes found for domain: {domain_name}")
            return {'error': 'No active edge nodes found'}
        
        # Normalize URL path
        if not url_path.startswith('/'):
            url_path = '/' + url_path
        
        purge_results = []
        successful_purges = 0
        
        for edge_node in edge_nodes:
            try:
                if wildcard:
                    # Wildcard purge using pattern matching
                    purge_command = f"""
                    # Purge Nginx cache using wildcard pattern
                    find /var/cache/nginx -name "*{domain_name}*" -type f | while read file; do
                        if grep -q "{url_path}" "$file" 2>/dev/null; then
                            rm -f "$file"
                        fi
                    done
                    
                    # Reload Nginx
                    nginx -s reload
                    
                    # Log purge event
                    echo "$(date): Wildcard cache purged for {domain_name}{url_path}" >> /var/log/cachenet-purge.log
                    """
                else:
                    # Specific URL purge
                    # Create cache key based on Nginx naming convention
                    cache_key = f"{domain_name}{url_path}".replace('/', '_').replace('?', '_').replace('&', '_')
                    
                    purge_command = f"""
                    # Purge specific URL from Nginx cache
                    find /var/cache/nginx -name "*{cache_key}*" -type f -delete
                    
                    # Also try alternative cache key formats
                    find /var/cache/nginx -name "*{domain_name}*" -type f | while read file; do
                        if grep -q "{url_path}" "$file" 2>/dev/null; then
                            rm -f "$file"
                        fi
                    done
                    
                    # Reload Nginx
                    nginx -s reload
                    
                    # Log purge event
                    echo "$(date): URL cache purged for {domain_name}{url_path}" >> /var/log/cachenet-purge.log
                    """
                
                result = execute_ssh_command(edge_node.ip_address, purge_command)
                
                if result['success']:
                    logger.info(f"URL cache purged successfully on {edge_node.hostname}")
                    successful_purges += 1
                else:
                    logger.error(f"URL cache purge failed on {edge_node.hostname}: {result['error']}")
                
                purge_results.append({
                    'edge_node': edge_node.hostname,
                    'success': result['success'],
                    'error': result.get('error')
                })
                
            except Exception as e:
                logger.error(f"Error purging URL cache on {edge_node.hostname}: {str(e)}")
                purge_results.append({
                    'edge_node': edge_node.hostname,
                    'success': False,
                    'error': str(e)
                })
        
        # Log purge event
        purge_type = "wildcard" if wildcard else "URL"
        logger.info(f"{purge_type} cache purge completed: {domain_name}{url_path} ({successful_purges}/{len(edge_nodes)} nodes)")
        
        return {
            'success': successful_purges > 0,
            'domain': domain_name,
            'url_path': url_path,
            'wildcard': wildcard,
            'total_nodes': len(edge_nodes),
            'successful_purges': successful_purges,
            'results': purge_results
        }
        
    except Exception as e:
        logger.error(f"URL cache purge error for domain {domain_id}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying URL cache purge for domain {domain_id}")
            raise self.retry(countdown=30 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def purge_edge_cache(self, edge_node_id, domain_name=None):
    """Purge all cache on specific edge node"""
    try:
        logger.info(f"Starting edge cache purge for edge node ID: {edge_node_id}")
        
        # Get edge node
        edge_node = EdgeNode.query.get(edge_node_id)
        if not edge_node:
            logger.error(f"Edge node not found: {edge_node_id}")
            return {'error': 'Edge node not found'}
        
        if edge_node.status != 'active':
            logger.error(f"Edge node not active: {edge_node.hostname}")
            return {'error': 'Edge node not active'}
        
        try:
            if domain_name:
                # Purge specific domain cache
                purge_command = f"""
                # Purge cache for specific domain
                find /var/cache/nginx -name "*{domain_name}*" -type f -delete
                
                # Reload Nginx
                nginx -s reload
                
                # Log purge event
                echo "$(date): Domain cache purged for {domain_name}" >> /var/log/cachenet-purge.log
                """
            else:
                # Purge all cache
                purge_command = """
                # Purge all Nginx cache
                rm -rf /var/cache/nginx/*
                
                # Restart Nginx to ensure clean state
                systemctl restart nginx
                
                # Log purge event
                echo "$(date): All cache purged" >> /var/log/cachenet-purge.log
                """
            
            result = execute_ssh_command(edge_node.ip_address, purge_command)
            
            if result['success']:
                logger.info(f"Edge cache purged successfully on {edge_node.hostname}")
                return {
                    'success': True,
                    'edge_node': edge_node.hostname,
                    'domain': domain_name
                }
            else:
                logger.error(f"Edge cache purge failed on {edge_node.hostname}: {result['error']}")
                return {
                    'success': False,
                    'edge_node': edge_node.hostname,
                    'error': result['error']
                }
                
        except Exception as e:
            logger.error(f"Error purging edge cache on {edge_node.hostname}: {str(e)}")
            return {
                'success': False,
                'edge_node': edge_node.hostname,
                'error': str(e)
            }
        
    except Exception as e:
        logger.error(f"Edge cache purge error for edge node {edge_node_id}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying edge cache purge for edge node {edge_node_id}")
            raise self.retry(countdown=30 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task
def bulk_purge_domains(domain_ids):
    """Bulk purge cache for multiple domains"""
    try:
        logger.info(f"Starting bulk cache purge for {len(domain_ids)} domains")
        
        results = []
        
        for domain_id in domain_ids:
            try:
                # Trigger domain cache purge
                task_result = purge_domain_cache.delay(domain_id)
                results.append({
                    'domain_id': domain_id,
                    'task_id': task_result.id
                })
            except Exception as e:
                logger.error(f"Error starting purge for domain {domain_id}: {str(e)}")
                results.append({
                    'domain_id': domain_id,
                    'error': str(e)
                })
        
        logger.info(f"Bulk cache purge initiated for {len(results)} domains")
        
        return {
            'success': True,
            'total_domains': len(domain_ids),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Bulk purge domains error: {str(e)}")
        return {'error': str(e)}

@shared_task
def scheduled_cache_cleanup():
    """Scheduled task to clean up old cache files"""
    try:
        logger.info("Starting scheduled cache cleanup")
        
        # Get all active edge nodes
        edge_nodes = EdgeNode.query.filter_by(status='active').all()
        
        cleanup_results = []
        
        for edge_node in edge_nodes:
            try:
                # Clean up cache files older than 24 hours
                cleanup_command = """
                # Clean up old cache files (older than 24 hours)
                find /var/cache/nginx -type f -mtime +1 -delete
                
                # Clean up empty directories
                find /var/cache/nginx -type d -empty -delete
                
                # Log cleanup event
                echo "$(date): Scheduled cache cleanup completed" >> /var/log/cachenet-cleanup.log
                """
                
                result = execute_ssh_command(edge_node.ip_address, cleanup_command)
                
                cleanup_results.append({
                    'edge_node': edge_node.hostname,
                    'success': result['success'],
                    'error': result.get('error')
                })
                
            except Exception as e:
                logger.error(f"Error cleaning up cache on {edge_node.hostname}: {str(e)}")
                cleanup_results.append({
                    'edge_node': edge_node.hostname,
                    'success': False,
                    'error': str(e)
                })
        
        successful_cleanups = sum(1 for result in cleanup_results if result['success'])
        
        logger.info(f"Scheduled cache cleanup completed: {successful_cleanups}/{len(edge_nodes)} nodes")
        
        return {
            'success': True,
            'total_nodes': len(edge_nodes),
            'successful_cleanups': successful_cleanups,
            'results': cleanup_results
        }
        
    except Exception as e:
        logger.error(f"Scheduled cache cleanup error: {str(e)}")
        return {'error': str(e)}