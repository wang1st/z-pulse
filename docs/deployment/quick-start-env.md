# 快速配置 .env 文件

如果看到类似以下警告，说明服务器上缺少 `.env` 文件：

```
WARN[0000] The "POSTGRES_USER" variable is not set. Defaulting to a blank string.
WARN[0000] The "POSTGRES_PASSWORD" variable is not set. Defaulting to a blank string.
```

## 快速解决

在服务器上执行：

```bash
# 1. 进入项目目录
cd /opt/z-pulse

# 2. 从模板创建 .env 文件
cp env.example .env

# 3. 编辑配置文件
nano .env
```

## 必须配置的变量

至少需要配置以下变量才能启动服务：

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

## 配置完成后

```bash
# 验证配置
cat .env | grep -E "POSTGRES_|REDIS_|DASHSCOPE_|BREVO_|EMAIL_FROM|WEB_URL" | grep -v "^#"

# 启动服务
docker compose -f docker-compose.prod.yml up -d

# 或使用标准配置
docker compose up -d
```

## 详细配置说明

更多配置选项和说明，请参考：
- `env.example` 文件中的注释
- [完整部署文档](aliyun.md#第三步配置环境变量)

