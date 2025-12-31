# 更新 .env 配置并应用更改

## 快速操作步骤

### 1. 编辑 .env 文件

```bash
# 进入项目目录
cd /opt/z-pulse

# 编辑配置文件
nano .env
# 或使用其他编辑器：vi .env
```

### 2. 应用更改

修改 `.env` 文件后，有两种方式应用更改：

#### 方式A：重新创建容器（推荐，确保环境变量完全加载）

```bash
# 停止并重新创建所有容器（会重新读取 .env 文件）
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# 或使用标准配置
docker compose down
docker compose up -d
```

**优点**：
- 确保所有环境变量都被重新读取
- 适用于修改了数据库密码、API密钥等关键配置

#### 方式B：重启服务（快速，适用于小改动）

```bash
# 重启所有服务
docker compose -f docker-compose.prod.yml restart

# 或重启特定服务
docker compose -f docker-compose.prod.yml restart api-backend
docker compose -f docker-compose.prod.yml restart ai-worker
```

**注意**：
- `restart` 命令会重启容器，但某些环境变量可能需要在容器创建时设置
- 如果修改了数据库相关配置，建议使用方式A

### 3. 验证更改

```bash
# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看服务日志，确认配置已生效
docker compose -f docker-compose.prod.yml logs api-backend | head -20
```

## 不同配置类型的处理方式

### 数据库配置（POSTGRES_*, REDIS_PASSWORD）

**必须使用方式A（重新创建容器）**：

```bash
nano .env  # 修改数据库密码等
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### API密钥（DASHSCOPE_API_KEY, BREVO_API_KEY）

可以使用方式B（重启服务）：

```bash
nano .env  # 修改API密钥
docker compose -f docker-compose.prod.yml restart api-backend ai-worker
```

### 网站URL（WEB_URL, NEXT_PUBLIC_API_URL）

**注意**：如果修改了 `NEXT_PUBLIC_API_URL`，需要重新构建前端镜像！

```bash
# 如果只修改了 WEB_URL（后端使用）
nano .env
docker compose -f docker-compose.prod.yml restart api-backend

# 如果修改了 NEXT_PUBLIC_API_URL（前端构建参数）
# 需要在开发机上重新构建前端镜像
```

## 完整示例

```bash
# 1. 编辑配置
cd /opt/z-pulse
nano .env

# 2. 应用更改（推荐方式）
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# 3. 检查服务状态
docker compose -f docker-compose.prod.yml ps

# 4. 查看日志确认
docker compose -f docker-compose.prod.yml logs -f
```

## 常见问题

**Q: 修改 .env 后，服务没有读取新配置？**

A: 使用 `down` + `up -d` 重新创建容器，而不是只使用 `restart`。

**Q: 修改了数据库密码，服务无法连接？**

A: 确保使用 `down` + `up -d` 重新创建所有容器，包括数据库容器。

**Q: 修改配置后需要重新构建镜像吗？**

A: 只有修改了 `NEXT_PUBLIC_API_URL` 才需要重新构建前端镜像。其他配置修改后只需重启服务。

