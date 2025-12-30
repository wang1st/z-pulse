#!/bin/bash
# ============================================
# Z-Pulse 镜像拉取脚本（服务器端）
# 用于在服务器上手动拉取所有需要的外部镜像
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Z-Pulse 镜像拉取脚本（服务器端）${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# 定义需要拉取的镜像
IMAGES=(
    "postgres:15-alpine"
    "redis:7-alpine"
    "nginx:latest"
    "rachelos/we-mp-rss:latest"
)

FAILED_IMAGES=()
SUCCESS_IMAGES=()

echo -e "${YELLOW}开始拉取镜像...${NC}"
echo ""

for image in "${IMAGES[@]}"; do
    echo -e "${YELLOW}正在拉取: ${image}${NC}"
    if docker pull "${image}"; then
        echo -e "  ${GREEN}✓${NC} ${image} 拉取成功"
        SUCCESS_IMAGES+=("${image}")
    else
        echo -e "  ${RED}✗${NC} ${image} 拉取失败"
        FAILED_IMAGES+=("${image}")
    fi
    echo ""
done

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}拉取完成${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

if [ ${#SUCCESS_IMAGES[@]} -gt 0 ]; then
    echo -e "${GREEN}成功拉取的镜像 (${#SUCCESS_IMAGES[@]}/${#IMAGES[@]}):${NC}"
    for image in "${SUCCESS_IMAGES[@]}"; do
        echo -e "  ${GREEN}✓${NC} ${image}"
    done
    echo ""
fi

if [ ${#FAILED_IMAGES[@]} -gt 0 ]; then
    echo -e "${RED}拉取失败的镜像 (${#FAILED_IMAGES[@]}/${#IMAGES[@]}):${NC}"
    for image in "${FAILED_IMAGES[@]}"; do
        echo -e "  ${RED}✗${NC} ${image}"
    done
    echo ""
    echo -e "${YELLOW}建议：${NC}"
    echo "  如果部分镜像拉取失败，请使用从本地开发机导入镜像的方法："
    echo "  1. 在本地开发机上运行: ./scripts/export-images.sh"
    echo "  2. 传输镜像文件到服务器: scp z-pulse-images.tar root@server:/opt/z-pulse/"
    echo "  3. 在服务器上运行: ./scripts/import-images.sh z-pulse-images.tar"
    echo ""
    exit 1
else
    echo -e "${GREEN}所有镜像已成功拉取！${NC}"
    echo ""
    echo "下一步："
    echo "  1. 启动服务："
    echo "     docker compose up -d"
    echo ""
    echo "  2. 查看服务状态："
    echo "     docker compose ps"
    echo ""
    exit 0
fi

