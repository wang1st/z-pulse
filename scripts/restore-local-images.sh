#!/bin/bash
# ============================================
# 恢复本地开发环境镜像
# ============================================

set -e

echo "正在恢复本地开发环境..."

# 停止所有容器
docker compose down 2>/dev/null || true

# 删除损坏的服务器镜像（如果存在）
docker rmi zpulse-backend:server zpulse-frontend:server 2>/dev/null || true

# 重新构建本地镜像（使用本地平台，不指定 --platform）
echo "重新构建本地镜像..."
docker compose build

echo "启动本地服务..."
docker compose up -d

echo "✅ 本地环境已恢复！"
echo ""
echo "查看服务状态："
docker compose ps

