#!/bin/bash

# Cachenet CDN Database Backup Script
# Automated backup of PostgreSQL database with retention policy

set -e

# Configuration
BACKUP_DIR="/var/backups/cachenet"
DB_CONTAINER="cachenet-db"
DB_NAME="cachenet"
DB_USER="cachenet"
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
BACKUP_FILE="cachenet-db-$(date +%Y%m%d-%H%M%S).sql.gz"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

log "Starting database backup..."

# Check if database container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    error "Database container '$DB_CONTAINER' is not running"
    exit 1
fi

# Create database backup
log "Creating backup: $BACKUP_FILE"
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-password | gzip > "$BACKUP_PATH"

# Check if backup was successful
if [[ $? -eq 0 && -f "$BACKUP_PATH" ]]; then
    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    log "Backup completed successfully: $BACKUP_FILE ($BACKUP_SIZE)"
else
    error "Backup failed!"
    exit 1
fi

# Clean up old backups (keep only last RETENTION_DAYS days)
log "Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "cachenet-db-*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

REMAINING_BACKUPS=$(find "$BACKUP_DIR" -name "cachenet-db-*.sql.gz" -type f | wc -l)
log "Cleanup completed. $REMAINING_BACKUPS backup files remaining."

# Optional: Upload to S3 or remote storage
if [[ -n "$BACKUP_S3_BUCKET" ]]; then
    log "Uploading backup to S3..."
    if command -v aws &> /dev/null; then
        aws s3 cp "$BACKUP_PATH" "s3://$BACKUP_S3_BUCKET/backups/$(basename $BACKUP_PATH)"
        if [[ $? -eq 0 ]]; then
            log "Backup uploaded to S3 successfully"
        else
            warn "Failed to upload backup to S3"
        fi
    else
        warn "AWS CLI not installed, skipping S3 upload"
    fi
fi

# Optional: Send notification
if [[ -n "$BACKUP_WEBHOOK_URL" ]]; then
    log "Sending backup notification..."
    curl -X POST "$BACKUP_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"Cachenet database backup completed: $BACKUP_FILE ($BACKUP_SIZE)\"}" \
        2>/dev/null || warn "Failed to send notification"
fi

log "Backup process completed successfully"

# Create backup metadata
cat > "$BACKUP_DIR/latest-backup.json" << EOF
{
    "filename": "$BACKUP_FILE",
    "path": "$BACKUP_PATH",
    "size": "$BACKUP_SIZE",
    "timestamp": "$(date -Iseconds)",
    "database": "$DB_NAME",
    "retention_days": $RETENTION_DAYS
}
EOF

exit 0