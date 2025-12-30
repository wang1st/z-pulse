# 采集状态检查指南

## 如何查看采集进程是否在运行

### 1. 检查容器状态

```bash
# 查看所有工作节点状态
docker compose ps | grep -E "(ingest|worker)"

# 应该看到：
# zpulse-ingest-worker   Up X hours
# zpulse-ai-worker       Up X hours
```

### 2. 查看实时日志

```bash
# 查看 ingestion-worker 的实时日志
docker compose logs -f ingestion-worker

# 或者查看最近50行日志
docker compose logs --tail=50 ingestion-worker
```

### 3. 检查公众号状态

在管理后台的"公众号管理"页面，你可以看到：
- **文章总数** (`total_articles`): 每个公众号采集到的文章数量
- **最后采集时间** (`last_collection_time`): 最后一次成功采集的时间

### 4. 使用检查脚本

```bash
# 运行状态检查脚本
docker compose exec api-backend python /app/backend/check_collection_status.py
```

这个脚本会显示：
- 公众号总数和活跃数量
- 每个活跃公众号的详细信息
- 文章总数
- 最近采集的文章

### 5. 检查抓取进程是否正常工作

**正常情况下的日志应该显示：**
```
Starting collection for X accounts
Account [公众号名]: X new articles
Collection completed successfully
```

**异常情况：**
- 日志中没有新的采集记录
- 出现大量错误信息
- 最后采集时间超过1小时

## 采集配置

### 采集间隔

默认配置：每30分钟采集一次（`:00` 和 `:30`）

可以通过环境变量修改：
```bash
POLL_INTERVAL=1800  # 秒（30分钟）
INGEST_OFFSET_MINUTES=5  # 错峰时间（避免整点冲突）
```

### 采集时间窗口

系统只会采集指定日期之后的文章：
```bash
MIN_ARTICLE_DATE=2025-12-15  # 最早采集日期
```

## 常见问题

### Q: 为什么没有新文章？

A: 可能的原因：
1. **采集进程未运行**：检查容器状态和日志
2. **公众号没有新文章**：在we-mp-rss中检查
3. **日期过滤**：检查 `MIN_ARTICLE_DATE` 配置
4. **we-mp-rss连接问题**：检查rss-bridge服务状态

### Q: 如何手动触发采集？

A: 在管理后台的"公众号管理"页面，点击"立即采集"按钮。

### Q: 采集速度很慢怎么办？

A: 
1. 检查网络连接
2. 检查we-mp-rss服务状态
3. 调整 `SPAN_INTERVAL`（文章间隔时间）
4. 减少同时采集的公众号数量

### Q: 如何查看某个公众号的采集历史？

A: 在管理后台的"公众号管理"页面，点击公众号名称查看详情。

## 相关文档

- [we-mp-rss故障排除](../troubleshooting/werss.md)
- [管理后台使用指南](./admin.md)

