# Z-Pulse 部署指南

## 目录

- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [生产环境部署](#生产环境部署)
- [服务配置](#服务配置)
- [监控和日志](#监控和日志)
- [故障排除](#故障排除)

## 环境要求

### 硬件要求

- CPU: 4核心及以上
- 内存: 8GB及以上
- 存储: 100GB及以上（推荐使用SSD）

### 软件要求

- Docker: 20.10+
- Docker Compose: 2.0+
- Python: 3.11+ （如果本地运行）
- PostgreSQL: 15+ （如果本地部署数据库）
- Redis: 7+ （如果本地部署缓存）

## 快速部署

### 1. 克隆项目

```bash
git clone https://gitee.com/wang1st/z-pulse.git
cd z-pulse
```

### 2. 配置环境变量

```bash
cp env.example .env
```

编辑`.env`文件，配置以下必需项：

```env
# 数据库
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_PASSWORD=your_redis_password

# API密钥
API_SECRET_KEY=your_secret_key_for_jwt

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# 邮件服务
SENDGRID_API_KEY=your_sendgrid_api_key
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 初始化数据库

```bash
docker-compose exec api-gateway python scripts/init_db.py
```

### 5. 导入公众号清单

```bash
docker-compose exec collector python scripts/import_accounts.py data/official_accounts.csv
```

### 6. 验证部署

访问以下地址验证服务：

- API文档: http://localhost:8000/api/v1/docs
- MinIO控制台: http://localhost:9001

## 生产环境部署

### 1. 使用外部数据库

推荐使用托管的PostgreSQL服务（如AWS RDS、Azure Database等）：

```env
POSTGRES_HOST=your-db-host.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=zpulse_prod
POSTGRES_USER=zpulse
POSTGRES_PASSWORD=your_strong_password
```

### 2. 使用外部Redis

推荐使用托管的Redis服务（如AWS ElastiCache、Azure Cache等）：

```env
REDIS_HOST=your-redis-host.cache.amazonaws.com
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
```

### 3. 配置对象存储

推荐使用云对象存储（如AWS S3、Azure Blob等）：

```env
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
MINIO_BUCKET=zpulse-prod
MINIO_SECURE=true
```

### 4. 配置反向代理

使用Nginx作为反向代理：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. 配置HTTPS

使用Let's Encrypt获取免费SSL证书：

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 6. 配置日志轮转

创建`/etc/logrotate.d/zpulse`:

```
/path/to/z-pulse/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        docker-compose restart api-gateway collector ai-processor email-sender
    endscript
}
```

## 服务配置

### API网关配置

```env
API_HOST=0.0.0.0
API_PORT=8000
API_CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com
```

### 采集服务配置

```env
COLLECTOR_INTERVAL_HOURS=6  # 采集间隔（小时）
COLLECTOR_MAX_WORKERS=5     # 最大并发采集数
```

### AI处理服务配置

```env
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

### 邮件服务配置

```env
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=your_key
EMAIL_FROM=noreply@your-domain.com
EMAIL_FROM_NAME=Your App Name
```

## 监控和日志

### 日志查看

查看所有服务日志：
```bash
docker-compose logs -f
```

查看特定服务日志：
```bash
docker-compose logs -f api-gateway
docker-compose logs -f collector
docker-compose logs -f ai-processor
docker-compose logs -f email-sender
```

### 健康检查

```bash
# API网关
curl http://localhost:8000/health

# 数据采集服务
curl http://localhost:8001/

# AI处理服务
curl http://localhost:8002/

# 邮件服务
curl http://localhost:8003/
```

### Prometheus监控

访问Prometheus: http://localhost:9090

### Grafana仪表板

访问Grafana: http://localhost:3000

默认用户名密码: admin/admin

## 故障排除

### 数据库连接失败

1. 检查数据库服务是否运行：
```bash
docker-compose ps postgres
```

2. 检查数据库连接配置：
```bash
docker-compose exec postgres psql -U zpulse -d zpulse
```

### Redis连接失败

1. 检查Redis服务：
```bash
docker-compose ps redis
```

2. 测试Redis连接：
```bash
docker-compose exec redis redis-cli ping
```

### 采集任务失败

1. 查看Celery worker日志：
```bash
docker-compose logs -f celery-worker
```

2. 检查任务队列：
```bash
docker-compose exec redis redis-cli
> LLEN celery
```

### AI处理超时

1. 增加OpenAI超时时间
2. 检查API密钥是否有效
3. 查看AI处理服务日志

### 邮件发送失败

1. 检查SendGrid API密钥
2. 验证邮箱地址格式
3. 查看邮件服务日志

## 备份和恢复

### 数据库备份

```bash
# 备份
docker-compose exec postgres pg_dump -U zpulse zpulse > backup.sql

# 恢复
docker-compose exec -T postgres psql -U zpulse zpulse < backup.sql
```

### 完整备份

```bash
./scripts/backup.sh
```

### 恢复数据

```bash
./scripts/restore.sh backup-2024-01-01.tar.gz
```

## 性能优化

### 数据库优化

1. 创建必要的索引
2. 定期运行VACUUM
3. 调整PostgreSQL配置

### Redis优化

1. 配置合适的maxmemory
2. 使用Redis持久化
3. 监控内存使用

### 应用优化

1. 使用连接池
2. 启用缓存
3. 优化查询
4. 使用异步处理

## 安全建议

1. 使用强密码
2. 定期更新密钥
3. 启用HTTPS
4. 配置防火墙
5. 定期备份
6. 监控异常访问
7. 及时更新依赖

