#!/bin/bash
# ============================================
# Z-Pulse 镜像导出脚本
# 用于在可以访问 Docker Hub 的环境中导出镜像
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Z-Pulse 镜像导出脚本${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# 定义需要导出的镜像
IMAGES=(
    "postgres:15-alpine"
    "redis:7-alpine"
    "nginx:latest"
    "rachelos/we-mp-rss:latest"
)

OUTPUT_FILE="z-pulse-images.tar"

echo -e "${YELLOW}步骤 1: 检查镜像是否存在${NC}"
MISSING_IMAGES=()
for image in "${IMAGES[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${image}$"; then
        echo -e "  ${GREEN}✓${NC} ${image}"
    else
        echo -e "  ${RED}✗${NC} ${image} (缺失)"
        MISSING_IMAGES+=("${image}")
    fi
done

if [ ${#MISSING_IMAGES[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}步骤 2: 拉取缺失的镜像${NC}"
    for image in "${MISSING_IMAGES[@]}"; do
        echo -e "  正在拉取: ${image}"
        docker pull "${image}" || {
            echo -e "  ${RED}错误: 无法拉取 ${image}${NC}"
            exit 1
        }
    done
else
    echo -e "${GREEN}所有镜像已存在，跳过拉取步骤${NC}"
fi

echo ""
echo -e "${YELLOW}步骤 3: 导出镜像到 ${OUTPUT_FILE}${NC}"
echo "  这可能需要几分钟，请耐心等待..."
docker save "${IMAGES[@]}" -o "${OUTPUT_FILE}"

if [ $? -eq 0 ]; then
    FILE_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
    echo -e "  ${GREEN}✓${NC} 导出成功！文件大小: ${FILE_SIZE}"
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}导出完成！${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo "下一步："
    echo "  1. 将 ${OUTPUT_FILE} 传输到服务器："
    echo "     scp ${OUTPUT_FILE} root@your-server-ip:/opt/z-pulse/"
    echo ""
    echo "  2. 在服务器上导入镜像："
    echo "     cd /opt/z-pulse"
    echo "     docker load -i ${OUTPUT_FILE}"
    echo ""
    echo "  3. 启动服务："
    echo "     docker compose up -d"
else
    echo -e "  ${RED}✗${NC} 导出失败"
    exit 1
fi

