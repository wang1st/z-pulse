# we-mp-rss 集成指南

## 架构设计

### 职责分离

```
┌──────────────────────────────────────────────────────┐
│                  Z-Pulse System                      │
│                                                      │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ API Gateway│  │AI Processor│  │ Email Sender │  │
│  └────┬───────┘  └────┬───────┘  └──────┬───────┘  │
│       │               │                  │          │
│  ┌────▼───────────────▼──────────────────▼───┐     │
│  │         Sync Service (同步层)             │     │
│  │   - 从we-mp-rss拉取数据                   │     │
│  │   - 数据清洗和标准化                      │     │
│  │   - 触发AI处理                            │     │
│  └───────────────┬───────────────────────────┘     │
│                  │                                  │
│  ┌───────────────▼────────────────┐                │
│  │      PostgreSQL Database       │                │
│  └────────────────────────────────┘                │
└──────────────────────────────────────────────────────┘
                    ▲
                    │ HTTP/RSS
                    │
┌───────────────────┴────────────────────────────────┐
│              we-mp-rss (采集层)                     │
│  - 微信公众号爬虫                                   │
│  - 定时更新文章                                     │
│  - 生成RSS订阅                                      │
│  - 提供REST API                                     │
│  - 独立部署和维护                                   │
└────────────────────────────────────────────────────┘
```

### 为什么这样设计？

1. **职责单一**: we-mp-rss专注于"脏活累活"（与微信交互）
2. **解耦合**: 两个系统可以独立开发、部署和升级
3. **容错性**: we-mp-rss故障不影响Z-Pulse核心功能
4. **可替换**: 未来可以替换为其他采集方案
5. **专业性**: 使用成熟的开源项目，避免重复造轮子

## 部署 we-mp-rss

### 方式一：使用Docker Compose（推荐）

```bash
# 1. 创建网络（如果不存在）
docker network create zpulse-network

# 2. 启动we-mp-rss
docker-compose -f docker-compose.werss.yml up -d

# 3. 访问Web UI
open http://localhost:3000
```

### 方式二：独立部署

```bash
# 克隆项目
git clone https://github.com/rachelos/we-mp-rss.git
cd we-mp-rss

# 配置
cp config.example.yaml config.yaml
# 编辑 config.yaml

# 启动
docker-compose up -d
```

## 配置 we-mp-rss

### 1. 添加公众号

通过Web UI添加：
1. 访问 http://localhost:3000
2. 登录（首次访问会创建管理员账号）
3. 点击"添加订阅"
4. 输入公众号名称或微信号
5. 等待采集完成

### 2. 获取订阅ID

每个公众号都有一个唯一的`feed_id`，可以通过：

- Web UI: 在订阅列表中查看
- API: `GET http://localhost:8080/api/feeds`
- RSS URL: `http://localhost:8080/rss/{feed_id}`

### 3. 配置通知（可选）

编辑 `config.yaml`:

```yaml
notice:
  dingding:
    webhook: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
  wechat:
    webhook: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
  feishu:
    webhook: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

## 在 Z-Pulse 中配置

### 1. 环境变量

在 `.env` 文件中添加：

```env
# we-mp-rss配置
WERSS_API_URL=http://we-mp-rss:8001
WERSS_API_TOKEN=your_api_token  # 可选
WERSS_WEB_URL=http://localhost:3000
```

### 2. 导入公众号

修改 `data/official_accounts/example.csv`:

```csv
name,wechat_id,description,level,region,department,werss_feed_id,werss_sync_method
中华人民共和国财政部,mofgov,财政部官方微信公众号,national,全国,财政部,abc123,rss
浙江财政,zjcz-gov,浙江省财政厅官方微信公众号,provincial,浙江省,财政厅,def456,rss
```

字段说明：
- `werss_feed_id`: we-mp-rss中的订阅ID
- `werss_sync_method`: 同步方式（rss或api）

### 3. 导入到数据库

```bash
docker-compose exec api-gateway python scripts/import_accounts.py data/official_accounts/example.csv
```

## 同步数据

### 手动同步

```bash
# 同步单个公众号
curl -X POST http://localhost:8004/sync/account/1

# 同步所有公众号
curl -X POST http://localhost:8004/sync/all
```

### 自动同步

系统会每小时自动同步一次所有公众号。可以在 `services/sync-service/app/tasks.py` 中修改频率：

```python
celery_app.conf.beat_schedule = {
    "sync-all-accounts": {
        "task": "sync.sync_all",
        "schedule": 3600,  # 每小时
    },
}
```

## 数据流程

### 完整流程

```
1. we-mp-rss 采集
   └─> 微信公众号 → we-mp-rss数据库
   
2. Z-Pulse 同步
   └─> we-mp-rss (RSS/API) → sync-service → PostgreSQL
   
3. AI 处理
   └─> PostgreSQL → ai-processor → 更新文章（摘要、分类等）
   
4. 报告生成
   └─> ai-processor → 生成报告 → PostgreSQL
   
5. 邮件发送
   └─> email-sender → 发送报告 → 用户邮箱
```

### 数据同步方式对比

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| RSS | 简单、标准化 | 字段有限 | 大部分场景 |
| API | 完整数据、灵活 | 需要认证 | 需要详细数据 |

推荐使用RSS方式，除非需要阅读数、点赞数等详细统计。

## API接口

### we-mp-rss API

```bash
# 获取订阅列表
GET http://localhost:8080/api/feeds

# 获取文章列表
GET http://localhost:8080/api/feeds/{feed_id}/articles

# 获取文章详情
GET http://localhost:8080/api/articles/{article_id}
```

### Z-Pulse Sync Service API

```bash
# 同步指定公众号
POST http://localhost:8004/sync/account/{account_id}

# 同步所有公众号
POST http://localhost:8004/sync/all

# 获取同步状态
GET http://localhost:8004/sync/status
```

## 监控和运维

### 健康检查

```bash
# we-mp-rss
curl http://localhost:8080/

# sync-service
curl http://localhost:8004/
```

### 查看日志

```bash
# we-mp-rss日志
docker-compose -f docker-compose.werss.yml logs -f

# sync-service日志
docker-compose logs -f sync-service
```

### 数据备份

we-mp-rss使用SQLite，系统会自动备份：

```bash
# 备份位置
./backups/werss_backup_*.db

# 手动备份
docker-compose -f docker-compose.werss.yml exec we-mp-rss \
  cp /app/data/werss.db /app/data/backup.db
```

## 故障排除

### we-mp-rss无法采集

1. 检查网络连接
2. 查看we-mp-rss日志
3. 确认公众号ID正确
4. 尝试手动刷新

### 同步失败

1. 检查WERSS_API_URL配置
2. 确认we-mp-rss服务运行正常
3. 查看sync-service日志
4. 验证feed_id是否正确

### 数据不一致

1. 检查同步时间
2. 对比we-mp-rss和PostgreSQL数据
3. 手动触发同步
4. 检查去重逻辑

## 最佳实践

### 1. 公众号分批导入

```bash
# 先导入少量公众号测试
# 确认工作正常后再批量导入
```

### 2. 监控同步状态

```bash
# 定期检查同步状态
# 设置告警（通过钉钉/企业微信）
```

### 3. 定期备份

```bash
# we-mp-rss数据
# PostgreSQL数据
# 配置文件
```

### 4. 性能优化

- 调整同步频率
- 限制并发数
- 使用缓存
- 定期清理旧数据

## 参考资源

- [we-mp-rss GitHub](https://github.com/rachelos/we-mp-rss)
- [we-mp-rss 文档](https://werss.csol.store)
- [RSS规范](https://www.rssboard.org/rss-specification)

