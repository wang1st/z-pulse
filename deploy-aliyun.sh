#!/bin/bash

# Z-Pulse 阿里云服务器自动部署脚本
# 在本地 macOS 上运行，自动完成镜像构建、上传和部署

set -e

SERVER="root@47.97.115.235"
DEPLOY_DIR="/root/z-pulse"
LOCAL_BUILD_DIR="./build-amd64"

echo "========================================="
echo "Z-Pulse 阿里云自动部署脚本"
echo "========================================="

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  警告: 有未提交的 git 更改"
    read -p "继续部署? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "步骤 1: 构建 AMD64 镜像..."
echo "-----------------------------------"
if [ -f "$LOCAL_BUILD_DIR/zpulse_images_amd64.tar.gz" ]; then
    echo "✓ 镜像文件已存在，跳过构建步骤"
else
    chmod +x build-amd64-images.sh
    ./build-amd64-images.sh
fi

echo ""
echo "步骤 2: 导出数据库..."
echo "-----------------------------------"
mkdir -p $LOCAL_BUILD_DIR/db
echo "导出 PostgreSQL 数据库..."
docker-compose exec -T postgres-db pg_dump -U zpulse zpulse > $LOCAL_BUILD_DIR/db/zpulse_db.sql
echo "✓ PostgreSQL 数据库已导出"

echo "复制 we-mp-rss 数据库..."
docker cp zpulse-rss:/app/data/werss.db $LOCAL_BUILD_DIR/db/werss.db
echo "✓ we-mp-rss 数据库已复制"

echo ""
echo "步骤 3: 准备部署文件..."
echo "-----------------------------------"
cp docker-compose.yml $LOCAL_BUILD_DIR/
cp nginx/nginx.conf $LOCAL_BUILD_DIR/
cp .env $LOCAL_BUILD_DIR/
echo "✓ 配置文件已复制"

echo ""
echo "步骤 4: 上传到服务器..."
echo "-----------------------------------"
echo "在服务器上创建部署目录..."
ssh $SERVER "mkdir -p $DEPLOY_DIR"

echo "上传镜像文件..."
scp $LOCAL_BUILD_DIR/zpulse_images_amd64.tar.gz $SERVER:$DEPLOY_DIR/

echo "上传配置文件..."
scp $LOCAL_BUILD_DIR/docker-compose.yml $SERVER:$DEPLOY_DIR/
scp $LOCAL_BUILD_DIR/nginx.conf $SERVER:$DEPLOY_DIR/
scp $LOCAL_BUILD_DIR/.env $SERVER:$DEPLOY_DIR/

echo "上传数据库文件..."
scp $LOCAL_BUILD_DIR/db/zpulse_db.sql $SERVER:$DEPLOY_DIR/
scp $LOCAL_BUILD_DIR/db/werss.db $SERVER:$DEPLOY_DIR/

echo "✓ 所有文件已上传"

echo ""
echo "步骤 5: 在服务器上部署..."
echo "-----------------------------------"
ssh $SERVER << 'ENDSSH'
cd /root/z-pulse

echo "停止现有容器..."
docker-compose down 2>/dev/null || true

echo "解压并加载镜像..."
tar -xzf zpulse_images_amd64.tar.gz
docker load -i postgres.tar
docker load -i redis.tar
docker load -i nginx.tar
docker load -i backend.tar
docker load -i frontend.tar
docker load -i werss.tar

echo "清理镜像文件..."
rm -f *.tar zpulse_images_amd64.tar.gz

echo "启动数据库..."
docker-compose up -d postgres-db redis
sleep 10

echo "导入数据..."
docker-compose exec -T postgres-db psql -U zpulse zpulse < zpulse_db.sql
rm -f zpulse_db.sql

echo "启动 RSS bridge..."
docker-compose up -d rss-bridge
sleep 10

echo "导入 we-mp-rss 数据库..."
docker-compose exec -T rss-bridge sh -c 'cat > /app/data/werss.db' < werss.db
docker-compose restart rss-bridge
rm -f werss.db

echo "启动所有服务..."
docker-compose down
docker-compose up -d
sleep 20

echo "检查服务状态..."
docker-compose ps

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
ENDSSH

echo ""
echo "========================================="
echo "服务地址"
echo "========================================="
echo "主应用: http://47.97.115.235:8899"
echo "管理后台: http://47.97.115.235:8899/admin"
echo "RSS采集: http://47.97.115.235:8080"
echo ""
echo "⚠️  重要: 请访问 http://47.97.115.235:8080 重新扫码登录微信！"
echo "========================================="
