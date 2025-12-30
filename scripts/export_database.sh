#!/bin/bash
# 导出数据库备份脚本

BACKUP_FILE="z-pulse-backup-$(date +%Y%m%d_%H%M%S).dump"

echo "开始导出数据库..."
docker compose exec -T postgres-db pg_dump -U ${POSTGRES_USER:-zpulse} -Fc ${POSTGRES_DB:-zpulse} > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 数据库导出成功: $BACKUP_FILE"
    echo "文件大小: $(du -h $BACKUP_FILE | cut -f1)"
else
    echo "❌ 数据库导出失败"
    exit 1
fi
