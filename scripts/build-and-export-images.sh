#!/bin/bash
# ============================================
# Z-Pulse 镜像构建和导出脚本（开发机）
# 用于在开发机上构建所有镜像并导出，以便传输到低配置服务器
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Z-Pulse 镜像构建和导出脚本（开发机）${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# 检查是否在项目根目录
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误: 请在项目根目录执行此脚本${NC}"
    exit 1
fi

# 读取环境变量（用于构建参数）
# 安全地加载 .env 文件，只读取 NEXT_PUBLIC_API_URL
if [ -f ".env" ]; then
    # 使用 grep 和 sed 安全地提取 NEXT_PUBLIC_API_URL 的值
    # 只匹配以 KEY= 开头的行，忽略注释和空行
    ENV_VALUE=$(grep -E '^NEXT_PUBLIC_API_URL=' .env 2>/dev/null | head -1 | cut -d '=' -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//' | tr -d '\r\n')
    
    if [ -n "$ENV_VALUE" ]; then
        export NEXT_PUBLIC_API_URL="$ENV_VALUE"
        echo -e "${BLUE}已从 .env 文件加载 NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}${NC}"
    else
        echo -e "${YELLOW}未在 .env 文件中找到 NEXT_PUBLIC_API_URL，将使用默认值${NC}"
    fi
else
    echo -e "${YELLOW}提示: 未找到 .env 文件，将使用默认值${NC}"
fi

# 设置镜像标签（使用 server 标签，避免覆盖本地镜像）
BACKEND_IMAGE="zpulse-backend:server"
FRONTEND_IMAGE="zpulse-frontend:server"
OUTPUT_FILE="z-pulse-built-images.tar"

echo -e "${YELLOW}步骤 1: 构建后端镜像...${NC}"
echo "  这可能需要几分钟，请耐心等待..."

# 直接使用 docker build 构建后端镜像（指定平台为 linux/amd64，兼容服务器）
docker build --platform linux/amd64 -t "${BACKEND_IMAGE}" -f backend/Dockerfile .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 后端镜像构建完成: ${BACKEND_IMAGE}"
else
    echo -e "${RED}✗${NC} 后端镜像构建失败"
    exit 1
fi
echo ""

echo -e "${YELLOW}步骤 2: 构建前端镜像...${NC}"
echo "  这可能需要几分钟，请耐心等待..."

# 设置构建参数
NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://api-backend:8000}"

# 直接使用 docker build 构建前端镜像（指定平台为 linux/amd64，兼容服务器）
docker build --platform linux/amd64 -t "${FRONTEND_IMAGE}" \
    --build-arg NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL}" \
    -f frontend/Dockerfile \
    frontend/

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 前端镜像构建完成: ${FRONTEND_IMAGE}"
else
    echo -e "${RED}✗${NC} 前端镜像构建失败"
    exit 1
fi
echo ""

echo -e "${YELLOW}步骤 3: 导出镜像...${NC}"
echo "  正在导出 ${BACKEND_IMAGE} 和 ${FRONTEND_IMAGE}..."

# 导出时重新标记为 latest，以便服务器使用
docker tag "${BACKEND_IMAGE}" zpulse-backend:latest
docker tag "${FRONTEND_IMAGE}" zpulse-frontend:latest
docker save zpulse-backend:latest zpulse-frontend:latest -o "${OUTPUT_FILE}"

if [ $? -eq 0 ]; then
    FILE_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
    echo -e "${GREEN}✓${NC} 镜像已成功导出到 ${OUTPUT_FILE} (${FILE_SIZE})"
else
    echo -e "${RED}✗${NC} 镜像导出失败"
    exit 1
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}构建和导出完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "下一步："
echo "  1. 将 ${OUTPUT_FILE} 文件传输到您的服务器："
echo "     scp ${OUTPUT_FILE} root@your-server-ip:/opt/z-pulse/"
echo ""
echo "  2. 在服务器上执行导入脚本："
echo "     cd /opt/z-pulse"
echo "     chmod +x scripts/import-built-images.sh"
echo "     ./scripts/import-built-images.sh ${OUTPUT_FILE}"
echo ""
echo "  3. 导入成功后，修改 docker-compose.yml 使用预构建镜像，然后启动服务："
echo "     docker compose up -d"
echo ""

