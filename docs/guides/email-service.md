# 邮件服务配置指南

## 支持的邮件服务商

系统支持多个邮件服务商，推荐使用 **Brevo（原Sendinblue）**：

- ✅ **Brevo**：免费额度最高（300封/天），注册简单，推荐用于项目初期
- **SendGrid**：免费额度100封/天，但注册验证较复杂
- **其他SMTP服务**：支持标准SMTP协议的服务

## 🔄 配置Brevo（推荐）

### 步骤1: 注册Brevo账号

1. 访问：https://www.brevo.com/
2. 点击"Sign up free"
3. 填写邮箱和密码
4. 验证邮箱（通常立即收到）

### 步骤2: 获取API密钥

1. 登录Brevo控制台
2. 进入 **Settings** → **SMTP & API**
3. 点击 **API Keys** 标签
4. 点击 **Generate a new API key**
5. 选择权限：**Mail Send**（发送邮件）
6. 复制生成的API密钥

### 步骤3: 配置环境变量

在 `.env` 文件中配置：

```bash
EMAIL_PROVIDER=brevo
BREVO_API_KEY=your_brevo_api_key_here
EMAIL_FROM=your-email@example.com
EMAIL_FROM_NAME=浙财脉动
```

### 步骤4: 重启服务

```bash
docker compose restart api-backend ai-worker
```

## 🔄 配置SendGrid

### 步骤1: 注册SendGrid账号

1. 访问：https://sendgrid.com/
2. 点击"Start for free"
3. 填写注册信息
4. **重要**：验证邮箱（检查收件箱和垃圾邮件）

### 步骤2: 获取API密钥

1. 登录SendGrid控制台
2. 进入 **Settings** → **API Keys**
3. 点击 **Create API Key**
4. 选择权限：**Full Access** 或 **Mail Send**
5. 复制生成的API密钥（只显示一次，请保存）

### 步骤3: 配置环境变量

```bash
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=your_sendgrid_api_key_here
EMAIL_FROM=your-email@example.com
EMAIL_FROM_NAME=浙财脉动
```

### 步骤4: 重启服务

```bash
docker compose restart api-backend ai-worker
```

## 🚨 SendGrid登录问题解决方案

### 问题：`You are not authorized to access this account`

这是SendGrid常见的账户验证问题，可能的原因：

1. **邮箱未验证** - 注册后需要验证邮箱
2. **账户被限制** - 新账户可能需要等待审核
3. **地区限制** - 某些地区可能需要额外验证
4. **账户状态** - 账户可能被暂停

### 解决方案

#### 方案1: 检查邮箱验证

1. 检查注册邮箱的收件箱（包括垃圾邮件）
2. 查找来自SendGrid的验证邮件
3. 点击验证链接

#### 方案2: 联系SendGrid支持

1. 访问：https://support.sendgrid.com/
2. 提交工单说明问题
3. 通常24小时内会回复

#### 方案3: 使用Brevo（推荐）

如果SendGrid验证困难，建议切换到Brevo，因为：
- ✅ 免费额度更高（300封/天 vs 100封/天）
- ✅ 注册简单，无需复杂验证
- ✅ Python SDK完善
- ✅ 适合项目初期

## 📧 测试邮件发送

### 方法1: 通过管理后台

1. 登录管理后台
2. 进入"订阅管理"
3. 选择一个订阅者
4. 点击"发送测试邮件"

### 方法2: 通过API

```bash
curl -X POST http://localhost:8000/api/admin/subscribers/{id}/send-test \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 方法3: 使用Python脚本

```bash
docker compose exec api-backend python /app/backend/app/tools/send_test_email.py recipient@example.com
```

## 🔍 查看邮件发送状态

### 查看日志

```bash
# 查看邮件服务日志
docker compose logs api-backend | grep -i email
docker compose logs ai-worker | grep -i email
```

### 检查发送统计

在管理后台的"订阅管理"页面，可以看到：
- 每个订阅者的发送次数
- 最后发送时间

## 🐛 故障排除

### 邮件发送失败

1. **检查API密钥**：确认API密钥正确配置
2. **检查服务商状态**：访问服务商控制台查看账户状态
3. **检查发送限制**：确认未超过免费额度
4. **查看日志**：检查详细的错误信息

### 邮件进入垃圾箱

1. **配置SPF记录**：在DNS中添加SPF记录
2. **配置DKIM**：在服务商控制台配置DKIM
3. **使用已验证的发件人**：使用已验证的邮箱地址

### 邮件格式问题

1. **检查HTML渲染**：在管理后台预览报告
2. **检查编码**：确保使用UTF-8编码
3. **检查链接**：确认所有链接正确

## 相关文档

- [管理后台使用指南](./admin.md)
- [故障排除](../troubleshooting/README.md)

