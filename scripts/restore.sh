#!/bin/bash

# 恢复脚本

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Extracting backup..."
tar -xzf $BACKUP_FILE

echo "Restoring database..."
cat db_*.sql | docker-compose exec -T postgres psql -U zpulse zpulse

echo "Cleaning up..."
rm db_*.sql

echo "Restore completed successfully"

