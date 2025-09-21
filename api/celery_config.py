#!/usr/bin/env python3
"""
Cachenet CDN Platform Celery Configuration
Background task processing with Redis broker
"""

import os
from celery import Celery
from datetime import timedelta

# Create Celery instance
celery = Celery('cachenet')

# Configuration
celery.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/2'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    worker_prefetch_multiplier=1,
    broker_transport_options={'visibility_timeout': 3600},
    result_expires=3600,
    task_routes={
        'tasks.dns_provision.*': {'queue': 'dns'},
        'tasks.ssl_issue.*': {'queue': 'ssl'},
        'tasks.purge_cache.*': {'queue': 'cache'},
        'tasks.auto_scale.*': {'queue': 'scaling'},
        'tasks.edge_config.*': {'queue': 'config'},
    },
    beat_schedule={
        'check-ssl-expiry': {
            'task': 'tasks.ssl_issue.check_expiring_certificates',
            'schedule': timedelta(hours=6),
        },
        'auto-scale-check': {
            'task': 'tasks.auto_scale.auto_scale_check',
            'schedule': timedelta(minutes=int(os.getenv('AUTO_SCALE_CHECK_INTERVAL', 300))),
        },
        'update-edge-stats': {
            'task': 'tasks.edge_config.update_edge_statistics',
            'schedule': timedelta(minutes=5),
        },
        'cleanup-expired-tasks': {
            'task': 'tasks.cleanup.cleanup_expired_tasks',
            'schedule': timedelta(hours=24),
        },
    },
)

# Auto-discover tasks
celery.autodiscover_tasks([
    'tasks.dns_provision',
    'tasks.ssl_issue', 
    'tasks.purge_cache',
    'tasks.auto_scale',
    'tasks.edge_config',
])

if __name__ == '__main__':
    celery.start()