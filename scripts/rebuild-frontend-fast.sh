#!/bin/bash

# 快速重建前端（优先使用 Docker 缓存，不删除镜像、不 --no-cache）
# 适用场景：只是更新了前端代码，希望尽快让容器里的 Next.js 产物更新，
# 并避免每次都重新下载 apk / 编译依赖（你说的“GNU 包”）。

set -euo pipefail

echo "⚡️ 快速重建前端（使用缓存）..."

echo "📦 停止前端服务..."
docker compose stop frontend-web || true

echo "🗑️  删除旧容器（保留镜像/缓存层）..."
docker compose rm -f frontend-web || true

echo "🔨 重新构建前端（使用缓存）..."
docker compose build frontend-web

echo "🚀 启动前端服务..."
docker compose up -d frontend-web

echo "⏳ 等待服务启动..."
sleep 5

echo "✅ 检查服务状态..."
docker compose ps frontend-web

echo "📋 查看最新日志..."
docker compose logs frontend-web --tail 10

echo ""
echo "✨ 完成！"
echo "📝 如果浏览器仍是旧页面：Cmd+Shift+R 强刷，或用无痕模式。"


