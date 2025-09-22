#!/bin/bash

# Database initialization and seeding script for Cachenet CDN

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] DB-INIT: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] DB-INIT WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] DB-INIT ERROR: $1${NC}"
}

log "Starting database initialization..."

# Wait for database to be ready
log "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} >/dev/null 2>&1; then
        log "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        error "PostgreSQL failed to start within 5 minutes"
        exit 1
    fi
    sleep 10
done

# Create extensions
log "Creating PostgreSQL extensions..."
docker-compose exec -T db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} <<EOF
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
EOF

# Initialize PowerDNS schema
log "Initializing PowerDNS schema..."
docker-compose exec -T db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} <<EOF
-- PowerDNS schema
CREATE TABLE IF NOT EXISTS domains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    master VARCHAR(128) DEFAULT NULL,
    last_check INT DEFAULT NULL,
    type VARCHAR(6) NOT NULL,
    notified_serial INT DEFAULT NULL,
    account VARCHAR(40) DEFAULT NULL,
    CONSTRAINT c_lowercase_name CHECK (((name)::TEXT = LOWER((name)::TEXT)))
);

CREATE UNIQUE INDEX IF NOT EXISTS name_index ON domains(name);

CREATE TABLE IF NOT EXISTS records (
    id SERIAL PRIMARY KEY,
    domain_id INT DEFAULT NULL,
    name VARCHAR(255) DEFAULT NULL,
    type VARCHAR(10) DEFAULT NULL,
    content VARCHAR(65000) DEFAULT NULL,
    ttl INT DEFAULT NULL,
    prio INT DEFAULT NULL,
    change_date INT DEFAULT NULL,
    disabled BOOLEAN DEFAULT 'f',
    ordername VARCHAR(255),
    auth BOOLEAN DEFAULT 't',
    CONSTRAINT domain_exists
        FOREIGN KEY(domain_id) REFERENCES domains(id)
        ON DELETE CASCADE,
    CONSTRAINT c_lowercase_name CHECK (((name)::TEXT = LOWER((name)::TEXT)))
);

CREATE INDEX IF NOT EXISTS rec_name_index ON records(name);
CREATE INDEX IF NOT EXISTS nametype_index ON records(name,type);
CREATE INDEX IF NOT EXISTS domain_id ON records(domain_id);
CREATE INDEX IF NOT EXISTS recordorder ON records (domain_id, ordername text_pattern_ops);

CREATE TABLE IF NOT EXISTS supermasters (
    ip INET NOT NULL,
    nameserver VARCHAR(255) NOT NULL,
    account VARCHAR(40) NOT NULL,
    PRIMARY KEY(ip, nameserver)
);

CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    domain_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(10) NOT NULL,
    modified_at INT NOT NULL,
    account VARCHAR(40) DEFAULT NULL,
    comment VARCHAR(65000) NOT NULL,
    CONSTRAINT domain_exists
        FOREIGN KEY(domain_id) REFERENCES domains(id)
        ON DELETE CASCADE,
    CONSTRAINT c_lowercase_name CHECK (((name)::TEXT = LOWER((name)::TEXT)))
);

CREATE INDEX IF NOT EXISTS comments_domain_id_idx ON comments (domain_id);
CREATE INDEX IF NOT EXISTS comments_name_type_idx ON comments (name, type);
CREATE INDEX IF NOT EXISTS comments_order_idx ON comments (domain_id, modified_at);

CREATE TABLE IF NOT EXISTS domainmetadata (
    id SERIAL PRIMARY KEY,
    domain_id INT REFERENCES domains(id) ON DELETE CASCADE,
    kind VARCHAR(32),
    content TEXT
);

CREATE INDEX IF NOT EXISTS domainmetaidindex ON domainmetadata(domain_id);

CREATE TABLE IF NOT EXISTS cryptokeys (
    id SERIAL PRIMARY KEY,
    domain_id INT REFERENCES domains(id) ON DELETE CASCADE,
    flags INT NOT NULL,
    active BOOL,
    content TEXT
);

CREATE INDEX IF NOT EXISTS domainidindex ON cryptokeys(domain_id);

CREATE TABLE IF NOT EXISTS tsigkeys (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    algorithm VARCHAR(50),
    secret VARCHAR(255),
    CONSTRAINT c_lowercase_name CHECK (((name)::TEXT = LOWER((name)::TEXT)))
);

CREATE UNIQUE INDEX IF NOT EXISTS namealgoindex ON tsigkeys(name, algorithm);
EOF

# Initialize application database schema
log "Initializing application database schema..."
docker-compose exec -T api python -c "
import os
import sys
sys.path.append('/app')
from app import create_app, db

app = create_app()
with app.app_context():
    try:
        # Create all tables
        db.create_all()
        print('Application database schema created successfully')
    except Exception as e:
        print(f'Error creating schema: {e}')
        sys.exit(1)
"

# Create admin user if specified in environment
if [ ! -z "${ADMIN_EMAIL}" ] && [ ! -z "${ADMIN_PASSWORD}" ]; then
    log "Creating admin user..."
    docker-compose exec -T api python -c "
import os
import sys
import secrets
sys.path.append('/app')
from app import create_app, db
from models import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    try:
        # Check if admin user already exists
        admin = User.query.filter_by(email='${ADMIN_EMAIL}').first()
        if admin:
            print('Admin user already exists')
        else:
            # Create admin user
            admin = User(
                email='${ADMIN_EMAIL}',
                username='admin',
                password_hash=generate_password_hash('${ADMIN_PASSWORD}'),
                first_name='${ADMIN_FIRST_NAME:-Administrator}',
                last_name='${ADMIN_LAST_NAME:-User}',
                is_admin=True,
                is_active=True,
                api_key=secrets.token_urlsafe(32)
            )
            db.session.add(admin)
            db.session.commit()
            print(f'Admin user created successfully')
            print(f'Email: ${ADMIN_EMAIL}')
            print(f'API Key: {admin.api_key}')
    except Exception as e:
        print(f'Error creating admin user: {e}')
        sys.exit(1)
"
fi

# Seed default data
log "Seeding default data..."
docker-compose exec -T api python -c "
import sys
sys.path.append('/app')
from app import create_app, db
from models import EdgeRegion, SSLProvider

app = create_app()
with app.app_context():
    try:
        # Create default edge regions
        regions = [
            {'code': 'nyc1', 'name': 'New York 1', 'country': 'US', 'provider': 'digitalocean'},
            {'code': 'sfo1', 'name': 'San Francisco 1', 'country': 'US', 'provider': 'digitalocean'},
            {'code': 'lon1', 'name': 'London 1', 'country': 'GB', 'provider': 'digitalocean'},
            {'code': 'fra1', 'name': 'Frankfurt 1', 'country': 'DE', 'provider': 'digitalocean'},
            {'code': 'sgp1', 'name': 'Singapore 1', 'country': 'SG', 'provider': 'digitalocean'},
            {'code': 'tor1', 'name': 'Toronto 1', 'country': 'CA', 'provider': 'digitalocean'},
        ]
        
        for region_data in regions:
            region = EdgeRegion.query.filter_by(code=region_data['code']).first()
            if not region:
                region = EdgeRegion(**region_data)
                db.session.add(region)
        
        # Create default SSL providers
        ssl_providers = [
            {'name': 'Let\'s Encrypt', 'type': 'acme', 'config': {'server': 'https://acme-v02.api.letsencrypt.org/directory'}},
            {'name': 'ZeroSSL', 'type': 'acme', 'config': {'server': 'https://acme.zerossl.com/v2/DV90'}},
        ]
        
        for provider_data in ssl_providers:
            provider = SSLProvider.query.filter_by(name=provider_data['name']).first()
            if not provider:
                provider = SSLProvider(**provider_data)
                db.session.add(provider)
        
        db.session.commit()
        print('Default data seeded successfully')
    except Exception as e:
        print(f'Error seeding data: {e}')
        sys.exit(1)
"

log "Database initialization completed successfully!"