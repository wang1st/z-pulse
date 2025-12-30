#!/bin/bash
# ============================================
# Z-Pulse 镜像导入脚本
# 用于在服务器上导入从本地导出的镜像
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Z-Pulse 镜像导入脚本${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

IMAGE_FILE="${1:-z-pulse-images.tar}"

if [ ! -f "${IMAGE_FILE}" ]; then
    echo -e "${RED}错误: 找不到镜像文件 ${IMAGE_FILE}${NC}"
    echo ""
    echo "使用方法:"
    echo "  ./import-images.sh [镜像文件路径]"
    echo ""
    echo "示例:"
    echo "  ./import-images.sh z-pulse-images.tar"
    exit 1
fi

FILE_SIZE=$(du -h "${IMAGE_FILE}" | cut -f1)
echo -e "${YELLOW}镜像文件: ${IMAGE_FILE} (${FILE_SIZE})${NC}"
echo ""

echo -e "${YELLOW}步骤 1: 导入镜像${NC}"
echo "  这可能需要几分钟，请耐心等待..."
docker load -i "${IMAGE_FILE}"

if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} 导入成功！"
else
    echo -e "  ${RED}✗${NC} 导入失败"
    exit 1
fi

echo ""
echo -e "${YELLOW}步骤 2: 验证镜像${NC}"
EXPECTED_IMAGES=(
    "postgres:15-alpine"
    "redis:7-alpine"
    "nginx:latest"
    "rachelos/we-mp-rss:latest"
)

ALL_PRESENT=true
for image in "${EXPECTED_IMAGES[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${image}$"; then
        echo -e "  ${GREEN}✓${NC} ${image}"
    else
        echo -e "  ${RED}✗${NC} ${image} (缺失)"
        ALL_PRESENT=false
    fi
done

if [ "$ALL_PRESENT" = true ]; then
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}所有镜像已成功导入！${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo "下一步："
    echo "  1. 启动服务："
    echo "     docker compose up -d"
    echo ""
    echo "  2. 查看服务状态："
    echo "     docker compose ps"
    echo ""
    echo "  3. 查看日志："
    echo "     docker compose logs -f"
else
    echo ""
    echo -e "${RED}警告: 部分镜像缺失，请检查导入过程${NC}"
    exit 1
fi

