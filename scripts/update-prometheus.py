#!/usr/bin/env python3

"""
Prometheus Configuration Update Script
Auto-discovers edge nodes and updates Prometheus targets
"""

import os
import sys
import json
import yaml
import psycopg2
from datetime import datetime

def load_env():
    """Load environment variables from .env file"""
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value.strip('"\'')
    return env_vars

def get_edge_nodes():
    """Get list of active edge nodes from database"""
    env = load_env()
    
    try:
        conn = psycopg2.connect(
            host=env.get('POSTGRES_HOST', 'localhost'),
            port=env.get('POSTGRES_PORT', 5432),
            database=env.get('POSTGRES_DB', 'cachenet'),
            user=env.get('POSTGRES_USER', 'cachenet'),
            password=env.get('POSTGRES_PASSWORD', 'cachenet')
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ip_address, region, provider, status 
            FROM edge_nodes 
            WHERE status = 'active' AND is_active = true
        """)
        
        nodes = []
        for row in cursor.fetchall():
            ip_address, region, provider, status = row
            nodes.append({
                'ip': ip_address,
                'region': region,
                'provider': provider,
                'status': status
            })
        
        cursor.close()
        conn.close()
        
        return nodes
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return []

def update_prometheus_config(edge_nodes):
    """Update Prometheus configuration with edge node targets"""
    
    # Base Prometheus configuration
    config = {
        'global': {
            'scrape_interval': '15s',
            'evaluation_interval': '15s'
        },
        'rule_files': [],
        'scrape_configs': [
            {
                'job_name': 'prometheus',
                'static_configs': [
                    {'targets': ['localhost:9090']}
                ]
            },
            {
                'job_name': 'cachenet-api',
                'static_configs': [
                    {'targets': ['api:5000']}
                ],
                'metrics_path': '/metrics',
                'scrape_interval': '30s'
            },
            {
                'job_name': 'nginx-edge-nodes',
                'static_configs': [],
                'metrics_path': '/nginx_status',
                'scrape_interval': '30s'
            },
            {
                'job_name': 'node-exporter',
                'static_configs': [],
                'metrics_path': '/metrics',
                'scrape_interval': '30s'
            }
        ]
    }
    
    # Add edge node targets
    nginx_targets = []
    node_exporter_targets = []
    
    for node in edge_nodes:
        # Nginx metrics endpoint
        nginx_targets.append({
            'targets': [f"{node['ip']}:9113"],
            'labels': {
                'region': node['region'],
                'provider': node['provider'],
                'instance': node['ip']
            }
        })
        
        # Node exporter metrics
        node_exporter_targets.append({
            'targets': [f"{node['ip']}:9100"],
            'labels': {
                'region': node['region'],
                'provider': node['provider'],
                'instance': node['ip']
            }
        })
    
    # Update config
    config['scrape_configs'][2]['static_configs'] = nginx_targets
    config['scrape_configs'][3]['static_configs'] = node_exporter_targets
    
    # Write updated configuration
    config_path = 'prometheus/prometheus.yml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"Updated Prometheus configuration with {len(edge_nodes)} edge nodes")
    return config_path

def reload_prometheus():
    """Send reload signal to Prometheus"""
    import requests
    
    try:
        # Send POST request to reload Prometheus config
        response = requests.post('http://localhost:9090/-/reload', timeout=10)
        if response.status_code == 200:
            print("Prometheus configuration reloaded successfully")
        else:
            print(f"Failed to reload Prometheus: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error reloading Prometheus: {e}")

def main():
    """Main function"""
    print(f"[{datetime.now()}] Updating Prometheus configuration...")
    
    # Get edge nodes from database
    edge_nodes = get_edge_nodes()
    print(f"Found {len(edge_nodes)} active edge nodes")
    
    # Update Prometheus configuration
    config_path = update_prometheus_config(edge_nodes)
    print(f"Configuration written to {config_path}")
    
    # Reload Prometheus if running
    reload_prometheus()
    
    # Create summary
    regions = set(node['region'] for node in edge_nodes)
    providers = set(node['provider'] for node in edge_nodes)
    
    print(f"Edge nodes summary:")
    print(f"  Regions: {', '.join(sorted(regions))}")
    print(f"  Providers: {', '.join(sorted(providers))}")
    print(f"  Total nodes: {len(edge_nodes)}")

if __name__ == '__main__':
    main()