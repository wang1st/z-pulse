# 故障排除指南

本目录包含各种故障排除指南，帮助您解决系统运行中遇到的问题。

## 📚 故障排除文档

### Docker 相关

- [Docker 镜像加速器问题排查](./docker-mirror.md) - Docker Hub 连接超时和镜像拉取问题

### we-mp-rss 相关

- [we-mp-rss 故障排除](./werss.md) - we-mp-rss服务相关问题

### UI 相关

- [UI样式问题排查](./ui.md) - 前端样式和显示问题

## 🔍 快速诊断

### 检查服务状态

```bash
# 查看所有服务状态
docker compose ps

# 查看服务日志
docker compose logs -f
```

### 常见问题快速检查

1. **服务无法启动**
   - 检查Docker是否运行：`docker ps`
   - 检查端口占用：`lsof -i :3000`
   - 查看服务日志：`docker compose logs <service-name>`

2. **数据库连接失败**
   - 检查数据库服务：`docker compose ps postgres-db`
   - 查看数据库日志：`docker compose logs postgres-db`
   - 重启数据库：`docker compose restart postgres-db`

3. **前端无法访问**
   - 检查前端服务：`docker compose ps frontend-web`
   - 清除浏览器缓存（硬刷新：Cmd+Shift+R）
   - 检查Nginx配置：`docker compose logs reverse-proxy`

4. **API无法访问**
   - 检查API服务：`docker compose ps api-backend`
   - 查看API日志：`docker compose logs api-backend`
   - 检查健康状态：`curl http://localhost:8000/api/health`

## 📖 相关文档

- [部署指南](../deployment/README.md)
- [使用指南](../guides/README.md)

