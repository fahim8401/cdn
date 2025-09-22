#!/usr/bin/env python3
"""
Cachenet CDN Auto-Provisioning Script
Automatically provisions new edge servers based on load and demand
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CloudProvider:
    """Base class for cloud provider implementations"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def create_instance(self, region: str, size: str = '2gb') -> Dict:
        """Create a new instance"""
        raise NotImplementedError
    
    def delete_instance(self, instance_id: str) -> bool:
        """Delete an instance"""
        raise NotImplementedError
    
    def list_instances(self) -> List[Dict]:
        """List all instances"""
        raise NotImplementedError

class DigitalOceanProvider(CloudProvider):
    """DigitalOcean cloud provider implementation"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.digitalocean.com/v2"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def create_instance(self, region: str, size: str = 's-2vcpu-2gb') -> Dict:
        """Create a new DigitalOcean droplet"""
        
        # Read SSH public key
        ssh_key_path = "ansible/keys/cachenet-ed25519.pub"
        if not os.path.exists(ssh_key_path):
            raise Exception(f"SSH public key not found: {ssh_key_path}")
        
        with open(ssh_key_path, 'r') as f:
            ssh_public_key = f.read().strip()
        
        # Upload SSH key if not exists
        ssh_key_id = self._get_or_create_ssh_key(ssh_public_key)
        
        # Create droplet
        data = {
            "name": f"cachenet-edge-{region}-{int(time.time())}",
            "region": region,
            "size": size,
            "image": "ubuntu-22-04-x64",
            "ssh_keys": [ssh_key_id],
            "user_data": self._get_user_data(),
            "tags": ["cachenet", "edge-server", "auto-provisioned"],
            "monitoring": True,
            "ipv6": True
        }
        
        response = requests.post(
            f"{self.base_url}/droplets",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        
        droplet_data = response.json()['droplet']
        logger.info(f"Created DigitalOcean droplet: {droplet_data['id']}")
        
        return {
            'provider': 'digitalocean',
            'instance_id': str(droplet_data['id']),
            'name': droplet_data['name'],
            'region': region,
            'size': size,
            'status': droplet_data['status'],
            'ip_address': None,  # Will be assigned when active
            'created_at': droplet_data['created_at']
        }
    
    def _get_or_create_ssh_key(self, public_key: str) -> int:
        """Get existing SSH key or create new one"""
        
        # List existing SSH keys
        response = requests.get(f"{self.base_url}/account/keys", headers=self.headers)
        response.raise_for_status()
        
        # Check if key already exists
        for key in response.json()['ssh_keys']:
            if key['public_key'].strip() == public_key.strip():
                return key['id']
        
        # Create new SSH key
        data = {
            "name": f"cachenet-{int(time.time())}",
            "public_key": public_key
        }
        
        response = requests.post(
            f"{self.base_url}/account/keys",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        
        key_id = response.json()['ssh_key']['id']
        logger.info(f"Created SSH key: {key_id}")
        
        return key_id
    
    def _get_user_data(self) -> str:
        """Get cloud-init user data for edge server setup"""
        return """#!/bin/bash
# Cachenet Edge Server Bootstrap

# Update system
apt-get update && apt-get upgrade -y

# Install required packages
apt-get install -y nginx docker.io docker-compose curl wget htop ufw fail2ban

# Configure firewall
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 9100/tcp  # Node exporter

# Configure fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# Add cachenet user
useradd -m -s /bin/bash cachenet
usermod -aG docker cachenet

# Create systemd service for edge node
cat > /etc/systemd/system/cachenet-edge.service << 'EOF'
[Unit]
Description=Cachenet Edge Node
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=cachenet
WorkingDirectory=/home/cachenet
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cachenet-edge

# Signal that bootstrap is complete
touch /var/log/cachenet-bootstrap-complete
"""
    
    def get_instance_info(self, instance_id: str) -> Optional[Dict]:
        """Get instance information"""
        response = requests.get(
            f"{self.base_url}/droplets/{instance_id}",
            headers=self.headers
        )
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        droplet = response.json()['droplet']
        
        # Get public IP
        public_ip = None
        for network in droplet['networks']['v4']:
            if network['type'] == 'public':
                public_ip = network['ip_address']
                break
        
        return {
            'provider': 'digitalocean',
            'instance_id': str(droplet['id']),
            'name': droplet['name'],
            'region': droplet['region']['slug'],
            'size': droplet['size_slug'],
            'status': droplet['status'],
            'ip_address': public_ip,
            'created_at': droplet['created_at']
        }

class AutoProvisioner:
    """Main auto-provisioning class"""
    
    def __init__(self):
        self.api_url = os.getenv('API_URL', 'http://localhost:5000')
        self.api_token = os.getenv('API_TOKEN')
        
        if not self.api_token:
            raise Exception("API_TOKEN environment variable required")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        # Initialize cloud providers
        self.providers = {}
        
        # DigitalOcean
        do_token = os.getenv('DIGITALOCEAN_API_TOKEN')
        if do_token:
            self.providers['digitalocean'] = DigitalOceanProvider(do_token)
        
        # Add other providers here (Linode, Vultr, Hetzner)
        
        if not self.providers:
            logger.warning("No cloud providers configured")
    
    def check_scaling_needs(self) -> List[Dict]:
        """Check if scaling is needed based on current load"""
        
        # Get current edge node statistics
        response = requests.get(
            f"{self.api_url}/api/auto-scale/edge-nodes",
            headers=self.headers
        )
        response.raise_for_status()
        
        edge_nodes = response.json()['edge_nodes']
        scaling_actions = []
        
        # Group nodes by region
        regions = {}
        for node in edge_nodes:
            region = node['region']
            if region not in regions:
                regions[region] = []
            regions[region].append(node)
        
        # Check each region
        for region, nodes in regions.items():
            active_nodes = [n for n in nodes if n['status'] == 'active']
            
            if not active_nodes:
                # No active nodes in region - need at least one
                scaling_actions.append({
                    'action': 'scale_up',
                    'region': region,
                    'reason': 'no_active_nodes',
                    'target_count': 1
                })
                continue
            
            # Calculate average load
            total_load = sum(node['load_score'] for node in active_nodes)
            avg_load = total_load / len(active_nodes)
            
            # Calculate average client count
            total_clients = sum(node['client_count'] for node in active_nodes)
            avg_clients = total_clients / len(active_nodes)
            max_clients_per_node = int(os.getenv('EDGE_MAX_CLIENTS_PER_NODE', '25'))
            
            # Scale up conditions
            if avg_load > 0.8 or avg_clients > max_clients_per_node * 0.8:
                scaling_actions.append({
                    'action': 'scale_up',
                    'region': region,
                    'reason': f'high_load_{avg_load:.2f}_or_clients_{avg_clients:.0f}',
                    'target_count': len(active_nodes) + 1
                })
            
            # Scale down conditions (only if we have more than 2 nodes)
            elif len(active_nodes) > 2 and avg_load < 0.3 and avg_clients < max_clients_per_node * 0.3:
                scaling_actions.append({
                    'action': 'scale_down',
                    'region': region,
                    'reason': f'low_load_{avg_load:.2f}_and_clients_{avg_clients:.0f}',
                    'target_count': len(active_nodes) - 1
                })
        
        return scaling_actions
    
    def provision_edge_node(self, region: str, provider: str = 'digitalocean') -> Dict:
        """Provision a new edge node"""
        
        if provider not in self.providers:
            raise Exception(f"Provider {provider} not configured")
        
        logger.info(f"Provisioning new edge node in {region} using {provider}")
        
        # Create instance
        instance_info = self.providers[provider].create_instance(region)
        
        # Wait for instance to be active
        instance_id = instance_info['instance_id']
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            current_info = self.providers[provider].get_instance_info(instance_id)
            
            if current_info and current_info['status'] == 'active' and current_info['ip_address']:
                instance_info = current_info
                break
            
            logger.info(f"Waiting for instance {instance_id} to become active...")
            time.sleep(30)
        else:
            raise Exception(f"Instance {instance_id} did not become active within {max_wait_time} seconds")
        
        # Register edge node in Cachenet API
        edge_data = {
            'name': instance_info['name'],
            'hostname': instance_info['name'],
            'ip_address': instance_info['ip_address'],
            'region': region,
            'provider': provider,
            'instance_id': instance_id,
            'status': 'pending'
        }
        
        response = requests.post(
            f"{self.api_url}/api/auto-scale/edge-nodes",
            headers=self.headers,
            json=edge_data
        )
        response.raise_for_status()
        
        edge_node = response.json()['edge_node']
        logger.info(f"Edge node registered: {edge_node['id']}")
        
        # Deploy edge node configuration via Ansible
        self.deploy_edge_configuration(edge_node['id'])
        
        return edge_node
    
    def deploy_edge_configuration(self, edge_node_id: int):
        """Deploy configuration to edge node"""
        
        # Trigger deployment via API
        response = requests.post(
            f"{self.api_url}/api/auto-scale/deploy",
            headers=self.headers,
            json={'node_id': edge_node_id}
        )
        response.raise_for_status()
        
        logger.info(f"Configuration deployment triggered for edge node {edge_node_id}")
    
    def run_auto_scaling(self):
        """Run auto-scaling check and actions"""
        
        if not os.getenv('AUTO_SCALE_ENABLED', 'false').lower() == 'true':
            logger.info("Auto-scaling is disabled")
            return
        
        logger.info("Running auto-scaling check...")
        
        try:
            scaling_actions = self.check_scaling_needs()
            
            if not scaling_actions:
                logger.info("No scaling actions needed")
                return
            
            for action in scaling_actions:
                if action['action'] == 'scale_up':
                    logger.info(f"Scaling up in region {action['region']}: {action['reason']}")
                    self.provision_edge_node(action['region'])
                elif action['action'] == 'scale_down':
                    logger.info(f"Scale down needed in region {action['region']}: {action['reason']}")
                    # Note: Scale down is more complex and should be done carefully
                    # For now, just log the requirement
        
        except Exception as e:
            logger.error(f"Auto-scaling error: {str(e)}")

def main():
    """Main function"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        provisioner = AutoProvisioner()
        
        if command == "check":
            actions = provisioner.check_scaling_needs()
            print(json.dumps(actions, indent=2))
        
        elif command == "provision":
            if len(sys.argv) < 3:
                print("Usage: auto-provision.py provision <region>")
                sys.exit(1)
            
            region = sys.argv[2]
            edge_node = provisioner.provision_edge_node(region)
            print(json.dumps(edge_node, indent=2))
        
        elif command == "run":
            provisioner.run_auto_scaling()
        
        else:
            print("Usage: auto-provision.py {check|provision <region>|run}")
            sys.exit(1)
    
    else:
        print("Usage: auto-provision.py {check|provision <region>|run}")
        sys.exit(1)

if __name__ == "__main__":
    main()