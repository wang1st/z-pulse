#!/bin/bash

# 自动化部署脚本 - 从本地直接部署到阿里云
# 使用sshpass自动输入密码

set -e

SERVER="root@47.97.115.235"
PASSWORD="Wang@703711!"
DEPLOY_DIR="/root/z-pulse"

echo "========================================="
echo "Z-Pulse 自动部署到阿里云"
echo "========================================="

# 检查sshpass是否安装
if ! command -v sshpass &> /dev/null; then
    echo "❌ sshpass未安装"
    echo "请安装: brew install sshpass"
    echo "或者使用手动部署方式"
    exit 1
fi

echo ""
echo "步骤 1: 在服务器上创建目录结构..."
echo "-----------------------------------"
sshpass -p "$PASSWORD" ssh $SERVER << 'ENDSSH'
cd /root/z-pulse
mkdir -p backend/app/routers backend/app/services shared frontend/app
ENDSSH

echo "✓ 目录结构已创建"

echo ""
echo "步骤 2: 上传后端代码..."
echo "-----------------------------------"
sshpass -p "$PASSWORD" scp backend/app/routers/werss.py $SERVER:$DEPLOY_DIR/backend/app/routers/
echo "✓ werss.py 已上传"

sshpass -p "$PASSWORD" scp backend/app/services/werss_monitor.py $SERVER:$DEPLOY_DIR/backend/app/services/
echo "✓ werss_monitor.py 已上传"

echo ""
echo "步骤 3: 上传shared模块..."
echo "-----------------------------------"
sshpass -p "$PASSWORD" scp -r shared/database $SERVER:$DEPLOY_DIR/shared/
echo "✓ shared/database 已上传"

sshpass -p "$PASSWORD" scp shared/config.py $SERVER:$DEPLOY_DIR/shared/ 2>/dev/null || true
echo "✓ shared/config.py 已上传"

echo ""
echo "步骤 4: 上传前端代码..."
echo "-----------------------------------"
sshpass -p "$PASSWORD" scp -r frontend/app/we-rss-qrcode-direct $SERVER:$DEPLOY_DIR/frontend/app/
echo "✓ we-rss-qrcode-direct 页面已上传"

echo ""
echo "步骤 5: 上传Dockerfile..."
echo "-----------------------------------"
sshpass -p "$PASSWORD" scp backend/Dockerfile $SERVER:$DEPLOY_DIR/backend/
echo "✓ Dockerfile 已上传"

echo ""
echo "步骤 6: 在服务器上重新构建并部署..."
echo "-----------------------------------"
sshpass -p "$PASSWORD" ssh $SERVER << 'ENDSSH'
cd /root/z-pulse

echo "停止现有容器..."
docker-compose down 2>/dev/null || true

echo "重新构建前端镜像..."
cd frontend
docker build -t zpulse-frontend:latest .
cd ..

echo "重新构建后端镜像..."
cd backend
docker build -t z-pulse-api-backend:latest -f Dockerfile ../
cd ..

echo "启动所有服务..."
docker-compose up -d

echo "等待服务启动..."
sleep 15

echo ""
echo "检查服务状态..."
docker-compose ps
ENDSSH

echo ""
echo "步骤 7: 测试API..."
echo "-----------------------------------"
echo "测试二维码API:"
sshpass -p "$PASSWORD" ssh $SERVER "curl -s http://localhost:8000/api/werss/qrcode | jq ."

echo ""
echo "========================================="
echo "✅ 部署完成！"
echo "========================================="
echo "主应用: http://47.97.115.235:8899"
echo "二维码页面: http://47.97.115.235:8899/we-rss-qrcode-direct"
echo "WeRSS后台: http://47.97.115.235:8080"
echo ""
echo "检查日志:"
echo "  ssh root@47.97.115.235 'cd /root/z-pulse && docker-compose logs -f --tail=50'"
echo "========================================="
