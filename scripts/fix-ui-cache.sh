#!/bin/bash

# UI样式修复脚本（重型）
# 用于强制清除缓存并重新构建前端（会删除镜像并 --no-cache）
# 日常前端改动建议改用：scripts/rebuild-frontend-fast.sh

echo "🔧 开始修复UI样式问题..."

# 1. 停止前端服务
echo "📦 停止前端服务..."
docker compose stop frontend-web

# 2. 删除容器
echo "🗑️  删除旧容器..."
docker compose rm -f frontend-web

# 3. 删除镜像
echo "🗑️  删除旧镜像..."
docker rmi z-pulse-frontend-web 2>/dev/null || echo "镜像不存在，跳过"

# 4. 清理Next.js缓存
echo "🧹 清理Next.js缓存..."
cd frontend
rm -rf .next
rm -rf node_modules/.cache
cd ..

# 5. 重新构建（不使用缓存）
echo "🔨 重新构建前端（不使用缓存）..."
docker compose build --no-cache frontend-web

# 6. 启动服务
echo "🚀 启动前端服务..."
docker compose up -d frontend-web

# 7. 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 8. 检查状态
echo "✅ 检查服务状态..."
docker compose ps frontend-web

# 9. 查看日志
echo "📋 查看最新日志..."
docker compose logs frontend-web --tail 10

echo ""
echo "✨ 完成！"
echo ""
echo "📝 下一步操作："
echo "1. 清除浏览器缓存："
echo "   - Mac: Cmd + Shift + R"
echo "   - Windows: Ctrl + Shift + R"
echo "2. 或使用无痕模式访问：http://localhost:3000/admin/login"
echo "3. 如果还有问题，查看 UI_TROUBLESHOOTING.md 获取详细排查步骤"

