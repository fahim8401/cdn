#!/usr/bin/env python3
"""
Cachenet CDN Platform Auto-scaling Tasks
Automatic edge node provisioning and scaling
"""

import os
import logging
import requests
import time
from datetime import datetime, timedelta
from celery import shared_task
from models import db, EdgeNode, Domain
from tasks.edge_config import deploy_edge_node
from tasks.dns_provision import add_edge_node_to_dns, remove_edge_node_from_dns

logger = logging.getLogger(__name__)

# Cloud provider API configurations
DIGITALOCEAN_API_TOKEN = os.getenv('DIGITALOCEAN_API_TOKEN')
LINODE_API_TOKEN = os.getenv('LINODE_API_TOKEN')
VULTR_API_KEY = os.getenv('VULTR_API_KEY')
HETZNER_API_TOKEN = os.getenv('HETZNER_API_TOKEN')

# Auto-scaling configuration
AUTO_SCALE_ENABLED = os.getenv('AUTO_SCALE_ENABLED', 'true').lower() == 'true'
MAX_CLIENTS_PER_NODE = int(os.getenv('EDGE_MAX_CLIENTS_PER_NODE', 25))
MIN_NODES = int(os.getenv('AUTO_SCALE_MIN_NODES', 2))
MAX_NODES = int(os.getenv('AUTO_SCALE_MAX_NODES', 50))

def create_digitalocean_droplet(region, name):
    """Create DigitalOcean droplet"""
    try:
        if not DIGITALOCEAN_API_TOKEN:
            raise Exception("DigitalOcean API token not configured")
        
        headers = {
            'Authorization': f'Bearer {DIGITALOCEAN_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Droplet configuration
        droplet_data = {
            'name': name,
            'region': region,
            'size': 's-1vcpu-1gb',  # $5/month basic droplet
            'image': 'ubuntu-22-04-x64',
            'ssh_keys': [],  # Will be populated with SSH key fingerprints
            'backups': False,
            'ipv6': True,
            'user_data': '''#!/bin/bash
                # Basic server setup
                apt-get update
                apt-get install -y nginx python3 python3-pip
                
                # Install monitoring agent
                curl -sSL https://repos.insights.digitalocean.com/install.sh | sudo bash
                
                # Basic security
                ufw allow ssh
                ufw allow http
                ufw allow https
                ufw --force enable
                
                # Create cachenet user
                useradd -m -s /bin/bash cachenet
                mkdir -p /home/cachenet/.ssh
                chmod 700 /home/cachenet/.ssh
                
                # Reboot to apply all changes
                reboot
            ''',
            'tags': ['cachenet', 'edge-node', 'auto-scaled']
        }
        
        # Create droplet
        response = requests.post(
            'https://api.digitalocean.com/v2/droplets',
            json=droplet_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 202:
            droplet = response.json()['droplet']
            return {
                'success': True,
                'instance_id': str(droplet['id']),
                'name': droplet['name'],
                'region': droplet['region']['slug'],
                'status': droplet['status']
            }
        else:
            logger.error(f"DigitalOcean droplet creation failed: {response.text}")
            return {
                'success': False,
                'error': f"API error: {response.status_code}"
            }
        
    except Exception as e:
        logger.error(f"DigitalOcean droplet creation error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def create_linode_instance(region, name):
    """Create Linode instance"""
    try:
        if not LINODE_API_TOKEN:
            raise Exception("Linode API token not configured")
        
        headers = {
            'Authorization': f'Bearer {LINODE_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Instance configuration
        instance_data = {
            'label': name,
            'region': region,
            'type': 'g6-nanode-1',  # $5/month basic instance
            'image': 'linode/ubuntu22.04',
            'root_pass': 'TempPassword123!',  # Will be changed by Ansible
            'authorized_keys': [],
            'backups_enabled': False,
            'tags': ['cachenet', 'edge-node', 'auto-scaled']
        }
        
        # Create instance
        response = requests.post(
            'https://api.linode.com/v4/linode/instances',
            json=instance_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            instance = response.json()
            return {
                'success': True,
                'instance_id': str(instance['id']),
                'name': instance['label'],
                'region': instance['region'],
                'status': instance['status']
            }
        else:
            logger.error(f"Linode instance creation failed: {response.text}")
            return {
                'success': False,
                'error': f"API error: {response.status_code}"
            }
        
    except Exception as e:
        logger.error(f"Linode instance creation error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def create_vultr_instance(region, name):
    """Create Vultr instance"""
    try:
        if not VULTR_API_KEY:
            raise Exception("Vultr API key not configured")
        
        headers = {
            'Authorization': f'Bearer {VULTR_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Instance configuration
        instance_data = {
            'label': name,
            'region': region,
            'plan': 'vc2-1c-1gb',  # $5/month basic instance
            'os_id': 1743,  # Ubuntu 22.04 LTS
            'enable_ipv6': True,
            'tags': ['cachenet', 'edge-node', 'auto-scaled']
        }
        
        # Create instance
        response = requests.post(
            'https://api.vultr.com/v2/instances',
            json=instance_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 202:
            instance = response.json()['instance']
            return {
                'success': True,
                'instance_id': instance['id'],
                'name': instance['label'],
                'region': instance['region'],
                'status': instance['power_status']
            }
        else:
            logger.error(f"Vultr instance creation failed: {response.text}")
            return {
                'success': False,
                'error': f"API error: {response.status_code}"
            }
        
    except Exception as e:
        logger.error(f"Vultr instance creation error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def create_hetzner_server(region, name):
    """Create Hetzner Cloud server"""
    try:
        if not HETZNER_API_TOKEN:
            raise Exception("Hetzner API token not configured")
        
        headers = {
            'Authorization': f'Bearer {HETZNER_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Server configuration
        server_data = {
            'name': name,
            'server_type': 'cx11',  # ~$3/month basic server
            'location': region,
            'image': 'ubuntu-22.04',
            'ssh_keys': [],
            'user_data': '''#!/bin/bash
                apt-get update
                apt-get install -y nginx python3 python3-pip
                ufw allow ssh
                ufw allow http
                ufw allow https
                ufw --force enable
            ''',
            'labels': {
                'project': 'cachenet',
                'type': 'edge-node',
                'auto-scaled': 'true'
            }
        }
        
        # Create server
        response = requests.post(
            'https://api.hetzner.cloud/v1/servers',
            json=server_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 201:
            server = response.json()['server']
            return {
                'success': True,
                'instance_id': str(server['id']),
                'name': server['name'],
                'region': server['datacenter']['location']['name'],
                'status': server['status']
            }
        else:
            logger.error(f"Hetzner server creation failed: {response.text}")
            return {
                'success': False,
                'error': f"API error: {response.status_code}"
            }
        
    except Exception as e:
        logger.error(f"Hetzner server creation error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_instance_ip(provider, instance_id):
    """Get instance IP address from cloud provider"""
    try:
        if provider == 'digitalocean':
            headers = {'Authorization': f'Bearer {DIGITALOCEAN_API_TOKEN}'}
            response = requests.get(
                f'https://api.digitalocean.com/v2/droplets/{instance_id}',
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                droplet = response.json()['droplet']
                networks = droplet.get('networks', {})
                v4_networks = networks.get('v4', [])
                for network in v4_networks:
                    if network['type'] == 'public':
                        return network['ip_address']
        
        elif provider == 'linode':
            headers = {'Authorization': f'Bearer {LINODE_API_TOKEN}'}
            response = requests.get(
                f'https://api.linode.com/v4/linode/instances/{instance_id}/ips',
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                ips = response.json()
                ipv4_public = ips.get('ipv4', {}).get('public', [])
                if ipv4_public:
                    return ipv4_public[0]
        
        elif provider == 'vultr':
            headers = {'Authorization': f'Bearer {VULTR_API_KEY}'}
            response = requests.get(
                f'https://api.vultr.com/v2/instances/{instance_id}',
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                instance = response.json()['instance']
                return instance.get('main_ip')
        
        elif provider == 'hetzner':
            headers = {'Authorization': f'Bearer {HETZNER_API_TOKEN}'}
            response = requests.get(
                f'https://api.hetzner.cloud/v1/servers/{instance_id}',
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                server = response.json()['server']
                public_net = server.get('public_net', {})
                ipv4 = public_net.get('ipv4', {})
                return ipv4.get('ip')
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting instance IP for {provider} instance {instance_id}: {str(e)}")
        return None

@shared_task(bind=True, max_retries=3)
def scale_up_edge_nodes(self, region, provider='digitalocean'):
    """Scale up edge nodes in specified region"""
    try:
        logger.info(f"Scaling up edge nodes in region: {region}, provider: {provider}")
        
        if not AUTO_SCALE_ENABLED:
            logger.info("Auto-scaling is disabled")
            return {'error': 'Auto-scaling is disabled'}
        
        # Check if we've reached the maximum number of nodes
        current_node_count = EdgeNode.query.filter_by(status='active').count()
        if current_node_count >= MAX_NODES:
            logger.warning(f"Maximum node limit reached: {current_node_count}/{MAX_NODES}")
            return {'error': f'Maximum node limit reached: {MAX_NODES}'}
        
        # Generate unique name for the new edge node
        timestamp = int(time.time())
        node_name = f"edge-{region}-{timestamp}"
        hostname = f"{node_name}.cachenet.local"
        
        # Create instance based on provider
        if provider == 'digitalocean':
            result = create_digitalocean_droplet(region, node_name)
        elif provider == 'linode':
            result = create_linode_instance(region, node_name)
        elif provider == 'vultr':
            result = create_vultr_instance(region, node_name)
        elif provider == 'hetzner':
            result = create_hetzner_server(region, node_name)
        else:
            raise Exception(f"Unsupported provider: {provider}")
        
        if not result['success']:
            raise Exception(f"Failed to create instance: {result['error']}")
        
        instance_id = result['instance_id']
        
        # Wait for instance to be ready and get IP address
        logger.info(f"Waiting for instance {instance_id} to be ready...")
        
        max_attempts = 30  # 5 minutes
        ip_address = None
        
        for attempt in range(max_attempts):
            time.sleep(10)  # Wait 10 seconds between checks
            ip_address = get_instance_ip(provider, instance_id)
            if ip_address:
                break
            logger.info(f"Attempt {attempt + 1}/{max_attempts}: Waiting for IP address...")
        
        if not ip_address:
            raise Exception("Failed to get instance IP address")
        
        # Create edge node record in database
        edge_node = EdgeNode(
            name=node_name,
            hostname=hostname,
            ip_address=ip_address,
            region=region,
            provider=provider,
            instance_id=instance_id,
            max_clients=MAX_CLIENTS_PER_NODE,
            status='pending'
        )
        
        db.session.add(edge_node)
        db.session.commit()
        
        # Trigger edge node deployment
        deploy_task = deploy_edge_node.delay(edge_node.id)
        
        logger.info(f"Edge node scale-up completed: {hostname} ({ip_address})")
        
        return {
            'success': True,
            'edge_node_id': edge_node.id,
            'hostname': hostname,
            'ip_address': ip_address,
            'region': region,
            'provider': provider,
            'instance_id': instance_id,
            'deployment_task_id': deploy_task.id
        }
        
    except Exception as e:
        logger.error(f"Scale up error in region {region}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying scale up in region {region}")
            raise self.retry(countdown=120 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def scale_down_edge_nodes(self, region=None):
    """Scale down edge nodes (remove least utilized nodes)"""
    try:
        logger.info(f"Scaling down edge nodes in region: {region or 'all'}")
        
        if not AUTO_SCALE_ENABLED:
            logger.info("Auto-scaling is disabled")
            return {'error': 'Auto-scaling is disabled'}
        
        # Get active edge nodes
        if region:
            edge_nodes = EdgeNode.query.filter_by(region=region, status='active').all()
        else:
            edge_nodes = EdgeNode.query.filter_by(status='active').all()
        
        # Check minimum node count
        if len(edge_nodes) <= MIN_NODES:
            logger.warning(f"Minimum node count reached: {len(edge_nodes)}/{MIN_NODES}")
            return {'error': f'Minimum node count reached: {MIN_NODES}'}
        
        # Find least utilized node (lowest client count and load score)
        least_utilized = min(
            edge_nodes,
            key=lambda node: (node.client_count or 0, node.load_score or 0)
        )
        
        # Only scale down if the node has very low utilization
        if (least_utilized.client_count or 0) > 5 or (least_utilized.load_score or 0) > 0.2:
            logger.info("No nodes suitable for scale down (all nodes have significant load)")
            return {'error': 'No nodes suitable for scale down'}
        
        # Remove node from DNS first
        remove_edge_node_from_dns.delay(least_utilized.id)
        
        # Wait a bit for DNS propagation
        time.sleep(30)
        
        # Destroy cloud instance
        try:
            if least_utilized.provider == 'digitalocean' and DIGITALOCEAN_API_TOKEN:
                headers = {'Authorization': f'Bearer {DIGITALOCEAN_API_TOKEN}'}
                requests.delete(
                    f'https://api.digitalocean.com/v2/droplets/{least_utilized.instance_id}',
                    headers=headers,
                    timeout=30
                )
            elif least_utilized.provider == 'linode' and LINODE_API_TOKEN:
                headers = {'Authorization': f'Bearer {LINODE_API_TOKEN}'}
                requests.delete(
                    f'https://api.linode.com/v4/linode/instances/{least_utilized.instance_id}',
                    headers=headers,
                    timeout=30
                )
            elif least_utilized.provider == 'vultr' and VULTR_API_KEY:
                headers = {'Authorization': f'Bearer {VULTR_API_KEY}'}
                requests.delete(
                    f'https://api.vultr.com/v2/instances/{least_utilized.instance_id}',
                    headers=headers,
                    timeout=30
                )
            elif least_utilized.provider == 'hetzner' and HETZNER_API_TOKEN:
                headers = {'Authorization': f'Bearer {HETZNER_API_TOKEN}'}
                requests.delete(
                    f'https://api.hetzner.cloud/v1/servers/{least_utilized.instance_id}',
                    headers=headers,
                    timeout=30
                )
        except Exception as e:
            logger.error(f"Error destroying cloud instance: {str(e)}")
        
        # Remove edge node from database
        node_info = {
            'hostname': least_utilized.hostname,
            'ip_address': least_utilized.ip_address,
            'region': least_utilized.region,
            'provider': least_utilized.provider
        }
        
        db.session.delete(least_utilized)
        db.session.commit()
        
        logger.info(f"Edge node scaled down: {node_info['hostname']}")
        
        return {
            'success': True,
            'removed_node': node_info
        }
        
    except Exception as e:
        logger.error(f"Scale down error: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info("Retrying scale down")
            raise self.retry(countdown=120 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task
def auto_scale_check():
    """Periodic check for auto-scaling requirements"""
    try:
        logger.info("Running auto-scaling check")
        
        if not AUTO_SCALE_ENABLED:
            return {'message': 'Auto-scaling is disabled'}
        
        # Get edge node statistics
        edge_nodes = EdgeNode.query.filter_by(status='active').all()
        
        if not edge_nodes:
            logger.warning("No active edge nodes found")
            return {'error': 'No active edge nodes found'}
        
        # Calculate regional load
        regional_load = {}
        
        for node in edge_nodes:
            region = node.region
            if region not in regional_load:
                regional_load[region] = {
                    'nodes': 0,
                    'total_clients': 0,
                    'avg_load': 0.0,
                    'overloaded_nodes': 0
                }
            
            regional_load[region]['nodes'] += 1
            regional_load[region]['total_clients'] += node.client_count or 0
            regional_load[region]['avg_load'] += node.load_score or 0.0
            
            # Check if node is overloaded
            if (node.client_count or 0) >= MAX_CLIENTS_PER_NODE * 0.8:  # 80% threshold
                regional_load[region]['overloaded_nodes'] += 1
        
        # Calculate averages
        for region in regional_load:
            if regional_load[region]['nodes'] > 0:
                regional_load[region]['avg_load'] /= regional_load[region]['nodes']
        
        scaling_actions = []
        
        # Check for scale-up requirements
        for region, load_data in regional_load.items():
            # Scale up if more than 50% of nodes are overloaded
            if load_data['overloaded_nodes'] > load_data['nodes'] * 0.5:
                logger.info(f"Scale-up required in region {region}: {load_data['overloaded_nodes']}/{load_data['nodes']} nodes overloaded")
                
                # Choose provider (simple round-robin)
                providers = ['digitalocean', 'linode', 'vultr', 'hetzner']
                provider = providers[len(edge_nodes) % len(providers)]
                
                task = scale_up_edge_nodes.delay(region, provider)
                scaling_actions.append({
                    'action': 'scale_up',
                    'region': region,
                    'provider': provider,
                    'task_id': task.id
                })
        
        # Check for scale-down requirements (if no scale-up is happening)
        if not scaling_actions:
            for region, load_data in regional_load.items():
                # Scale down if average load is very low and we have more than minimum nodes
                if (load_data['avg_load'] < 0.1 and 
                    load_data['nodes'] > MIN_NODES and 
                    load_data['total_clients'] < load_data['nodes'] * MAX_CLIENTS_PER_NODE * 0.2):
                    
                    logger.info(f"Scale-down considered in region {region}: low utilization")
                    
                    task = scale_down_edge_nodes.delay(region)
                    scaling_actions.append({
                        'action': 'scale_down',
                        'region': region,
                        'task_id': task.id
                    })
                    break  # Only scale down one region at a time
        
        logger.info(f"Auto-scaling check completed: {len(scaling_actions)} actions triggered")
        
        return {
            'success': True,
            'regional_load': regional_load,
            'scaling_actions': scaling_actions
        }
        
    except Exception as e:
        logger.error(f"Auto-scaling check error: {str(e)}")
        return {'error': str(e)}

@shared_task
def cleanup_failed_instances():
    """Clean up failed or stuck edge node instances"""
    try:
        logger.info("Cleaning up failed edge node instances")
        
        # Find nodes that have been in 'pending' status for more than 30 minutes
        threshold = datetime.utcnow() - timedelta(minutes=30)
        failed_nodes = EdgeNode.query.filter(
            EdgeNode.status == 'pending',
            EdgeNode.created_at <= threshold
        ).all()
        
        cleanup_count = 0
        
        for node in failed_nodes:
            try:
                logger.info(f"Cleaning up failed node: {node.hostname}")
                
                # Try to destroy cloud instance
                if node.instance_id:
                    try:
                        if node.provider == 'digitalocean' and DIGITALOCEAN_API_TOKEN:
                            headers = {'Authorization': f'Bearer {DIGITALOCEAN_API_TOKEN}'}
                            requests.delete(
                                f'https://api.digitalocean.com/v2/droplets/{node.instance_id}',
                                headers=headers,
                                timeout=30
                            )
                        # Add similar cleanup for other providers...
                    except Exception as e:
                        logger.error(f"Error destroying failed instance {node.instance_id}: {str(e)}")
                
                # Remove from database
                db.session.delete(node)
                cleanup_count += 1
                
            except Exception as e:
                logger.error(f"Error cleaning up failed node {node.id}: {str(e)}")
        
        db.session.commit()
        
        logger.info(f"Failed instance cleanup completed: {cleanup_count} instances cleaned up")
        
        return {
            'success': True,
            'instances_cleaned': cleanup_count
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed instances error: {str(e)}")
        return {'error': str(e)}