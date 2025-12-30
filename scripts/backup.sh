#!/bin/bash

# 备份脚本

set -e

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz"

echo "Creating backup directory..."
mkdir -p $BACKUP_DIR

echo "Backing up database..."
docker-compose exec -T postgres pg_dump -U zpulse zpulse > ${BACKUP_DIR}/db_${TIMESTAMP}.sql

echo "Backing up data..."
tar -czf $BACKUP_FILE \
    data/ \
    ${BACKUP_DIR}/db_${TIMESTAMP}.sql

echo "Cleaning up..."
rm ${BACKUP_DIR}/db_${TIMESTAMP}.sql

echo "Backup completed: $BACKUP_FILE"

