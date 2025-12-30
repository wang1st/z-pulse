# Docker 构建内存不足（OOM）问题排查

## 问题：构建时出现 exit code: 137

### 症状

```bash
=> ERROR [api-backend 3/9] RUN apt-get update && apt-get install -y ...
Killed
failed to solve: process "/bin/sh -c apt-get update && apt-get install -y ..." did not complete successfully: exit code: 137
```

### 原因分析

**退出代码 137 = 128 + 9**，表示进程被 SIGKILL (9) 信号终止，通常是因为：

1. **内存不足（OOM - Out of Memory）**
   - 服务器可用内存不足
   - Docker 构建时内存占用过高
   - 系统 OOM killer 杀死了进程

2. **Docker 构建内存限制**
   - Docker 默认可能没有足够的内存用于构建
   - 构建大型镜像时内存需求高

3. **并发构建**
   - 多个服务同时构建会消耗更多内存

## 解决方案

### 方案1：优化 Dockerfile（推荐）

已优化 `backend/Dockerfile`，使用 `--no-install-recommends` 减少包数量：

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # ... packages ...
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean
```

### 方案2：检查服务器内存

```bash
# 查看服务器内存使用情况
free -h

# 查看系统日志中的 OOM 记录
dmesg | grep -i "out of memory"
journalctl -k | grep -i "out of memory"

# 查看 Docker 内存使用
docker stats
```

### 方案3：增加交换空间（Swap）

如果服务器内存不足，可以临时增加交换空间：

```bash
# 创建 2GB 交换文件
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久启用（可选）
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 验证
free -h
```

### 方案4：限制并发构建

一次只构建一个服务，避免内存竞争：

```bash
# 先构建 api-backend
docker compose build api-backend

# 再构建其他服务
docker compose build ingestion-worker
docker compose build ai-worker
docker compose build frontend-web

# 最后启动所有服务
docker compose up -d
```

### 方案5：使用 Docker BuildKit 并设置内存限制

```bash
# 启用 BuildKit
export DOCKER_BUILDKIT=1

# 设置构建内存限制（例如 2GB）
export BUILDKIT_STEP_LOG_MAX_SIZE=10485760
export BUILDKIT_STEP_LOG_MAX_SPEED=10485760

# 构建时指定内存限制
docker build --memory=2g -t zpulse-backend -f ./backend/Dockerfile .
```

### 方案6：在本地构建镜像，然后推送到服务器

如果服务器内存确实不足，可以在本地开发机构建镜像，然后导出导入：

```bash
# 在本地开发机上
cd /path/to/z-pulse

# 构建所有需要构建的镜像
docker compose build

# 导出构建的镜像
docker save \
  zpulse-frontend:latest \
  -o z-pulse-built-images.tar

# 传输到服务器
scp z-pulse-built-images.tar root@server:/opt/z-pulse/

# 在服务器上导入
docker load -i z-pulse-built-images.tar
```

## 诊断步骤

### 1. 检查内存使用

```bash
# 查看当前内存使用
free -h

# 查看内存使用详情
cat /proc/meminfo

# 查看 OOM 记录
dmesg | tail -50 | grep -i "killed\|oom"
```

### 2. 检查 Docker 资源使用

```bash
# 查看 Docker 系统信息
docker system df

# 查看运行中的容器资源使用
docker stats --no-stream

# 清理未使用的资源
docker system prune -a
```

### 3. 监控构建过程

```bash
# 在另一个终端监控内存
watch -n 1 free -h

# 查看系统负载
top
htop
```

## 预防措施

1. **优化 Dockerfile**
   - 使用 `--no-install-recommends` 减少包数量
   - 及时清理 apt 缓存
   - 使用多阶段构建

2. **合理分配资源**
   - 确保服务器有足够内存（建议至少 2GB 可用）
   - 配置适当的交换空间

3. **分批构建**
   - 不要同时构建所有服务
   - 先构建基础镜像，再构建应用镜像

## 问题2：网络连接失败（exit code: 100）

### 症状

```bash
W: Failed to fetch http://deb.debian.org/debian/dists/trixie/main/binary-amd64/Packages
Unable to connect to deb.debian.org:http
E: Unable to locate package gcc
failed to solve: ... exit code: 100
```

### 原因分析

服务器在中国，无法访问或访问 Debian 官方源（`deb.debian.org`）很慢，导致构建失败。

### 解决方案

**已优化 Dockerfile**：自动配置使用阿里云 Debian 镜像源。

如果仍然失败，可以手动验证：

```bash
# 在构建时查看镜像源配置
docker build --progress=plain -t test -f ./backend/Dockerfile . 2>&1 | grep -i "mirror\|source"

# 或者进入容器检查
docker run --rm python:3.11-slim cat /etc/apt/sources.list
```

**备选方案**：如果阿里云镜像也不可用，可以尝试其他国内镜像：

```dockerfile
# 使用清华大学镜像
sed -i 's|http://deb.debian.org|http://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list

# 或使用中科大镜像
sed -i 's|http://deb.debian.org|http://mirrors.ustc.edu.cn|g' /etc/apt/sources.list
```

## 相关文档

- [Docker 构建优化最佳实践](https://docs.docker.com/build/building/best-practices/)
- [Docker 内存限制](https://docs.docker.com/config/containers/resource_constraints/#memory)
- [Debian 镜像源列表](https://www.debian.org/mirror/list)

