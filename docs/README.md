# Z-Pulse 文档中心

欢迎来到 Z-Pulse 文档中心！这里包含了系统的完整文档。

## 📚 文档目录

### 🚀 快速开始

- [项目README](../README.md) - 项目概览和快速开始

### 📖 使用指南

- [使用指南索引](./guides/README.md)
  - [管理后台使用指南](./guides/admin.md)
  - [晨报生成指南](./guides/daily-reports.md)
  - [采集状态检查指南](./guides/collection.md)
  - [邮件服务配置指南](./guides/email-service.md)

### 🚀 部署指南

- [部署指南索引](./deployment/README.md)
  - [阿里云部署指南](./deployment/aliyun.md)
  - [Docker安装指南](./deployment/docker-install.md)
  - [服务重启指南](./deployment/restart.md)
  - [we-mp-rss集成指南](./deployment/werss-integration.md)

### 🔧 故障排除

- [故障排除索引](./troubleshooting/README.md)
  - [we-mp-rss故障排除](./troubleshooting/werss.md)
  - [UI样式问题排查](./troubleshooting/ui.md)

### 🏗️ 架构设计

- [架构对比](./architecture-comparison.md) - 集成we-mp-rss前后对比
- [开发指南](./development.md) - 本地开发环境搭建

## 🗺️ 按角色导航

### 👨‍💻 开发者

1. 阅读 [开发指南](./development.md)
2. 阅读 [架构对比](./architecture-comparison.md)
3. 参考 [API文档](http://localhost:8000/docs)（本地运行后）

### 🔧 运维人员

1. 阅读 [部署指南索引](./deployment/README.md)
2. 阅读 [we-mp-rss集成指南](./deployment/werss-integration.md)
3. 掌握 [故障排除指南](./troubleshooting/README.md)

### 👤 管理员

1. 阅读 [管理后台使用指南](./guides/admin.md)
2. 阅读 [晨报生成指南](./guides/daily-reports.md)
3. 阅读 [采集状态检查指南](./guides/collection.md)

## 🗺️ 按场景导航

### 首次部署

1. [项目README](../README.md) - 了解项目
2. [Docker安装指南](./deployment/docker-install.md) - 安装Docker
3. [阿里云部署指南](./deployment/aliyun.md) - 部署到云主机
4. [we-mp-rss集成指南](./deployment/werss-integration.md) - 配置采集服务

### 日常使用

1. [管理后台使用指南](./guides/admin.md) - 管理系统
2. [晨报生成指南](./guides/daily-reports.md) - 生成报告
3. [采集状态检查指南](./guides/collection.md) - 监控采集

### 故障排除

1. [故障排除索引](./troubleshooting/README.md) - 查找问题
2. [we-mp-rss故障排除](./troubleshooting/werss.md) - 采集问题
3. [UI样式问题排查](./troubleshooting/ui.md) - 前端问题

## 📖 核心概念

### 系统组成

- **postgres-db**: PostgreSQL 数据库
- **api-backend**: FastAPI 后端服务
- **frontend-web**: Next.js 前端服务
- **rss-bridge**: we-mp-rss RSS 服务
- **ingestion-worker**: 数据采集工作进程
- **ai-worker**: AI 报告生成工作进程
- **redis**: Redis 缓存
- **reverse-proxy**: Nginx 反向代理

### 数据流

```
微信公众号 → we-mp-rss → ingestion-worker → PostgreSQL → ai-worker → Report → Email
```

### 核心技术

- Python 3.10+
- FastAPI
- Next.js 14
- PostgreSQL 15
- Redis 7
- 阿里云Qwen
- BERTopic
- Docker & Docker Compose

## 🔗 外部资源

- [we-mp-rss GitHub](https://github.com/rachelos/we-mp-rss)
- [阿里云Qwen文档](https://help.aliyun.com/zh/model-studio/)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Next.js文档](https://nextjs.org/docs)

## 📝 贡献文档

如果您发现文档有误或需要补充，欢迎提交Issue或Pull Request！
