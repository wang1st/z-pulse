# 阿里云云主机部署指南

本指南将帮助您将 Z-Pulse 系统部署到阿里云云主机，并迁移现有的晨报日报数据。

## 📋 前置要求

### 1. 阿里云服务器要求

- **操作系统**: Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- **最低配置**（推荐，因为镜像在开发机上构建）: 
  - CPU: 2核
  - 内存: 2GB
  - 硬盘: 40GB SSD
- **推荐配置**:
  - CPU: 2核
  - 内存: 4GB
  - 硬盘: 60GB SSD

**注意**：由于镜像在开发机上构建，服务器只需运行容器，配置要求较低。

### 2. 网络要求

- 开放端口: `80`, `443`, `8000`, `3000`（可选，用于调试）
- 建议配置安全组规则，只允许必要的端口访问

### 3. 域名（可选但推荐）

- 已备案的域名（用于HTTPS）
- 域名DNS解析到云主机IP

## 🔧 第一步：准备云主机环境

### 1.1 连接到云主机

```bash
ssh root@your-server-ip
# 或使用您的用户名
ssh your-username@your-server-ip
```

### 1.2 更新系统

```bash
# Ubuntu/Debian
apt update && apt upgrade -y

# CentOS
yum update -y
```

### 1.3 安装 Docker 和 Docker Compose

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 启动 Docker
systemctl start docker
systemctl enable docker

# 配置 Docker 镜像加速器（重要！解决国内访问 Docker Hub 慢的问题）
# 创建或编辑 Docker daemon 配置文件
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 如果使用阿里云容器镜像服务（推荐，需要登录阿里云控制台获取专属加速地址）
# 访问：https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors
# 获取您的专属加速地址，然后替换上面的镜像地址

# 重启 Docker 使配置生效
systemctl daemon-reload
systemctl restart docker

# 验证镜像加速器配置
docker info | grep -A 10 "Registry Mirrors"

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 1.4 安装 Git

```bash
# Ubuntu/Debian
apt install git -y

# CentOS
yum install git -y
```

## 📦 第二步：上传项目代码

### 2.1 方式一：使用 Git（推荐）

#### 首次部署（新服务器）

```bash
# 在云主机上克隆项目
cd /opt
git clone https://gitee.com/wang1st/z-pulse.git z-pulse
cd z-pulse
```

#### 更新代码（已有仓库）

如果服务器上已经有旧版本的代码，由于 Git 历史已重置，需要重新克隆：

**方案A：删除旧仓库重新克隆（推荐，最简单）**

```bash
# 1. 备份重要文件（如 .env 配置文件）
cd /opt/z-pulse
cp .env .env.backup 2>/dev/null || echo "没有 .env 文件"

# 2. 停止所有服务
docker compose down

# 3. 返回上级目录并删除旧仓库
cd /opt
rm -rf z-pulse

# 4. 重新克隆最新代码
git clone https://gitee.com/wang1st/z-pulse.git z-pulse
cd z-pulse

# 5. 恢复配置文件
cp ../.env.backup .env 2>/dev/null || echo "需要重新配置 .env"

# 6. 检查代码版本
git log --oneline -1
# 应该显示: Initial commit: Z-Pulse 财政信息聚合系统
```

**方案B：重置现有仓库（保留工作目录）**

```bash
# 1. 进入项目目录
cd /opt/z-pulse

# 2. 停止所有服务
docker compose down

# 3. 备份配置文件
cp .env .env.backup 2>/dev/null

# 4. 删除旧的 Git 历史
rm -rf .git

# 5. 重新初始化并拉取代码
git init
git remote add origin https://gitee.com/wang1st/z-pulse.git
git fetch origin
git reset --hard origin/main
git branch -M main

# 6. 恢复配置文件
cp .env.backup .env 2>/dev/null || echo "需要重新配置 .env"

# 7. 验证
git log --oneline -1
```

### 2.2 方式二：使用 SCP 上传

在本地机器上执行：

```bash
# 打包项目（排除 node_modules, __pycache__ 等）
cd /Users/ethan/Codes/z-pulse
tar --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.log' \
    -czf z-pulse.tar.gz .

# 上传到云主机
scp z-pulse.tar.gz root@your-server-ip:/opt/

# 在云主机上解压
ssh root@your-server-ip
cd /opt
tar -xzf z-pulse.tar.gz -C z-pulse
cd z-pulse
```

## ⚙️ 第三步：配置环境变量

**⚠️ 重要：在启动任何服务之前，必须先配置 `.env` 文件！**

### 3.1 复制环境变量模板

```bash
# 确保在项目根目录
cd /opt/z-pulse

# 复制模板文件
cp env.example .env
```

### 3.2 编辑环境变量

```bash
nano .env
# 或使用其他编辑器：vi .env
```

**必须配置的项（至少需要设置以下变量才能启动服务）：**

```bash
# 数据库配置
POSTGRES_USER=zpulse
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_DB=zpulse
REDIS_PASSWORD=your_redis_password_here

# AI服务配置
DASHSCOPE_API_KEY=your_aliyun_qwen_api_key

# 邮件服务配置
EMAIL_PROVIDER=brevo  # 或 sendgrid
BREVO_API_KEY=your_brevo_api_key
EMAIL_FROM=your-email@example.com
EMAIL_FROM_NAME=这里财动

# 网站URL（生产环境）
WEB_URL=https://your-domain.com
NEXT_PUBLIC_API_URL=https://your-domain.com/api
```

## 🚀 第四步：构建和部署镜像

**本部署方案采用在开发机上构建镜像，然后传输到服务器的方式。这样可以降低服务器配置要求，加快部署速度。**

### 4.1 在开发机上构建镜像

#### 步骤1：准备开发环境

在您的本地开发机（Mac/Windows/Linux）上：

```bash
# 1. 进入项目目录
cd /Users/ethan/Codes/z-pulse  # 或您的项目路径

# 2. 拉取最新代码（如果还没有）
git pull origin main

# 3. 准备构建环境变量（只需要 NEXT_PUBLIC_API_URL）
cp env.example .env
# 编辑 .env，设置 NEXT_PUBLIC_API_URL（用于前端构建）
# 其他变量可以留空，因为运行时在服务器上配置
nano .env
# 至少设置：NEXT_PUBLIC_API_URL=https://your-domain.com/api

# 4. 拉取并导出外部镜像（postgres, redis, nginx, we-mp-rss）
echo "正在拉取外部镜像..."
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker pull rachelos/we-mp-rss:latest

echo "正在导出外部镜像..."
docker save postgres:15-alpine redis:7-alpine nginx:latest rachelos/we-mp-rss:latest -o z-pulse-external-images.tar

# 5. 构建并导出应用镜像（后端和前端）
chmod +x scripts/build-and-export-images.sh
./scripts/build-and-export-images.sh

# 6. 传输所有镜像文件到服务器
echo "正在传输镜像文件到服务器..."
scp z-pulse-external-images.tar root@your-server-ip:/opt/z-pulse/
scp z-pulse-built-images.tar root@your-server-ip:/opt/z-pulse/

echo "✅ 镜像文件已传输完成！"
```

#### 在服务器上：

```bash
# 1. 进入项目目录
cd /opt/z-pulse

# 2. 配置 .env 文件（重要！镜像中不包含 .env，必须在服务器上配置）
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，正在从模板创建..."
    cp env.example .env
    echo "请编辑 .env 文件，至少配置必需的变量："
    echo "  - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB"
    echo "  - REDIS_PASSWORD"
    echo "  - DASHSCOPE_API_KEY"
    echo "  - BREVO_API_KEY 或 SENDGRID_API_KEY"
    echo "  - EMAIL_FROM"
    echo "  - WEB_URL, NEXT_PUBLIC_API_URL"
    echo ""
    echo "编辑命令: nano .env"
    echo ""
    echo "注意：.env 文件不需要打包到镜像中，环境变量在运行时从服务器的 .env 文件读取。"
    exit 1
fi

# 3. 导入预构建的镜像
chmod +x scripts/import-built-images.sh
./scripts/import-built-images.sh z-pulse-built-images.tar

# 4. 初始化数据库
docker compose -f docker-compose.prod.yml up -d postgres-db
sleep 10
docker compose -f docker-compose.prod.yml exec postgres-db psql -U zpulse -d zpulse -f /docker-entrypoint-initdb.d/init.sql

# 5. 确保所有外部镜像已导入（如果之前没有导入）
# 检查镜像是否存在
docker images | grep -E "postgres:15-alpine|redis:7-alpine|nginx:latest|rachelos/we-mp-rss:latest"

# 如果缺少外部镜像，需要先导入（参考下方"常见问题"中的 Docker Hub 连接超时解决方案）
# 或从开发机导出外部镜像并导入：
# 在开发机上：docker save postgres:15-alpine redis:7-alpine nginx:latest rachelos/we-mp-rss:latest -o z-pulse-external-images.tar
# 传输到服务器后：docker load -i z-pulse-external-images.tar

# 6. 启动所有服务（使用预构建镜像，环境变量从 .env 文件读取）
docker compose -f docker-compose.prod.yml up -d
```

**重要说明**：
- `.env` 文件**不需要**打包到镜像中
- 镜像构建时只需要 `NEXT_PUBLIC_API_URL`（用于前端构建）
- 运行时环境变量（数据库密码、API密钥等）通过 Docker Compose 从服务器的 `.env` 文件读取
- 修改 `.env` 后只需重启服务，**不需要重新构建镜像**
- 详细说明请参考：[使用预构建镜像时的 .env 配置说明](env-for-prebuilt-images.md)

**两种方式的区别：**

- **方式A**：服务器需要足够内存（4GB+）和 CPU 来构建镜像，构建时间较长
- **方式B**：服务器只需运行镜像，内存需求低（2GB 即可），启动速度快

### 4.2 启动所有服务（方式A：直接构建）

```bash
# 如果遇到 Docker Hub 连接超时，请先配置镜像加速器（见下方"常见问题"部分）
# 然后尝试拉取镜像
docker compose pull

# 启动所有服务
docker compose up -d
```

### 4.3 创建管理员账户

```bash
docker compose exec api-backend python -c "
import sys
sys.path.insert(0, '/app')
from shared.database import SessionLocal, User
from shared.auth import get_password_hash

db = SessionLocal()
try:
    user = User(
        username='admin',
        email='admin@example.com',
        full_name='管理员',
        hashed_password=get_password_hash('your_password'),
        is_superuser=True
    )
    db.add(user)
    db.commit()
    print('✅ 管理员用户创建成功')
except Exception as e:
    print(f'❌ 错误: {e}')
finally:
    db.close()
"
```

## 🔒 第五步：配置HTTPS（可选但推荐）

### 5.1 安装 Certbot

```bash
# Ubuntu/Debian
apt install certbot python3-certbot-nginx -y

# CentOS
yum install certbot python3-certbot-nginx -y
```

### 5.2 配置 Nginx

编辑 `nginx/nginx.conf`，添加SSL配置：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # ... 其他配置
}
```

### 5.3 获取SSL证书

```bash
certbot certonly --standalone -d your-domain.com
```

### 5.4 复制证书到项目目录

```bash
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/certs/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/certs/
```

### 5.5 重启Nginx

```bash
docker compose restart reverse-proxy
```

## 📊 第六步：验证部署

### 6.1 检查服务状态

```bash
docker compose -f docker-compose.prod.yml ps
```

所有服务应该显示为 `Up` 状态。

### 6.2 检查服务健康

```bash
# 检查API
curl http://localhost:8000/api/health

# 检查前端
curl http://localhost:3000

# 检查数据库
docker compose -f docker-compose.prod.yml exec postgres-db pg_isready -U zpulse
```

### 6.3 访问系统

- 前端界面: `https://your-domain.com`
- API文档: `https://your-domain.com/docs`
- 管理后台: `https://your-domain.com/admin`

## 🔄 第七步：数据迁移（如果有旧数据）

### 7.1 导出旧数据库

在旧服务器上：

```bash
docker compose -f docker-compose.prod.yml exec postgres-db pg_dump -U zpulse zpulse > backup.sql
```

### 7.2 导入到新数据库

在新服务器上：

```bash
docker compose -f docker-compose.prod.yml exec -T postgres-db psql -U zpulse -d zpulse < backup.sql
```

## 🛠️ 维护和监控

### 查看日志

```bash
# 所有服务日志
docker compose -f docker-compose.prod.yml logs -f

# 特定服务日志
docker compose -f docker-compose.prod.yml logs -f api-backend
docker compose -f docker-compose.prod.yml logs -f ai-worker
```

### 备份数据库

```bash
docker compose -f docker-compose.prod.yml exec postgres-db pg_dump -U zpulse zpulse > backup_$(date +%Y%m%d).sql
```

### 更新系统

**重要提示**：由于 Git 历史已重置，如果服务器上已有旧代码，请使用"第二步：上传项目代码"中的更新方法。

**后续更新方法（在开发机上构建后传输）：**

#### 在开发机上：

```bash
# 1. 进入项目目录
cd /Users/ethan/Codes/z-pulse

# 2. 拉取最新代码
git pull origin main

# 3. 检查是否需要重新构建外部镜像（通常不需要）
# 如果外部镜像有更新，需要重新导出：
# docker pull postgres:15-alpine redis:7-alpine nginx:latest rachelos/we-mp-rss:latest
# docker save postgres:15-alpine redis:7-alpine nginx:latest rachelos/we-mp-rss:latest -o z-pulse-external-images.tar
# scp z-pulse-external-images.tar root@your-server-ip:/opt/z-pulse/

# 4. 重新构建并导出应用镜像
./scripts/build-and-export-images.sh

# 5. 传输镜像到服务器
scp z-pulse-built-images.tar root@your-server-ip:/opt/z-pulse/
```

#### 在服务器上：

```bash
# 1. 进入项目目录
cd /opt/z-pulse

# 2. 拉取最新代码（获取配置文件和脚本更新）
git pull origin main

# 3. 停止服务
docker compose -f docker-compose.prod.yml down

# 4. 导入新镜像（如果外部镜像有更新，也需要导入）
# docker load -i z-pulse-external-images.tar  # 如果需要
./scripts/import-built-images.sh z-pulse-built-images.tar

# 5. 启动服务
docker compose -f docker-compose.prod.yml up -d

# 6. 查看服务状态
docker compose -f docker-compose.prod.yml ps
```

**注意**：
- 如果只是修改了 `.env` 配置，不需要重新构建镜像，只需重启服务
- 如果修改了代码，需要在开发机上重新构建镜像
- 如果修改了 `NEXT_PUBLIC_API_URL`，需要重新构建前端镜像

## 🐛 常见问题

### 问题：Docker Hub 连接超时

**错误信息**：
```
Error response from daemon: Get "https://registry-1.docker.io/v2/": net/http: request canceled while waiting for connection (Client.Timeout exceeded while awaiting headers)
```

**原因**：在中国大陆访问 Docker Hub 可能很慢或被限制。

**解决方案**：

#### 方案1：配置 Docker 镜像加速器（推荐）

```bash
# 1. 创建或编辑 Docker daemon 配置文件
mkdir -p /etc/docker

# 如果使用阿里云镜像加速器（推荐，速度最快）
# 注意：镜像加速器和容器镜像服务（ACR）是不同的服务
# 访问：https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors
# 登录后查看"镜像加速器"部分（不是"容器镜像服务"）
# 获取的地址格式应该是：https://xxxxx.mirror.aliyuncs.com
# 如果获取的是 personal.cr.aliyuncs.com 格式，那是容器镜像服务，不是镜像加速器
# 将镜像加速器地址放在最前面

cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://您的阿里云专属地址.mirror.aliyuncs.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 2. 重启 Docker 使配置生效（重要！）
systemctl daemon-reload
systemctl restart docker

# 3. 等待 Docker 完全启动（约5秒）
sleep 5

# 4. 验证配置是否生效
docker info | grep -A 10 "Registry Mirrors"
# 应该能看到您配置的镜像地址

# 5. 测试拉取镜像（验证加速器是否工作）
docker pull hello-world
docker rmi hello-world

# 6. 手动拉取所有需要的镜像（避免 compose 超时）
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker pull rachelos/we-mp-rss:latest

# 7. 重新尝试启动服务
cd /opt/z-pulse
docker compose up -d
```

**重要提示**：
- 如果配置后仍然超时，请检查 `/etc/docker/daemon.json` 文件格式是否正确（JSON 格式）
- 确保重启 Docker 后配置生效：`docker info | grep "Registry Mirrors"`
- **如果镜像加速器配置了但仍然无法拉取镜像**，可能是以下原因：
  1. 阿里云镜像地址格式错误（应该是 `https://xxxxx.mirror.aliyuncs.com`，不是 `personal.cr.aliyuncs.com`）
  2. 镜像加速器服务暂时不可用
  3. 网络防火墙阻止了连接

**解决方案**：

如果镜像加速器不工作，可以尝试以下方法：

```bash
# 方法1：移除可能有问题的阿里云地址，只使用公共镜像源
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF
systemctl daemon-reload
systemctl restart docker
sleep 5
docker pull hello-world

# 方法2：如果方法1仍然失败，检查网络连接
ping docker.mirrors.ustc.edu.cn
curl -I https://docker.mirrors.ustc.edu.cn

# 方法3：使用阿里云容器镜像服务的正确地址格式
# 访问：https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors
# 获取的地址应该是：https://xxxxx.mirror.aliyuncs.com（不是 personal.cr.aliyuncs.com）
# 如果获取的地址格式不对，可以暂时移除，只使用公共镜像源

# 方法4：如果所有镜像加速器都不工作，使用代理或从其他环境导入镜像
```

**如果步骤6中某个镜像拉取失败**：

```bash
# 方法A：增加超时时间后重试
export DOCKER_CLIENT_TIMEOUT=120
export COMPOSE_HTTP_TIMEOUT=120
docker pull rachelos/we-mp-rss:latest

# 方法B：检查镜像加速器是否真的在工作
# 如果 docker pull hello-world 成功，但 pull rachelos/we-mp-rss 失败
# 可能是该镜像不在镜像加速器的缓存中
# 可以尝试多次重试，或者使用代理

# 方法C：从其他环境导入镜像（如果有）
# 在可以访问 Docker Hub 的机器上：
docker save rachelos/we-mp-rss:latest -o werss.tar
# 传输到服务器后：
docker load -i werss.tar
```

#### 方案2：手动拉取镜像（如果方案1仍然失败）

如果镜像加速器配置后仍然无法拉取，可以尝试以下方法：

```bash
# 方法A：使用代理拉取（如果有代理）
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker pull rachelos/we-mp-rss:latest
unset HTTP_PROXY HTTPS_PROXY

# 方法B：从其他环境导出镜像并导入
# 在可以访问 Docker Hub 的机器上：
docker save postgres:15-alpine redis:7-alpine nginx:latest rachelos/we-mp-rss:latest -o images.tar
# 传输到服务器后：
docker load -i images.tar

# 方法C：使用阿里云容器镜像服务同步（推荐）
# 1. 在阿里云控制台创建镜像仓库
# 2. 将 Docker Hub 镜像同步到阿里云
# 3. 修改 docker-compose.yml 中的镜像地址为阿里云地址
```

#### 方案3：修复镜像加速器配置（如果配置了但无法工作）

如果 `docker info` 显示镜像加速器已配置，但 `docker pull` 仍然失败：

```bash
# 1. 检查阿里云镜像地址格式是否正确
# 正确的格式应该是：https://xxxxx.mirror.aliyuncs.com
# 错误的格式：https://xxxxx.personal.cr.aliyuncs.com（这种格式可能不工作）

# 2. 如果阿里云地址格式不对，移除它，只使用公共镜像源
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 3. 重启 Docker
systemctl daemon-reload
systemctl restart docker
sleep 5

# 4. 测试网络连接
ping -c 3 docker.mirrors.ustc.edu.cn
curl -I https://docker.mirrors.ustc.edu.cn

# 5. 测试拉取镜像
docker pull hello-world

# 6. 如果仍然失败，检查防火墙
# CentOS/RHEL:
firewall-cmd --list-all
# Ubuntu/Debian:
ufw status

# 7. 如果网络正常但镜像加速器不工作，可能需要使用代理
# 或者从其他环境导入镜像（见方案4）
```

#### 方案4：从开发机导入镜像（推荐，最可靠）

**这是本部署方案的标准流程，已在"第四步：构建和部署镜像"中说明。**

如果遇到 Docker Hub 连接超时，请按照部署流程，在开发机上拉取并导出外部镜像：

```bash
# 在开发机上（已包含在部署流程中）：
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker pull rachelos/we-mp-rss:latest

# 导出镜像
docker save postgres:15-alpine redis:7-alpine nginx:latest rachelos/we-mp-rss:latest -o z-pulse-external-images.tar

# 传输到服务器
scp z-pulse-external-images.tar root@your-server-ip:/opt/z-pulse/

# 在服务器上导入镜像
cd /opt/z-pulse
docker load -i z-pulse-external-images.tar

# 验证镜像已导入
docker images | grep -E "postgres|redis|nginx|we-mp-rss"

# 然后启动服务（不会再去拉取镜像）
docker compose -f docker-compose.prod.yml up -d
```

#### 方案3：使用代理（如果有）

```bash
# 配置 Docker 使用代理
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/http-proxy.conf <<EOF
[Service]
Environment="HTTP_PROXY=http://proxy.example.com:8080"
Environment="HTTPS_PROXY=http://proxy.example.com:8080"
Environment="NO_PROXY=localhost,127.0.0.1"
EOF

systemctl daemon-reload
systemctl restart docker
```

### 问题：构建镜像失败

如果构建镜像时遇到问题：

```bash
# 1. 检查网络连接（开发机上）
# 确保可以访问 Docker Hub 和 npm registry

# 2. 清理 Docker 缓存后重试
docker system prune -a

# 3. 单独构建镜像进行调试
# 后端镜像
docker build -t zpulse-backend:latest -f backend/Dockerfile .

# 前端镜像
docker build -t zpulse-frontend:latest --build-arg NEXT_PUBLIC_API_URL=https://your-domain.com/api -f frontend/Dockerfile frontend/

# 4. 如果构建成功，手动导出
docker save zpulse-backend:latest zpulse-frontend:latest -o z-pulse-built-images.tar
```

## 相关文档

- [Docker安装指南](./docker-install.md)
- [服务重启指南](./restart.md)
- [故障排除](../troubleshooting/README.md)

