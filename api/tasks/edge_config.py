#!/usr/bin/env python3
"""
Cachenet CDN Platform Edge Configuration Tasks
Ansible integration for edge node deployment and configuration
"""

import os
import logging
import subprocess
import tempfile
from datetime import datetime, timedelta
from celery import shared_task
from models import db, Domain, EdgeNode, CacheStats

logger = logging.getLogger(__name__)

ANSIBLE_PATH = '/app/ansible'
ANSIBLE_INVENTORY = f'{ANSIBLE_PATH}/inventory.ini'
ANSIBLE_CONFIG = f'{ANSIBLE_PATH}/ansible.cfg'

def run_ansible_playbook(playbook_name, extra_vars=None, limit=None):
    """Run Ansible playbook with error handling"""
    try:
        cmd = [
            'ansible-playbook',
            f'{ANSIBLE_PATH}/playbooks/{playbook_name}',
            '-i', ANSIBLE_INVENTORY,
            '--config-file', ANSIBLE_CONFIG,
            '-v'
        ]
        
        if limit:
            cmd.extend(['--limit', limit])
        
        if extra_vars:
            cmd.extend(['--extra-vars', extra_vars])
        
        # Run playbook
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes timeout
            cwd=ANSIBLE_PATH
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"Ansible playbook {playbook_name} timed out")
        return {
            'success': False,
            'error': 'Playbook execution timed out',
            'return_code': -1
        }
    except Exception as e:
        logger.error(f"Error running Ansible playbook {playbook_name}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'return_code': -1
        }

def update_ansible_inventory():
    """Update Ansible inventory with current edge nodes"""
    try:
        edge_nodes = EdgeNode.query.filter_by(status='active').all()
        
        inventory_content = """[edge_nodes]
"""
        
        for node in edge_nodes:
            inventory_content += f"{node.hostname} ansible_host={node.ip_address} ansible_user=root region={node.region}\n"
        
        # Write inventory file
        with open(ANSIBLE_INVENTORY, 'w') as f:
            f.write(inventory_content)
        
        logger.info(f"Ansible inventory updated with {len(edge_nodes)} edge nodes")
        return True
        
    except Exception as e:
        logger.error(f"Error updating Ansible inventory: {str(e)}")
        return False

@shared_task(bind=True, max_retries=3)
def deploy_domain_config(self, domain_id):
    """Deploy domain configuration to all edge nodes"""
    try:
        logger.info(f"Deploying domain configuration for domain ID: {domain_id}")
        
        # Get domain
        domain = Domain.query.get(domain_id)
        if not domain:
            logger.error(f"Domain not found: {domain_id}")
            return {'error': 'Domain not found'}
        
        # Update Ansible inventory
        if not update_ansible_inventory():
            raise Exception("Failed to update Ansible inventory")
        
        # Prepare extra variables for Ansible
        extra_vars = f"""{{
            "domain_name": "{domain.domain_name}",
            "origin_server": "{domain.origin_server}",
            "cache_ttl": {domain.cache_ttl},
            "cdn_enabled": {"true" if domain.cdn_enabled else "false"},
            "ssl_enabled": {"true" if domain.ssl_enabled else "false"}
        }}"""
        
        # Run deployment playbook
        result = run_ansible_playbook('deploy-edge.yml', extra_vars)
        
        if result['success']:
            logger.info(f"Domain configuration deployed successfully: {domain.domain_name}")
            return {
                'success': True,
                'domain': domain.domain_name,
                'stdout': result['stdout']
            }
        else:
            logger.error(f"Domain configuration deployment failed: {result.get('stderr', 'Unknown error')}")
            raise Exception(f"Deployment failed: {result.get('stderr', 'Unknown error')}")
        
    except Exception as e:
        logger.error(f"Deploy domain config error for domain {domain_id}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying domain config deployment for domain {domain_id}")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def deploy_edge_node(self, edge_node_id):
    """Deploy and configure new edge node"""
    try:
        logger.info(f"Deploying edge node ID: {edge_node_id}")
        
        # Get edge node
        edge_node = EdgeNode.query.get(edge_node_id)
        if not edge_node:
            logger.error(f"Edge node not found: {edge_node_id}")
            return {'error': 'Edge node not found'}
        
        # Update edge node status
        edge_node.status = 'deploying'
        db.session.commit()
        
        # Create temporary inventory for this node
        temp_inventory_content = f"""[new_edge_nodes]
{edge_node.hostname} ansible_host={edge_node.ip_address} ansible_user=root region={edge_node.region}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as temp_inventory:
            temp_inventory.write(temp_inventory_content)
            temp_inventory_path = temp_inventory.name
        
        try:
            # Prepare extra variables
            extra_vars = f"""{{
                "edge_node_name": "{edge_node.name}",
                "edge_node_hostname": "{edge_node.hostname}",
                "edge_node_region": "{edge_node.region}",
                "max_clients": {edge_node.max_clients}
            }}"""
            
            # Run edge deployment playbook
            cmd = [
                'ansible-playbook',
                f'{ANSIBLE_PATH}/playbooks/deploy-edge.yml',
                '-i', temp_inventory_path,
                '--config-file', ANSIBLE_CONFIG,
                '--extra-vars', extra_vars,
                '--limit', edge_node.hostname,
                '-v'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1200,  # 20 minutes timeout for initial deployment
                cwd=ANSIBLE_PATH
            )
            
            if result.returncode == 0:
                # Update edge node status
                edge_node.status = 'active'
                edge_node.last_seen = datetime.utcnow()
                edge_node.updated_at = datetime.utcnow()
                db.session.commit()
                
                # Update main inventory
                update_ansible_inventory()
                
                logger.info(f"Edge node deployed successfully: {edge_node.hostname}")
                
                return {
                    'success': True,
                    'edge_node': edge_node.hostname,
                    'stdout': result.stdout
                }
            else:
                # Update edge node status to error
                edge_node.status = 'error'
                edge_node.updated_at = datetime.utcnow()
                db.session.commit()
                
                logger.error(f"Edge node deployment failed: {result.stderr}")
                raise Exception(f"Deployment failed: {result.stderr}")
                
        finally:
            # Clean up temporary inventory file
            os.unlink(temp_inventory_path)
        
    except Exception as e:
        logger.error(f"Deploy edge node error for node {edge_node_id}: {str(e)}")
        
        # Update edge node status to error
        try:
            edge_node = EdgeNode.query.get(edge_node_id)
            if edge_node:
                edge_node.status = 'error'
                edge_node.updated_at = datetime.utcnow()
                db.session.commit()
        except:
            pass
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying edge node deployment for node {edge_node_id}")
            raise self.retry(countdown=120 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def update_origin_server(self, domain_id, new_origin):
    """Update origin server configuration on all edge nodes"""
    try:
        logger.info(f"Updating origin server for domain ID: {domain_id}")
        
        # Get domain
        domain = Domain.query.get(domain_id)
        if not domain:
            logger.error(f"Domain not found: {domain_id}")
            return {'error': 'Domain not found'}
        
        # Update Ansible inventory
        if not update_ansible_inventory():
            raise Exception("Failed to update Ansible inventory")
        
        # Prepare extra variables
        extra_vars = f"""{{
            "domain_name": "{domain.domain_name}",
            "old_origin": "{domain.origin_server}",
            "new_origin": "{new_origin}"
        }}"""
        
        # Run origin update playbook
        result = run_ansible_playbook('update-origin.yml', extra_vars)
        
        if result['success']:
            logger.info(f"Origin server updated successfully: {domain.domain_name}")
            return {
                'success': True,
                'domain': domain.domain_name,
                'new_origin': new_origin,
                'stdout': result['stdout']
            }
        else:
            logger.error(f"Origin server update failed: {result.get('stderr', 'Unknown error')}")
            raise Exception(f"Origin update failed: {result.get('stderr', 'Unknown error')}")
        
    except Exception as e:
        logger.error(f"Update origin server error for domain {domain_id}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying origin server update for domain {domain_id}")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task
def update_edge_statistics():
    """Update edge node statistics and metrics"""
    try:
        logger.info("Updating edge node statistics")
        
        # Get all active edge nodes
        edge_nodes = EdgeNode.query.filter_by(status='active').all()
        
        for edge_node in edge_nodes:
            try:
                # Check if node is still responsive
                last_seen_threshold = datetime.utcnow() - timedelta(minutes=10)
                
                if edge_node.last_seen and edge_node.last_seen < last_seen_threshold:
                    # Mark as maintenance if not seen for 10 minutes
                    edge_node.status = 'maintenance'
                    logger.warning(f"Edge node marked as maintenance: {edge_node.hostname}")
                
                # Update load score based on client count
                if edge_node.client_count and edge_node.max_clients:
                    edge_node.load_score = edge_node.client_count / edge_node.max_clients
                else:
                    edge_node.load_score = 0.0
                
                edge_node.updated_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Error updating statistics for edge node {edge_node.hostname}: {str(e)}")
        
        db.session.commit()
        
        logger.info(f"Edge node statistics updated for {len(edge_nodes)} nodes")
        
        return {
            'success': True,
            'nodes_updated': len(edge_nodes)
        }
        
    except Exception as e:
        logger.error(f"Update edge statistics error: {str(e)}")
        return {'error': str(e)}

@shared_task
def collect_cache_statistics():
    """Collect cache statistics from all edge nodes"""
    try:
        logger.info("Collecting cache statistics from edge nodes")
        
        # Update Ansible inventory
        if not update_ansible_inventory():
            raise Exception("Failed to update Ansible inventory")
        
        # Run statistics collection playbook
        result = run_ansible_playbook('collect-stats.yml')
        
        if result['success']:
            logger.info("Cache statistics collected successfully")
            
            # Parse and store statistics (simplified)
            # In a real implementation, you would parse the Ansible output
            # and update the CacheStats table with actual data
            
            return {
                'success': True,
                'stdout': result['stdout']
            }
        else:
            logger.error(f"Cache statistics collection failed: {result.get('stderr', 'Unknown error')}")
            return {
                'success': False,
                'error': result.get('stderr', 'Unknown error')
            }
        
    except Exception as e:
        logger.error(f"Collect cache statistics error: {str(e)}")
        return {'error': str(e)}

@shared_task
def maintenance_mode_toggle(edge_node_id, enable_maintenance=True):
    """Toggle maintenance mode for edge node"""
    try:
        logger.info(f"Toggling maintenance mode for edge node ID: {edge_node_id}")
        
        # Get edge node
        edge_node = EdgeNode.query.get(edge_node_id)
        if not edge_node:
            logger.error(f"Edge node not found: {edge_node_id}")
            return {'error': 'Edge node not found'}
        
        # Update status
        if enable_maintenance:
            edge_node.status = 'maintenance'
        else:
            edge_node.status = 'active'
        
        edge_node.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Update Ansible inventory
        update_ansible_inventory()
        
        mode = "enabled" if enable_maintenance else "disabled"
        logger.info(f"Maintenance mode {mode} for edge node: {edge_node.hostname}")
        
        return {
            'success': True,
            'edge_node': edge_node.hostname,
            'maintenance_mode': enable_maintenance
        }
        
    except Exception as e:
        logger.error(f"Maintenance mode toggle error for edge node {edge_node_id}: {str(e)}")
        return {'error': str(e)}

@shared_task
def bulk_deploy_domains():
    """Deploy all active domains to all edge nodes"""
    try:
        logger.info("Starting bulk domain deployment")
        
        # Get all active domains
        domains = Domain.query.filter_by(status='active', cdn_enabled=True).all()
        
        if not domains:
            logger.info("No active domains found for deployment")
            return {'success': True, 'domains_deployed': 0}
        
        # Update Ansible inventory
        if not update_ansible_inventory():
            raise Exception("Failed to update Ansible inventory")
        
        deployment_results = []
        
        for domain in domains:
            try:
                # Deploy domain configuration
                task_result = deploy_domain_config.delay(domain.id)
                deployment_results.append({
                    'domain_id': domain.id,
                    'domain_name': domain.domain_name,
                    'task_id': task_result.id
                })
            except Exception as e:
                logger.error(f"Error starting deployment for domain {domain.domain_name}: {str(e)}")
                deployment_results.append({
                    'domain_id': domain.id,
                    'domain_name': domain.domain_name,
                    'error': str(e)
                })
        
        logger.info(f"Bulk domain deployment initiated for {len(domains)} domains")
        
        return {
            'success': True,
            'total_domains': len(domains),
            'deployment_results': deployment_results
        }
        
    except Exception as e:
        logger.error(f"Bulk deploy domains error: {str(e)}")
        return {'error': str(e)}