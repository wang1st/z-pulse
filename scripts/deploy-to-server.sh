#!/bin/bash
# ============================================
# Z-Pulse 自动部署脚本
# 用于在开发机上构建镜像并自动部署到服务器
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Z-Pulse 自动部署脚本${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# 检查是否在项目根目录
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误: 请在项目根目录执行此脚本${NC}"
    exit 1
fi

# 读取 .env 文件中的配置
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: 未找到 .env 文件${NC}"
    echo "请先创建 .env 文件：cp env.example .env"
    exit 1
fi

# 读取服务器配置
SCP_HOST_ADDRESS=$(grep -E '^SCP_HOST_ADDRESS=' .env 2>/dev/null | cut -d '=' -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//' | tr -d '\r\n')
SCP_ROOT_PASSWORD=$(grep -E '^SCP_ROOT_PASSWORD=' .env 2>/dev/null | cut -d '=' -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//' | tr -d '\r\n')

# 服务器配置（支持命令行参数或从 .env 读取）
SERVER_IP="${1:-${SCP_HOST_ADDRESS:-47.97.115.235}}"
SERVER_USER="${2:-root}"
SERVER_PATH="/opt/z-pulse"

# 验证服务器地址
if [ -z "$SERVER_IP" ]; then
    echo -e "${RED}错误: 未指定服务器地址${NC}"
    echo "请在 .env 文件中设置 SCP_HOST_ADDRESS，或通过命令行参数指定："
    echo "  ./scripts/deploy-to-server.sh [服务器IP] [用户名]"
    exit 1
fi

if [ -z "$SCP_ROOT_PASSWORD" ]; then
    echo -e "${YELLOW}警告: 未在 .env 文件中找到 SCP_ROOT_PASSWORD${NC}"
    echo "将尝试使用 SSH 密钥认证"
    USE_PASSWORD=false
else
    USE_PASSWORD=true
    echo -e "${BLUE}已从 .env 文件读取服务器密码${NC}"
    
    # 检查是否安装了 sshpass
    if ! command -v sshpass &> /dev/null; then
        echo -e "${YELLOW}检测到需要使用密码认证，但未安装 sshpass${NC}"
        echo "正在检查安装方式..."
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "macOS 系统，正在尝试安装 sshpass..."
            if command -v brew &> /dev/null; then
                echo "使用 Homebrew 安装 sshpass..."
                brew install hudochenkov/sshpass/sshpass || {
                    echo -e "${RED}安装失败，请手动安装：${NC}"
                    echo "  brew install hudochenkov/sshpass/sshpass"
                    echo ""
                    echo "或者配置 SSH 密钥认证（推荐）："
                    echo "  ssh-copy-id root@${SERVER_IP}"
                    exit 1
                }
                echo -e "${GREEN}✓${NC} sshpass 安装成功"
            else
                echo -e "${RED}未找到 Homebrew，请手动安装 sshpass 或配置 SSH 密钥${NC}"
                echo "安装 sshpass: brew install hudochenkov/sshpass/sshpass"
                echo "或配置 SSH 密钥: ssh-copy-id root@${SERVER_IP}"
                exit 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "Linux 系统，尝试安装 sshpass..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y sshpass
            elif command -v yum &> /dev/null; then
                sudo yum install -y sshpass
            else
                echo "无法自动安装 sshpass，请手动安装"
                exit 1
            fi
        else
            echo "不支持的系统类型，请手动安装 sshpass 或配置 SSH 密钥"
            exit 1
        fi
    fi
fi

# 读取 NEXT_PUBLIC_API_URL（用于构建）
NEXT_PUBLIC_API_URL=$(grep -E '^NEXT_PUBLIC_API_URL=' .env 2>/dev/null | cut -d '=' -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//' | tr -d '\r\n')
if [ -z "$NEXT_PUBLIC_API_URL" ]; then
    NEXT_PUBLIC_API_URL="http://api-backend:8000"
    echo -e "${YELLOW}未找到 NEXT_PUBLIC_API_URL，使用默认值: ${NEXT_PUBLIC_API_URL}${NC}"
fi

echo -e "${BLUE}部署配置：${NC}"
echo "  服务器: ${SERVER_USER}@${SERVER_IP}"
echo "  路径: ${SERVER_PATH}"
echo "  认证方式: $([ "$USE_PASSWORD" = true ] && echo "密码" || echo "SSH密钥")"
echo ""

# SSH 命令包装（根据认证方式选择）
if [ "$USE_PASSWORD" = true ]; then
    # 使用 sshpass，密码通过环境变量传递更安全
    export SSHPASS="${SCP_ROOT_PASSWORD}"
    SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    SCP_CMD="sshpass -e scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
else
    SSH_CMD="ssh -o StrictHostKeyChecking=no"
    SCP_CMD="scp -o StrictHostKeyChecking=no"
fi

# 步骤1：构建并导出镜像
echo -e "${YELLOW}步骤 1: 构建并导出镜像...${NC}"
echo ""

# 1.1 拉取并导出外部镜像（指定平台为 linux/amd64，兼容服务器）
echo -e "${YELLOW}  1.1 拉取外部镜像（linux/amd64平台）...${NC}"
echo "  注意：在 Mac M 系列上拉取 AMD64 镜像需要模拟，可能需要较长时间"
echo "  正在拉取 postgres:15-alpine..."
docker pull --platform linux/amd64 postgres:15-alpine
echo "  正在拉取 redis:7-alpine..."
docker pull --platform linux/amd64 redis:7-alpine
echo "  正在拉取 nginx:latest..."
docker pull --platform linux/amd64 nginx:latest
echo "  正在拉取 rachelos/we-mp-rss:latest..."
docker pull --platform linux/amd64 rachelos/we-mp-rss:latest
echo -e "${GREEN}✓${NC} 外部镜像拉取完成"

echo -e "${YELLOW}  1.2 导出外部镜像...${NC}"
docker save postgres:15-alpine redis:7-alpine nginx:latest rachelos/we-mp-rss:latest -o z-pulse-external-images.tar

# 1.3 构建应用镜像
echo -e "${YELLOW}  1.3 构建应用镜像...${NC}"
export NEXT_PUBLIC_API_URL
chmod +x scripts/build-and-export-images.sh
./scripts/build-and-export-images.sh

echo -e "${GREEN}✓${NC} 镜像构建完成"
echo ""

# 1.4 分卷压缩镜像文件（每个分卷 256MB，便于传输）
echo -e "${YELLOW}  1.4 分卷压缩镜像文件（每个分卷 256MB）...${NC}"
SPLIT_SIZE="256M"

# 压缩并分卷外部镜像
if [ -f "z-pulse-external-images.tar" ]; then
    echo "  压缩外部镜像..."
    tar -czf - z-pulse-external-images.tar | split -b ${SPLIT_SIZE} - z-pulse-external-images.tar.gz.part
    EXTERNAL_PARTS=$(ls z-pulse-external-images.tar.gz.part* 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✓ 外部镜像已分卷为 ${EXTERNAL_PARTS} 个文件"
fi

# 压缩并分卷应用镜像
if [ -f "z-pulse-built-images.tar" ]; then
    echo "  压缩应用镜像（这可能需要几分钟）..."
    tar -czf - z-pulse-built-images.tar | split -b ${SPLIT_SIZE} - z-pulse-built-images.tar.gz.part
    BUILT_PARTS=$(ls z-pulse-built-images.tar.gz.part* 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✓ 应用镜像已分卷为 ${BUILT_PARTS} 个文件"
fi

echo ""

# 步骤2：上传镜像到服务器
echo -e "${YELLOW}步骤 2: 上传镜像到服务器...${NC}"

# 2.1 确保服务器目录存在
echo -e "${YELLOW}  2.1 检查服务器目录...${NC}"
$SSH_CMD ${SERVER_USER}@${SERVER_IP} "mkdir -p ${SERVER_PATH}" || {
    echo -e "${RED}✗${NC} 无法连接到服务器或创建目录"
    exit 1
}

# 2.2 上传外部镜像分卷文件
echo -e "${YELLOW}  2.2 上传外部镜像分卷文件...${NC}"
EXTERNAL_PARTS=$(ls z-pulse-external-images.tar.gz.part* 2>/dev/null | wc -l | tr -d ' ')
if [ "$EXTERNAL_PARTS" -gt 0 ]; then
    echo "  共 ${EXTERNAL_PARTS} 个分卷文件"
    PART_COUNT=0
    for part in z-pulse-external-images.tar.gz.part*; do
        PART_COUNT=$((PART_COUNT + 1))
        echo "  上传 ${PART_COUNT}/${EXTERNAL_PARTS}: $(basename $part)"
        if [ "$USE_PASSWORD" = true ]; then
            rsync -avz --progress -e "sshpass -e ssh -o StrictHostKeyChecking=no" \
                "$part" ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/ || {
                echo -e "${RED}✗${NC} 分卷上传失败: $part"
                exit 1
            }
        else
            rsync -avz --progress -e "ssh -o StrictHostKeyChecking=no" \
                "$part" ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/ || {
                echo -e "${RED}✗${NC} 分卷上传失败: $part"
                exit 1
            }
        fi
    done
    echo -e "${GREEN}✓${NC} 外部镜像分卷上传完成"
else
    echo -e "${YELLOW}⚠️${NC} 未找到外部镜像分卷文件"
fi

# 2.3 上传应用镜像分卷文件
echo -e "${YELLOW}  2.3 上传应用镜像分卷文件...${NC}"
BUILT_PARTS=$(ls z-pulse-built-images.tar.gz.part* 2>/dev/null | wc -l | tr -d ' ')
if [ "$BUILT_PARTS" -gt 0 ]; then
    echo "  共 ${BUILT_PARTS} 个分卷文件（每个约256MB）"
    PART_COUNT=0
    for part in z-pulse-built-images.tar.gz.part*; do
        PART_COUNT=$((PART_COUNT + 1))
        echo "  上传 ${PART_COUNT}/${BUILT_PARTS}: $(basename $part)"
        if [ "$USE_PASSWORD" = true ]; then
            rsync -avz --progress -e "sshpass -e ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60" \
                "$part" ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/ || {
                echo -e "${YELLOW}⚠️${NC} 分卷上传中断，可以重新运行脚本继续上传"
                echo -e "${RED}✗${NC} 分卷上传失败: $part"
                exit 1
            }
        else
            rsync -avz --progress -e "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60" \
                "$part" ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/ || {
                echo -e "${YELLOW}⚠️${NC} 分卷上传中断，可以重新运行脚本继续上传"
                echo -e "${RED}✗${NC} 分卷上传失败: $part"
                exit 1
            }
        fi
    done
    echo -e "${GREEN}✓${NC} 应用镜像分卷上传完成"
else
    echo -e "${YELLOW}⚠️${NC} 未找到应用镜像分卷文件"
fi

echo -e "${GREEN}✓${NC} 镜像上传完成"
echo ""

# 步骤3：在服务器上导入镜像并启动服务
echo -e "${YELLOW}步骤 3: 在服务器上导入镜像并启动服务...${NC}"

# 3.1 检查并清理磁盘空间
echo -e "${YELLOW}  3.1 检查磁盘空间...${NC}"
$SSH_CMD ${SERVER_USER}@${SERVER_IP} "df -h / && echo '---' && docker system df" || true

echo -e "${YELLOW}  3.2 清理旧的 Docker 资源（如果需要）...${NC}"
$SSH_CMD ${SERVER_USER}@${SERVER_IP} "cd ${SERVER_PATH} && \
    docker compose -f docker-compose.prod.yml down 2>/dev/null || true && \
    docker system prune -f --volumes 2>/dev/null || true && \
    echo '清理完成'" || true

# 3.3 导入镜像
echo -e "${YELLOW}  3.3 导入镜像...${NC}"
$SSH_CMD ${SERVER_USER}@${SERVER_IP} "cd ${SERVER_PATH} && \
    docker load -i z-pulse-external-images.tar && \
    chmod +x scripts/import-built-images.sh && \
    ./scripts/import-built-images.sh z-pulse-built-images.tar" || {
    echo -e "${YELLOW}⚠️${NC} 镜像导入可能失败，检查磁盘空间..."
    $SSH_CMD ${SERVER_USER}@${SERVER_IP} "df -h / && docker system df"
    echo -e "${RED}✗${NC} 镜像导入失败，可能是磁盘空间不足"
    echo "建议："
    echo "  1. 清理服务器上的旧镜像和容器"
    echo "  2. 删除不需要的文件"
    echo "  3. 或者增加服务器磁盘空间"
    exit 1
}

# 3.5 检查 .env 文件
echo -e "${YELLOW}  3.5 检查配置文件...${NC}"
$SSH_CMD ${SERVER_USER}@${SERVER_IP} "cd ${SERVER_PATH} && \
    if [ ! -f .env ]; then \
        echo '⚠️  未找到 .env 文件，正在从模板创建...'; \
        cp env.example .env; \
        echo '请编辑 .env 文件配置必需的变量'; \
    fi" || {
    echo -e "${RED}✗${NC} 配置文件检查失败"
    exit 1
}

# 3.6 初始化数据库并启动服务
echo -e "${YELLOW}  3.6 启动服务...${NC}"
$SSH_CMD ${SERVER_USER}@${SERVER_IP} "cd ${SERVER_PATH} && \
    docker compose -f docker-compose.prod.yml up -d postgres-db && \
    sleep 10 && \
    docker compose -f docker-compose.prod.yml exec -T postgres-db psql -U zpulse -d zpulse -f /docker-entrypoint-initdb.d/init.sql 2>/dev/null || true && \
    docker compose -f docker-compose.prod.yml up -d" || {
    echo -e "${RED}✗${NC} 服务启动失败"
    exit 1
}

echo -e "${GREEN}✓${NC} 服务启动完成"
echo ""

# 步骤4：验证部署
echo -e "${YELLOW}步骤 4: 验证部署...${NC}"
$SSH_CMD ${SERVER_USER}@${SERVER_IP} "cd ${SERVER_PATH} && docker compose -f docker-compose.prod.yml ps"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "服务器地址: http://${SERVER_IP}"
echo "管理后台: http://${SERVER_IP}/admin"
echo ""
echo "查看服务状态:"
echo "  ssh ${SERVER_USER}@${SERVER_IP}"
echo "  cd ${SERVER_PATH}"
echo "  docker compose -f docker-compose.prod.yml ps"
echo ""
echo "查看日志:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
echo ""

