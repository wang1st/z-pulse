# 解决缺失外部镜像问题

## 问题现象

执行 `docker compose -f docker-compose.prod.yml up -d` 时出现：

```
Error response from daemon: Get "https://registry-1.docker.io/v2/": net/http: request canceled while waiting for connection (Client.Timeout exceeded while awaiting headers)
```

## 原因

服务器无法连接到 Docker Hub 拉取以下外部镜像：
- `postgres:15-alpine`
- `redis:7-alpine`
- `nginx:latest`
- `rachelos/we-mp-rss:latest`

## 快速解决方案

### 方案1：检查并导入外部镜像（如果已有镜像文件）

如果您之前已经导入了外部镜像：

```bash
# 检查哪些镜像已存在
docker images | grep -E "postgres|redis|nginx|we-mp-rss"

# 如果缺少镜像，使用导入脚本
cd /opt/z-pulse
./scripts/import-images.sh z-pulse-images.tar
```

### 方案2：从开发机导出并导入外部镜像（推荐）

**在开发机上：**

```bash
# 1. 拉取所有需要的外部镜像
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker pull rachelos/we-mp-rss:latest

# 2. 导出外部镜像
docker save postgres:15-alpine redis:7-alpine nginx:latest rachelos/we-mp-rss:latest -o z-pulse-external-images.tar

# 3. 传输到服务器
scp z-pulse-external-images.tar root@your-server-ip:/opt/z-pulse/
```

**在服务器上：**

```bash
# 1. 导入外部镜像
cd /opt/z-pulse
docker load -i z-pulse-external-images.tar

# 2. 验证镜像
docker images | grep -E "postgres|redis|nginx|we-mp-rss"

# 3. 启动服务
docker compose -f docker-compose.prod.yml up -d
```

### 方案3：配置镜像加速器

如果镜像加速器已配置但未生效，参考：[Docker 镜像加速器配置](aliyun.md#问题docker-hub-连接超时)

### 方案4：手动拉取（如果网络允许）

```bash
# 尝试逐个拉取（可能需要多次尝试）
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker pull rachelos/we-mp-rss:latest
```

## 验证所有镜像

启动服务前，确保以下镜像都存在：

```bash
# 检查所有必需的镜像
docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "^postgres:15-alpine$|^redis:7-alpine$|^nginx:latest$|^rachelos/we-mp-rss:latest$|^zpulse-backend:latest$|^zpulse-frontend:latest$"
```

应该看到：
- postgres:15-alpine
- redis:7-alpine
- nginx:latest
- rachelos/we-mp-rss:latest
- zpulse-backend:latest
- zpulse-frontend:latest

## 启动服务

所有镜像都存在后：

```bash
docker compose -f docker-compose.prod.yml up -d
```

