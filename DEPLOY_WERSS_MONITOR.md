# WeRSS Token监控系统部署指南

## 功能概述

自动监控微信公众号登录token状态，在即将过期时发送邮件提醒给管理员，邮件包含直接扫码链接（无需登录后台）。

## 部署步骤

### 1. 本地开发环境

#### 1.1 创建数据库表

```bash
cd backend/app/tools
python3 create_one_time_tokens_table.py
```

预期输出：
```
✅ one_time_tokens table created successfully
```

#### 1.2 更新配置（可选）

检查 `.env` 文件，确认管理员邮箱配置：
```bash
ADMIN_EMAILS=["paprio@qq.com"]
```

#### 1.3 测试监控功能

```bash
cd backend/app/workers
python3 werss_token_monitor.py --once
```

预期输出：
- 如果token健康：`All tokens are healthy`
- 如果有即将过期的token：会发送邮件到 `ADMIN_EMAILS`

#### 1.4 启动后端API

```bash
cd backend
python3 -m app.main
```

#### 1.5 测试前端页面

访问：`http://localhost:3000/we-rss-relogin?token=test_token`

应该看到令牌验证页面

### 2. 阿里云服务器部署

#### 2.1 上传文件到服务器

```bash
# 本地运行
scp backend/app/services/werss_monitor.py root@your-server:/root/z-pulse/backend/app/services/
scp backend/app/routers/werss.py root@your-server:/root/z-pulse/backend/app/routers/
scp backend/app/workers/werss_token_monitor.py root@your-server:/root/z-pulse/backend/app/workers/
scp backend/app/tools/create_one_time_tokens_table.py root@your-server:/root/z-pulse/backend/app/tools/
scp frontend/app/we-rss-relogin/page.tsx root@your-server:/root/z-pulse/frontend/app/we-rss-relogin/page.tsx
scp shared/database/models.py root@your-server:/root/z-pulse/shared/database/models.py
```

#### 2.2 服务器上创建数据库表

```bash
# SSH登录服务器
ssh root@your-server

# 创建表
cd /root/z-pulse/backend/app/tools
python3 create_one_time_tokens_table.py
```

#### 2.3 更新主应用（注册新路由）

编辑 `/root/z-pulse/backend/app/main.py`：

```python
# 在imports部分添加：
from .routers import reports, subscriptions, health, auth, admin, werss

# 在注册路由部分添加：
app.include_router(werss.router, tags=["WeRSS"])
```

#### 2.4 重启后端服务

```bash
cd /root/z-pulse
docker-compose restart backend-api
```

#### 2.5 测试API

```bash
curl "http://localhost:8000/api/werss-relogin/verify?token=test_token"
```

应该返回JSON响应

#### 2.6 设置定时任务

```bash
cd /root/z-pulse/backend/app/tools
bash setup_werss_monitor_cron.sh
```

或者手动添加crontab：

```bash
# 编辑crontab
crontab -e

# 添加以下行（每天早上9点检查）
0 9 * * * /usr/bin/python3 /root/z-pulse/backend/app/workers/werss_token_monitor.py --once >> /var/log/werss_monitor.log 2>&1
```

#### 2.7 查看日志

```bash
# 实时查看监控日志
tail -f /var/log/werss_monitor.log

# 查看最近10次运行结果
grep "WeRSS Token Monitor" /var/log/werss_monitor.log | tail -10
```

### 3. Docker环境配置

如果使用Docker部署，需要确保：

1. **数据库持久化**：确保PostgreSQL数据卷已挂载
2. **环境变量**：`ADMIN_EMAILS` 已在 `.env` 或 `docker-compose.yml` 中配置
3. **定时任务**：可以选择：
   - 在宿主机上运行cron（调用容器内脚本）
   - 使用Docker容器内的celery beat
   - 使用外部定时任务服务（如GitHub Actions）

#### 示例：在宿主机上运行cron

```bash
# crontab
0 9 * * * docker exec zpulse-backend-api python /app/backend/app/workers/werss_token_monitor.py --once
```

## 验证部署

### 1. 测试Token监控

```bash
# 手动运行一次监控
python3 backend/app/workers/werss_token_monitor.py --once

# 检查输出
# 应该看到： "Starting WeRSS token monitoring..."
# 应该看到： "All tokens are healthy" 或 "Found X tokens expiring soon"
```

### 2. 测试邮件提醒（模拟token即将过期）

编辑 `backend/app/services/werss_monitor.py`：

```python
# 临时修改：将24小时改为1000小时（强制触发）
if remaining.total_seconds() < 1000 * 3600:  # 原来是 24 * 3600
```

运行监控，应该收到邮件。

### 3. 测试前端页面

1. 从邮件中获取链接
2. 点击链接
3. 应该看到微信公众号重新登录页面
4. 点击"打开扫码页面"
5. 完成扫码后点击"已完成登录"

## 监控和维护

### 日志位置

- Token监控日志：`/var/log/werss_monitor.log`
- API日志：Docker容器日志或应用日志文件
- 邮件发送日志：应用日志（搜索 "email-service"）

### 定期检查

建议每月检查一次：

```bash
# 检查定时任务是否正常运行
grep "WeRSS Token Monitor" /var/log/werss_monitor.log | tail -30

# 检查数据库中是否有未清理的过期token
# （可选：可以添加清理脚本定期删除已使用/过期的token）
```

### 故障排查

#### 问题：没有收到邮件

**检查步骤：**
1. 检查定时任务是否运行：`grep /var/log/cron` 或 `grep /var/log/syslog`
2. 检查监控脚本日志：`tail /var/log/werss_monitor.log`
3. 检查邮件服务配置：`ADMIN_EMAILS` 和 `EMAIL_PROVIDER`
4. 检查WeRSS API是否可访问

#### 问题：前端页面无法访问

**检查步骤：**
1. 确认后端API已重启：`docker-compose ps backend-api`
2. 确认路由已注册：访问 `/docs` 查看"WeRSS"标签
3. 检查CORS配置

#### 问题：token验证失败

**可能原因：**
- Token已过期（24小时有效期）
- Token已被使用（一次性）
- 数据库连接问题

**解决方法：**
- 等待下次监控运行自动生成新token
- 或手动触发监控：`python3 werss_token_monitor.py --once`

## 文件清单

### 后端文件

- `backend/app/services/werss_monitor.py` - Token监控核心服务
- `backend/app/routers/werss.py` - WeRSS API路由
- `backend/app/workers/werss_token_monitor.py` - 监控Worker
- `backend/app/tools/create_one_time_tokens_table.py` - 数据库迁移脚本
- `backend/app/tools/setup_werss_monitor_cron.sh` - Cron设置脚本

### 前端文件

- `frontend/app/we-rss-relogin/page.tsx` - 扫码登录页面

### 数据库模型

- `shared/database/models.py` - 添加了 `OneTimeToken` 模型

### 配置文件

- `shared/config/settings.py` - 添加了 `ADMIN_EMAILS` 配置
- `.env` - 确认 `ADMIN_EMAILS` 已配置

## 安全建议

1. **Token安全**：
   - Token使用 `secrets.token_urlsafe(32)` 生成（64字符，足够安全）
   - 一次性使用，自动标记为已使用
   - 24小时有效期

2. **访问控制**：
   - 验证API不要求用户登录（根据设计）
   - 但通过token验证确保只有收到邮件的人才能访问

3. **日志审计**：
   - 记录所有token生成和验证事件
   - 定期检查异常访问

## 后续优化建议

1. **自动化清理**：添加脚本定期删除已使用/过期的token
2. **监控面板**：在管理后台添加token状态监控页面
3. **更多通知渠道**：支持钉钉、企业微信等webhook通知
4. **Token刷新提醒**：提前3天、1天、1小时分级提醒
