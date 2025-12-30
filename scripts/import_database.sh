#!/bin/bash
# 导入数据库备份脚本

if [ -z "$1" ]; then
    echo "用法: $0 <backup-file.dump>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "开始导入数据库..."
echo "⚠️  警告: 这将覆盖现有数据库！"
read -p "确认继续? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 0
fi

# 先启动数据库
docker compose up -d postgres-db
sleep 5

# 导入数据
docker compose exec -T postgres-db pg_restore -U ${POSTGRES_USER:-zpulse} -d ${POSTGRES_DB:-zpulse} -c "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 数据库导入成功"
else
    echo "❌ 数据库导入失败"
    exit 1
fi
