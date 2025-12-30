# 部署指南

本目录包含系统部署相关的文档，帮助您在不同环境中部署系统。

## 📚 部署文档

### 云主机部署

- [阿里云部署指南](./aliyun.md) - 在阿里云云主机上部署系统

### Docker相关

- [Docker安装指南](./docker-install.md) - 安装Docker和Docker Compose
- [服务重启指南](./restart.md) - 如何重启和管理服务

### 集成指南

- [we-mp-rss集成指南](./werss-integration.md) - we-mp-rss服务集成说明

## 🚀 快速开始

### 本地开发环境

1. 安装Docker和Docker Compose（参考[Docker安装指南](./docker-install.md)）
2. 克隆项目并配置环境变量
3. 启动服务：`docker compose up -d`
4. 访问系统：`http://localhost`

### 生产环境部署

1. 准备云主机（参考[阿里云部署指南](./aliyun.md)）
2. 配置环境变量和SSL证书
3. 启动服务并验证
4. 配置监控和备份

## 🔗 相关文档

- [使用指南](../guides/README.md)
- [故障排除](../troubleshooting/README.md)

