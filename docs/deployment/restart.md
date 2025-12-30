# Docker 服务重启指南

## 系统重启后重启所有服务

### 方法1：使用 Docker Compose（推荐）

```bash
# 进入项目目录
cd /path/to/z-pulse

# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看服务日志
docker compose logs -f
```

### 方法2：重启特定服务

```bash
# 重启单个服务
docker compose restart <service-name>

# 例如：重启API后端
docker compose restart api-backend

# 重启前端
docker compose restart frontend-web
```

### 方法3：完全重建并启动

如果遇到问题，可以完全重建：

```bash
# 停止所有服务
docker compose down

# 重新构建并启动
docker compose up -d --build

# 或者只重建特定服务
docker compose up -d --build api-backend
```

## 常用命令

### 查看服务状态
```bash
docker compose ps
```

### 查看所有服务日志
```bash
docker compose logs -f
```

### 查看特定服务日志
```bash
docker compose logs -f api-backend
docker compose logs -f frontend-web
docker compose logs -f ingestion-worker
docker compose logs -f ai-worker
```

### 停止所有服务
```bash
docker compose down
```

### 停止并删除所有数据（谨慎使用）
```bash
docker compose down -v
```

## 服务列表

当前系统包含以下服务：

1. **postgres-db** - PostgreSQL 数据库
2. **redis** - Redis 缓存
3. **api-backend** - FastAPI 后端服务
4. **frontend-web** - Next.js 前端服务
5. **rss-bridge** - we-mp-rss RSS 服务
6. **ingestion-worker** - 数据采集工作进程
7. **ai-worker** - AI 报告生成工作进程
8. **reverse-proxy** - Nginx 反向代理

## 检查服务健康状态

```bash
# 检查所有服务状态
docker compose ps

# 检查特定服务是否健康
docker compose ps | grep healthy

# 检查服务端口
docker compose ps | grep -E "NAME|PORTS"
```

## 故障排查

### 如果服务无法启动

1. **检查 Docker 是否运行**
   ```bash
   docker ps
   ```

2. **检查服务日志**
   ```bash
   docker compose logs <service-name>
   ```

3. **检查端口占用**
   ```bash
   lsof -i :3000  # 前端
   lsof -i :8000  # API
   lsof -i :5432  # PostgreSQL
   ```

4. **重启特定服务**
   ```bash
   docker compose restart <service-name>
   ```

### 如果数据库连接失败

```bash
# 检查数据库服务
docker compose ps postgres-db

# 查看数据库日志
docker compose logs postgres-db

# 重启数据库
docker compose restart postgres-db
```

## 设置开机自动启动（可选）

### macOS 使用 launchd

创建 `~/Library/LaunchAgents/com.zpulse.docker.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zpulse.docker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/docker</string>
        <string>compose</string>
        <string>-f</string>
        <string>/path/to/z-pulse/docker-compose.yml</string>
        <string>up</string>
        <string>-d</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/z-pulse</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
```

然后加载：
```bash
launchctl load ~/Library/LaunchAgents/com.zpulse.docker.plist
```

### 或者使用 Docker Desktop 设置

在 Docker Desktop 设置中启用 "Start Docker Desktop when you log in"

### Linux 使用 systemd

创建 `/etc/systemd/system/zpulse.service`:

```ini
[Unit]
Description=Z-Pulse Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/z-pulse
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
systemctl enable zpulse.service
systemctl start zpulse.service
```

## 快速启动脚本

创建 `start.sh`:

```bash
#!/bin/bash
cd /path/to/z-pulse
docker compose up -d
echo "等待服务启动..."
sleep 5
docker compose ps
```

使脚本可执行：
```bash
chmod +x start.sh
```

然后运行：
```bash
./start.sh
```

## 相关文档

- [Docker安装指南](./docker-install.md)
- [故障排除](../troubleshooting/README.md)

