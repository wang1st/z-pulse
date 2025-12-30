# we-mp-rss 故障排除指南

## 问题：Web UI (localhost:3001) 无法访问

### 症状
- Safari 显示"服务器意外中断了连接"
- curl 返回 "Connection reset by peer"
- 但 API (localhost:8080) 可以访问

### 重要发现
**we-mp-rss 的 Web UI 实际上运行在 8080 端口，而不是 3001！**

正确的访问地址是：`http://localhost:8080`

### 可能原因

1. **Web UI 服务未启动**
   - we-mp-rss 镜像可能只提供 API 服务
   - Web UI 可能需要额外配置

2. **端口映射问题**
   - 容器内服务可能未监听 3000 端口
   - 或服务启动失败

3. **服务仍在初始化**
   - we-mp-rss 首次启动需要下载浏览器驱动
   - 可能需要 2-5 分钟

## 解决方案

### 方案一：通过 API 管理（推荐）

即使 Web UI 无法访问，也可以通过 API 获取和管理订阅：

```bash
# 1. 获取所有订阅列表
curl http://localhost:8080/api/v1/wx/feeds

# 2. 添加新订阅（如果 API 支持）
curl -X POST http://localhost:8080/api/v1/wx/feeds \
  -H "Content-Type: application/json" \
  -d '{"name": "公众号名称", "wechat_id": "微信号"}'

# 3. 获取特定订阅的 Feed ID
curl http://localhost:8080/api/v1/wx/feeds/{feed_id}
```

### 方案二：检查并修复 Web UI

1. **检查服务日志**
   ```bash
   docker compose logs rss-bridge
   ```

2. **检查容器状态**
   ```bash
   docker compose ps rss-bridge
   ```

3. **重启服务**
   ```bash
   docker compose restart rss-bridge
   ```

4. **检查端口映射**
   ```bash
   docker compose port rss-bridge 8001
   ```

### 方案三：使用正确的端口

访问 `http://localhost:8080` 而不是 `http://localhost:3001`

## 问题：获取Feed ID

### 方法1: 通过API获取

```bash
# 获取所有订阅
curl http://localhost:8080/api/v1/wx/feeds

# 返回格式：
# [
#   {
#     "id": 1,
#     "name": "公众号名称",
#     "wechat_id": "微信号",
#     "feed_id": "feed_123456"
#   }
# ]
```

### 方法2: 通过Web UI获取

1. 访问 `http://localhost:8080`
2. 登录管理界面
3. 查看订阅列表，每个订阅都有对应的Feed ID

### 方法3: 使用脚本

```bash
# 使用项目提供的脚本
./scripts/get_werss_feeds.sh
```

## 问题：登录状态失效

### 症状
- API返回 "Invalid Session"
- 无法获取新文章
- 需要重新扫码登录

### 解决方案

1. **通过Web UI重新登录**
   - 访问 `http://localhost:8080`
   - 使用"刷新会话"功能
   - 或重新扫码登录

2. **检查会话状态**
   ```bash
   curl http://localhost:8080/api/v1/wx/auth/status
   ```

3. **重启服务（会清除会话）**
   ```bash
   docker compose restart rss-bridge
   ```
   **注意**：重启后需要重新登录

## 问题：采集速度慢

### 可能原因

1. **网络问题**：到微信服务器的网络延迟
2. **频率限制**：微信可能限制了请求频率
3. **浏览器驱动问题**：Playwright浏览器驱动未正确安装

### 解决方案

1. **调整采集间隔**
   ```bash
   # 在 docker-compose.yml 中调整
   SPAN_INTERVAL=8  # 每篇稿件间隔8秒（默认）
   ```

2. **检查浏览器驱动**
   ```bash
   # 检查容器内的浏览器驱动
   docker compose exec rss-bridge ls -la /app/data/driver/
   ```

3. **增加共享内存**
   ```bash
   # 在 docker-compose.yml 中
   shm_size: "1gb"  # 增加共享内存
   ```

## 问题：无法获取文章全文

### 症状
- RSS Feed中只有摘要
- 文章内容显示"欢迎关注..."

### 解决方案

1. **检查配置**
   ```bash
   # 确保以下环境变量已设置
   GATHER.CONTENT=True
   GATHER.CONTENT_MODE=web
   GATHER.CLEAN_HTML=True
   ```

2. **检查日志**
   ```bash
   docker compose logs rss-bridge | grep -i gather
   ```

3. **手动触发全文抓取**
   - 在Web UI中点击"获取全文"
   - 或通过API触发

## 常见错误码

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| Invalid Session | 会话失效 | 重新登录 |
| Connection timeout | 连接超时 | 检查网络，增加超时时间 |
| Browser closed | 浏览器关闭 | 检查共享内存，重启服务 |
| Rate limit | 频率限制 | 增加采集间隔 |

## 相关文档

- [采集状态检查指南](../guides/collection.md)
- [we-mp-rss集成指南](../deployment/werss-integration.md)

