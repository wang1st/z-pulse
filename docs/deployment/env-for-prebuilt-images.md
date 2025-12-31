# 使用预构建镜像时的 .env 配置说明

## 重要说明

**`.env` 文件不需要打包到镜像中！**

- **镜像构建时**：只需要 `NEXT_PUBLIC_API_URL`（作为构建参数，用于前端构建）
- **运行时**：所有环境变量通过 Docker Compose 从服务器的 `.env` 文件读取

## 工作流程

### 1. 在开发机上构建镜像

```bash
# 在开发机上，只需要设置 NEXT_PUBLIC_API_URL（可选）
# 如果没有设置，会使用默认值 http://api-backend:8000
cp env.example .env
# 编辑 .env，设置 NEXT_PUBLIC_API_URL（用于前端构建）
nano .env

# 构建并导出镜像
./scripts/build-and-export-images.sh
```

**注意**：开发机上的 `.env` 文件只需要 `NEXT_PUBLIC_API_URL`，其他变量可以留空或使用默认值。

### 2. 传输镜像到服务器

```bash
# 传输镜像文件
scp z-pulse-built-images.tar root@your-server-ip:/opt/z-pulse/
```

### 3. 在服务器上配置 .env（重要！）

```bash
# 在服务器上
cd /opt/z-pulse

# 从模板创建 .env 文件
cp env.example .env

# 编辑配置文件，设置所有必需的变量
nano .env
```

**必须配置的变量**：

```bash
# 数据库配置（必需）
POSTGRES_USER=zpulse
POSTGRES_PASSWORD=your_strong_password_here  # ⚠️ 必须修改！
POSTGRES_DB=zpulse
REDIS_PASSWORD=your_redis_password_here  # ⚠️ 必须修改！

# AI服务配置（必需）
DASHSCOPE_API_KEY=your_aliyun_qwen_api_key  # ⚠️ 必须修改！

# 邮件服务配置（必需）
EMAIL_PROVIDER=brevo  # 或 sendgrid
BREVO_API_KEY=your_brevo_api_key  # ⚠️ 必须修改！
EMAIL_FROM=your-email@example.com  # ⚠️ 必须修改！

# 网站URL（生产环境，必需）
WEB_URL=https://your-domain.com  # ⚠️ 必须修改！
NEXT_PUBLIC_API_URL=https://your-domain.com/api  # ⚠️ 必须修改！
```

### 4. 导入镜像并启动服务

```bash
# 导入预构建的镜像
./scripts/import-built-images.sh z-pulse-built-images.tar

# 启动服务（Docker Compose 会自动从 .env 文件读取环境变量）
docker compose -f docker-compose.prod.yml up -d
```

## 为什么不需要重新生成镜像？

1. **镜像中不包含 `.env` 文件**
   - `.env` 文件在 `.gitignore` 中，不会被复制到镜像
   - 镜像只包含代码和依赖

2. **环境变量在运行时注入**
   - Docker Compose 读取服务器的 `.env` 文件
   - 通过 `environment:` 配置传递给容器
   - 例如：`POSTGRES_PASSWORD=${POSTGRES_PASSWORD}`

3. **只有前端需要构建时参数**
   - `NEXT_PUBLIC_API_URL` 在构建时使用（用于生成前端代码）
   - 其他变量都在运行时使用

## 更新配置

如果修改了 `.env` 文件，只需要重启服务，**不需要重新构建镜像**：

```bash
# 修改 .env 文件后
nano .env

# 方式1：重新创建容器（推荐，确保环境变量完全加载）
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# 方式2：快速重启（适用于小改动）
docker compose -f docker-compose.prod.yml restart
```

**注意**：
- 修改数据库相关配置（如 `POSTGRES_PASSWORD`）时，建议使用方式1
- 修改API密钥等配置时，可以使用方式2
- 详细说明请参考：[更新 .env 配置并应用更改](update-env.md)

## 常见问题

**Q: 如果修改了 `NEXT_PUBLIC_API_URL`，需要重新构建镜像吗？**

A: 是的。`NEXT_PUBLIC_API_URL` 是前端构建时的参数，修改后需要重新构建前端镜像。

**Q: 如果修改了数据库密码，需要重新构建镜像吗？**

A: 不需要。数据库密码是运行时环境变量，修改 `.env` 后重启服务即可。

**Q: 开发机和服务器上的 `.env` 文件可以不同吗？**

A: 可以。开发机上的 `.env` 主要用于构建镜像（只需要 `NEXT_PUBLIC_API_URL`），服务器上的 `.env` 用于运行时配置（需要所有变量）。

