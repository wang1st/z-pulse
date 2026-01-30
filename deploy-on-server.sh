#!/bin/bash

# 在阿里云服务器上执行的部署脚本
# 使用方法：在服务器上执行此脚本

set -e

echo "========================================="
echo "Z-Pulse 代码更新脚本"
echo "========================================="

cd /root/z-pulse

echo ""
echo "步骤 1: 检查当前目录结构..."
echo "-----------------------------------"
ls -la

echo ""
echo "步骤 2: 创建后端和前端目录..."
echo "-----------------------------------"
mkdir -p backend/app/routers
mkdir -p backend/app/services
mkdir -p frontend/app

echo ""
echo "步骤 3: 从本地复制更新的文件..."
echo "-----------------------------------"
echo "请在本地执行以下命令来上传文件："
echo ""
echo "scp backend/app/routers/werss.py root@47.97.115.235:/root/z-pulse/backend/app/routers/"
echo "scp backend/app/services/werss_monitor.py root@47.97.115.235:/root/z-pulse/backend/app/services/"
echo "scp -r shared/* root@47.97.115.235:/root/z-pulse/shared/"
echo "scp -r frontend/app/we-rss-qrcode-direct root@47.97.115.235:/root/z-pulse/frontend/app/"
echo ""
read -p "文件上传完成后按回车继续..."

echo ""
echo "步骤 4: 检查docker-compose配置..."
echo "-----------------------------------"
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml 不存在"
    echo "请先上传 docker-compose.yml 文件"
    exit 1
fi

echo ""
echo "步骤 5: 停止现有容器..."
echo "-----------------------------------"
docker-compose down

echo ""
echo "步骤 6: 重新构建前端镜像..."
echo "-----------------------------------"
if [ -d "frontend" ]; then
    cd frontend
    docker build -t zpulse-frontend:latest .
    cd ..
else
    echo "⚠️  frontend目录不存在，跳过前端构建"
fi

echo ""
echo "步骤 7: 重新构建后端镜像..."
echo "-----------------------------------"
if [ -d "backend" ]; then
    cd backend
    docker build -t z-pulse-api-backend:latest -f Dockerfile ../
    cd ..
else
    echo "⚠️  backend目录不存在，跳过后端构建"
fi

echo ""
echo "步骤 8: 启动所有服务..."
echo "-----------------------------------"
docker-compose up -d

echo ""
echo "步骤 9: 等待服务启动..."
echo "-----------------------------------"
sleep 15

echo ""
echo "步骤 10: 检查服务状态..."
echo "-----------------------------------"
docker-compose ps

echo ""
echo "步骤 11: 测试API..."
echo "-----------------------------------"
echo "测试二维码API:"
curl -s http://localhost:8000/api/werss/qrcode | jq . || echo "API测试失败"

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo "主应用: http://47.97.115.235:8899"
echo "二维码页面: http://47.97.115.235:8899/we-rss-qrcode-direct"
echo "========================================="

echo ""
echo "查看日志："
echo "  docker-compose logs -f --tail=50"
echo ""
echo "重启特定服务："
echo "  docker-compose restart frontend-web"
echo "  docker-compose restart api-backend"
