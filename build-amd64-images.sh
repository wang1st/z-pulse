#!/bin/bash

# Z-Pulse AMD64 镜像构建脚本
# 用于在 macOS (ARM) 上构建适用于阿里云服务器 (AMD64) 的 Docker 镜像

set -e

echo "========================================="
echo "开始构建 AMD64 架构的 Docker 镜像"
echo "========================================="

# 创建构建输出目录
BUILD_DIR="./build-amd64"
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR
cd $BUILD_DIR

echo ""
echo "步骤 1: 拉取官方镜像的 AMD64 版本..."
echo "-----------------------------------"

echo "拉取 postgres:15-alpine (AMD64)..."
docker pull --platform linux/amd64 postgres:15-alpine
docker save --platform linux/amd64 -o postgres.tar postgres:15-alpine
echo "✓ 已保存 postgres.tar"

echo "拉取 redis:7-alpine (AMD64)..."
docker pull --platform linux/amd64 redis:7-alpine
docker save --platform linux/amd64 -o redis.tar redis:7-alpine
echo "✓ 已保存 redis.tar"

echo "拉取 nginx:alpine (AMD64)..."
docker pull --platform linux/amd64 nginx:alpine
docker save --platform linux/amd64 -o nginx.tar nginx:alpine
echo "✓ 已保存 nginx.tar"

echo ""
echo "步骤 2: 构建自定义应用镜像..."
echo "-----------------------------------"

# 保存项目根目录
PROJECT_ROOT=$(pwd)/..

# 构建前端镜像
echo "构建 frontend-web (AMD64)..."
cd $PROJECT_ROOT/frontend
docker buildx build --platform linux/amd64 -t zpulse-frontend:latest --load .
docker save --platform linux/amd64 -o $PROJECT_ROOT/$BUILD_DIR/frontend.tar zpulse-frontend:latest
echo "✓ 已保存 frontend.tar"

# 构建后端镜像
echo "构建 api-backend (AMD64)..."
cd $PROJECT_ROOT
docker buildx build --platform linux/amd64 -f backend/Dockerfile -t z-pulse-api-backend:latest --load .
docker save --platform linux/amd64 -o $PROJECT_ROOT/$BUILD_DIR/backend.tar z-pulse-api-backend:latest
echo "✓ 已保存 backend.tar"

# 拉取 RSS bridge 官方镜像的 AMD64 版本
echo "拉取 rachelos/we-mp-rss:latest (AMD64)..."
docker pull --platform linux/amd64 rachelos/we-mp-rss:latest
docker save --platform linux/amd64 -o $PROJECT_ROOT/$BUILD_DIR/werss.tar rachelos/we-mp-rss:latest
echo "✓ 已保存 werss.tar"

cd $PROJECT_ROOT/$BUILD_DIR

echo ""
echo "步骤 3: 打包所有镜像..."
echo "-----------------------------------"
tar -czf zpulse_images_amd64.tar.gz *.tar
echo "✓ 已打包 zpulse_images_amd64.tar.gz"

# 显示文件大小
echo ""
echo "========================================="
echo "镜像文件大小:"
echo "========================================="
ls -lh *.tar *.tar.gz

echo ""
echo "========================================="
echo "构建完成！"
echo "========================================="
echo "镜像文件位置: $BUILD_DIR/zpulse_images_amd64.tar.gz"
echo ""
echo "后续步骤:"
echo "1. 上传到服务器: scp zpulse_images_amd64.tar.gz root@47.97.115.235:/root/"
echo "2. 在服务器解压: tar -xzf zpulse_images_amd64.tar.gz"
echo "3. 加载镜像: docker load -i postgres.tar (依次加载所有镜像)"
echo "========================================="
