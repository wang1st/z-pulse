# Docker 镜像加速器问题排查

## 问题：镜像加速器配置了但无法拉取镜像

### 症状

```bash
docker pull hello-world
Error response from daemon: Get "https://registry-1.docker.io/v2/": net/http: request canceled while waiting for connection
```

即使 `docker info` 显示镜像加速器已配置，仍然无法拉取镜像。

### 原因分析

1. **阿里云镜像地址格式错误**
   - 错误格式：`https://xxxxx.personal.cr.aliyuncs.com`
   - 正确格式：`https://xxxxx.mirror.aliyuncs.com`

2. **镜像加速器服务暂时不可用**
3. **网络防火墙阻止连接**
4. **Docker 配置未完全生效**

## 解决方案

### 方案1：修复镜像加速器配置（推荐）

```bash
# 1. 移除可能有问题的阿里云地址，只使用公共镜像源
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 2. 重启 Docker
systemctl daemon-reload
systemctl restart docker
sleep 5

# 3. 验证配置
docker info | grep -A 10 "Registry Mirrors"

# 4. 测试网络连接
ping -c 3 docker.mirrors.ustc.edu.cn
curl -I https://docker.mirrors.ustc.edu.cn

# 5. 测试拉取镜像
docker pull hello-world

# 6. 如果 hello-world 成功，尝试拉取项目所需的所有镜像
# 可以使用项目提供的脚本（推荐）
cd /opt/z-pulse
chmod +x scripts/pull-images-server.sh
./scripts/pull-images-server.sh

# 或者手动拉取
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker pull rachelos/we-mp-rss:latest
```

### 方案2：从其他环境导入镜像（最可靠，强烈推荐）

如果镜像加速器完全不工作（出现 "connection refused" 或 "timeout"），从可以访问 Docker Hub 的环境导入镜像是最可靠的方法。

#### 方法A：使用脚本（推荐）

项目提供了便捷的导出/导入脚本：

**在本地开发机（可以访问 Docker Hub）上：**

```bash
# 1. 进入项目目录
cd /path/to/z-pulse

# 2. 运行导出脚本（会自动检查并拉取缺失的镜像）
./scripts/export-images.sh

# 3. 脚本会自动：
#    - 检查所需镜像是否存在
#    - 拉取缺失的镜像
#    - 导出所有镜像到 z-pulse-images.tar

# 4. 传输到服务器（替换为您的服务器IP）
scp z-pulse-images.tar root@your-server-ip:/opt/z-pulse/
```

**在服务器上：**

```bash
# 1. 进入项目目录
cd /opt/z-pulse

# 2. 运行导入脚本
chmod +x scripts/import-images.sh
./scripts/import-images.sh z-pulse-images.tar

# 3. 脚本会自动：
#    - 导入所有镜像
#    - 验证镜像是否完整
#    - 显示下一步操作提示

# 4. 启动服务（此时不会再去拉取镜像，因为镜像已存在）
docker compose up -d

# 5. 查看服务状态
docker compose ps
```

#### 方法B：手动操作

**在本地开发机（可以访问 Docker Hub）上：**

```bash
# 1. 确保所有镜像都已拉取
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker pull rachelos/we-mp-rss:latest

# 2. 验证镜像存在
docker images | grep -E "postgres|redis|nginx|we-mp-rss"

# 3. 导出所有镜像到一个文件
docker save \
  postgres:15-alpine \
  redis:7-alpine \
  nginx:latest \
  rachelos/we-mp-rss:latest \
  -o z-pulse-images.tar

# 4. 检查文件大小（应该有几个GB）
ls -lh z-pulse-images.tar

# 5. 传输到服务器（替换为您的服务器IP和路径）
scp z-pulse-images.tar root@your-server-ip:/opt/z-pulse/

# 如果文件很大，可以使用压缩传输（在服务器上解压）
# tar czf z-pulse-images.tar.gz z-pulse-images.tar
# scp z-pulse-images.tar.gz root@your-server-ip:/opt/z-pulse/
```

**在服务器上：**

```bash
# 1. 进入项目目录
cd /opt/z-pulse

# 2. 如果传输的是压缩文件，先解压
# gunzip z-pulse-images.tar.gz

# 3. 导入镜像（可能需要几分钟）
docker load -i z-pulse-images.tar

# 4. 验证镜像已导入
docker images | grep -E "postgres|redis|nginx|we-mp-rss"
# 应该能看到：
# postgres              15-alpine    ...
# redis                 7-alpine     ...
# nginx                 latest       ...
# rachelos/we-mp-rss    latest       ...

# 5. 启动服务（此时不会再去拉取镜像，因为镜像已存在）
docker compose up -d

# 6. 查看服务状态
docker compose ps
```

**注意事项**：
- 镜像文件可能很大（几个GB），传输需要一些时间
- 如果网络不稳定，可以使用 `rsync` 代替 `scp`（支持断点续传）
- 导入镜像后，`docker compose up -d` 不会再去拉取镜像

### 方案2.5：手动拉取镜像（如果镜像加速器部分工作）

如果 `hello-world` 可以拉取，但 `docker compose up -d` 时某些镜像拉取失败，可以尝试手动逐个拉取：

```bash
# 1. 进入项目目录
cd /opt/z-pulse

# 2. 手动拉取所有需要的外部镜像
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker pull rachelos/we-mp-rss:latest

# 3. 验证镜像已存在
docker images | grep -E "postgres|redis|nginx|we-mp-rss"
# 应该能看到：
# postgres              15-alpine    ...
# redis                 7-alpine     ...
# nginx                 latest       ...
# rachelos/we-mp-rss    latest       ...

# 4. 如果所有镜像都已存在，启动服务（此时不会再去拉取镜像）
docker compose up -d

# 5. 查看服务状态
docker compose ps

# 6. 如果某些服务启动失败，查看日志
docker compose logs [service-name]
```

**为什么需要手动拉取？**
- `docker compose up -d` 会并行拉取多个镜像，可能触发超时
- 某些镜像（如 `rachelos/we-mp-rss:latest`）可能无法通过镜像加速器拉取
- 先手动拉取可以确保所有镜像存在，避免启动时失败

**如果手动拉取仍然失败：**
- 使用方案2（从本地开发机导入镜像）是最可靠的方法

### 方案3：使用代理（如果有）

如果您的服务器有代理，可以配置 Docker 使用代理：

```bash
# 1. 创建代理配置文件
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/http-proxy.conf <<EOF
[Service]
Environment="HTTP_PROXY=http://your-proxy:port"
Environment="HTTPS_PROXY=http://your-proxy:port"
Environment="NO_PROXY=localhost,127.0.0.1,docker-registry.example.com"
EOF

# 2. 重启 Docker
systemctl daemon-reload
systemctl restart docker
sleep 5

# 3. 测试拉取镜像
docker pull hello-world
```

### 方案4：检查网络和防火墙

如果出现 "connection refused" 错误，可能是防火墙阻止了连接：

```bash
# 1. 检查防火墙状态（CentOS/RHEL）
firewall-cmd --list-all

# 2. 如果需要，允许 HTTPS 连接
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="0.0.0.0/0" port protocol="tcp" port="443" accept'
firewall-cmd --reload

# 3. 检查防火墙状态（Ubuntu/Debian）
ufw status
# 如果需要，允许 HTTPS
ufw allow 443/tcp

# 4. 测试网络连接
ping -c 3 docker.mirrors.ustc.edu.cn
curl -I https://docker.mirrors.ustc.edu.cn
telnet docker.mirrors.ustc.edu.cn 443
```

## 诊断步骤

### 1. 检查 Docker 配置

```bash
# 查看配置文件
cat /etc/docker/daemon.json

# 检查 Docker 是否使用了镜像加速器
docker info | grep -A 10 "Registry Mirrors"
```

### 2. 测试网络连接

```bash
# 测试镜像加速器地址
ping -c 3 docker.mirrors.ustc.edu.cn
curl -I https://docker.mirrors.ustc.edu.cn

# 测试 Docker Hub（应该失败或很慢）
curl -I https://registry-1.docker.io/v2/
```

### 3. 查看 Docker 日志

```bash
# 查看 Docker 服务日志
journalctl -u docker.service -n 50

# 查看 Docker 守护进程日志
tail -f /var/log/docker.log
```

### 4. 测试镜像拉取

```bash
# 测试拉取小镜像
docker pull hello-world

# 如果成功，尝试拉取实际需要的镜像
docker pull postgres:15-alpine
```

## 常见问题

### Q: 为什么配置了镜像加速器，Docker 仍然连接 Docker Hub？

A: 可能的原因：
1. Docker 配置未完全生效（需要重启 Docker）
2. 镜像加速器地址格式错误
3. 镜像加速器服务不可用
4. Docker 在某些情况下会回退到 Docker Hub

**解决方案**：先手动拉取所有镜像，然后再启动服务。

### Q: 阿里云容器镜像服务（ACR）和镜像加速器的区别？

A: 这是两个不同的服务：

**镜像加速器**（推荐用于加速 Docker Hub）：
- 地址格式：`https://xxxxx.mirror.aliyuncs.com`
- 用途：自动加速 Docker Hub 的镜像拉取
- 配置方式：在 `/etc/docker/daemon.json` 中配置 `registry-mirrors`
- 不需要登录，不需要同步镜像
- 直接使用：`docker pull postgres:15-alpine`（会自动通过加速器）

**容器镜像服务（ACR）**：
- 地址格式：`https://xxxxx.cn-hangzhou.personal.cr.aliyuncs.com` 或 `registry.cn-hangzhou.aliyuncs.com`
- 用途：托管自己的镜像仓库
- 需要先登录：`docker login registry.cn-hangzhou.aliyuncs.com`
- 需要先将镜像推送到自己的仓库，然后才能拉取
- 使用方式：`docker pull registry.cn-hangzhou.aliyuncs.com/namespace/image:tag`

**重要**：如果您想加速 Docker Hub 的镜像拉取，应该使用**镜像加速器**，而不是容器镜像服务。

### Q: 如何获取正确的阿里云镜像加速器地址？

A: 
1. 访问：https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors
2. 登录后查看"镜像加速器"部分（不是"容器镜像服务"）
3. 获取格式为 `https://xxxxx.mirror.aliyuncs.com` 的地址
4. 如果获取的是 `personal.cr.aliyuncs.com` 格式，那是容器镜像服务，不是镜像加速器

### Q: 我已经登录了容器镜像服务，为什么还是无法拉取镜像？

A: 容器镜像服务需要您先将镜像推送到自己的仓库。如果您想直接拉取 Docker Hub 的镜像，应该使用镜像加速器，而不是容器镜像服务。

**解决方案**：
1. 使用镜像加速器（推荐）：配置 `/etc/docker/daemon.json` 中的 `registry-mirrors`
2. 或者从其他环境导入镜像（见方案2）

### Q: 为什么 nginx、postgres 等镜像可以拉取，但 rachelos/we-mp-rss 不行？

A: 这是一个常见问题，主要原因包括：

**1. 镜像来源不同**
- `postgres:15-alpine`, `redis:7-alpine`, `nginx:latest` 来自 Docker Hub 的**官方仓库**（`library/`）
- `rachelos/we-mp-rss:latest` 来自 Docker Hub 的**用户仓库**（`rachelos/`）

**2. 镜像加速器的限制**
- 大多数镜像加速器**优先加速官方镜像**（`library/` 命名空间）
- 用户仓库的镜像（如 `username/image`）可能：
  - 不在加速器的缓存中
  - 需要回源到 Docker Hub，导致超时
  - 同步不及时

**3. 镜像大小和复杂度**
- `we-mp-rss` 镜像通常较大（包含 Playwright/Chromium 浏览器），拉取时间更长
- 更容易在网络不稳定时超时

**4. 网络路径不同**
- 官方镜像和用户镜像可能存储在不同的服务器上
- 用户镜像的网络路径可能更复杂，更容易失败

**解决方案**：

1. **多次重试**（如果网络不稳定）：
   ```bash
   # 重试拉取
   docker pull rachelos/we-mp-rss:latest
   ```

2. **使用从本地导入**（最可靠）：
   ```bash
   # 在本地开发机上
   ./scripts/export-images.sh
   scp z-pulse-images.tar root@server:/opt/z-pulse/
   
   # 在服务器上
   ./scripts/import-images.sh z-pulse-images.tar
   ```

3. **检查镜像是否存在**：
   ```bash
   # 在浏览器中访问，确认镜像存在
   https://hub.docker.com/r/rachelos/we-mp-rss
   ```

4. **使用代理**（如果有）：
   ```bash
   # 配置 Docker 使用代理（见方案3）
   ```

## 相关文档

- [阿里云部署指南](../deployment/aliyun.md)
- [Docker安装指南](../deployment/docker-install.md)

