# 管理后台使用指南

## 功能概述

管理后台提供了完整的系统管理功能，包括：

1. **仪表板** - 查看系统统计信息
2. **公众号管理** - 添加、编辑、删除公众号
3. **订阅管理** - 查看和管理邮件订阅者
4. **报告管理** - 查看和管理AI生成的报告

## 快速开始

### 1. 创建管理员用户

首先需要创建一个管理员账户。可以通过以下方式：

#### 方式一：使用API注册（推荐，最简单）

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "your_password",
    "full_name": "管理员"
  }'
```

**注意**：第一个注册的用户会自动成为超级用户。

#### 方式二：使用Python命令

```bash
# 在Docker容器中直接执行Python代码
docker compose exec api-backend python -c "
import sys
sys.path.insert(0, '/app')
from shared.database import SessionLocal, User
from shared.auth import get_password_hash

db = SessionLocal()
try:
    existing = db.query(User).filter((User.username == 'admin') | (User.email == 'admin@example.com')).first()
    if existing:
        print('❌ 用户已存在')
    else:
        user_count = db.query(User).count()
        user = User(
            username='admin',
            email='admin@example.com',
            full_name='管理员',
            hashed_password=get_password_hash('your_password'),
            is_superuser=(user_count == 0)
        )
        db.add(user)
        db.commit()
        print(f'✅ 管理员用户创建成功 (is_superuser={user_count == 0})')
finally:
    db.close()
"
```

#### 方式三：使用脚本

```bash
# 使用项目提供的脚本
docker compose exec api-backend python /app/scripts/create_admin.py
```

### 2. 登录管理后台

1. 访问：`http://localhost/admin`
2. 使用创建的管理员账户登录
3. 登录成功后会自动跳转到仪表板

## 功能详解

### 仪表板

仪表板显示系统的关键统计信息：

- **总文章数** - 系统中所有文章的总数
- **总订阅数** - 邮件订阅用户总数
- **已发送报告数** - 已生成的报告总数
- **活跃公众号数** - 正在采集的公众号数量

### 公众号管理

#### 添加公众号

1. 点击"公众号管理" → "添加公众号"
2. 填写以下信息：
   - **名称**：公众号显示名称
   - **微信号**：公众号的微信号（用于we-mp-rss）
   - **Feed ID**：从we-mp-rss获取的Feed ID（可选）
   - **描述**：公众号描述（可选）
3. 点击"保存"

#### 编辑公众号

1. 在公众号列表中，点击要编辑的公众号
2. 修改信息后点击"保存"

#### 删除公众号

1. 在公众号列表中，点击要删除的公众号
2. 点击"删除"按钮
3. 确认删除

**注意**：删除公众号不会删除已采集的文章，但会停止后续采集。

### 订阅管理

#### 查看订阅者

在"订阅管理"页面可以查看所有邮件订阅者，包括：

- 邮箱地址
- 订阅状态（已确认/待确认）
- 订阅时间
- 最后发送时间

#### 手动发送邮件

1. 选择要发送的订阅者
2. 选择要发送的报告
3. 点击"发送邮件"

### 报告管理

#### 查看报告

在"报告管理"页面可以查看所有生成的报告：

- **晨报**：每日生成的晨报
- **周报**：每周生成的周报

#### 手动生成报告

1. 点击"生成报告"
2. 选择报告类型（晨报/周报）
3. 选择日期（可选，默认为今天/本周）
4. 点击"生成"

#### 重新生成报告

如果对生成的报告不满意，可以重新生成：

1. 在报告列表中，点击要重新生成的报告
2. 点击"重新生成"
3. 系统会使用相同的参数重新生成报告

#### 删除报告

1. 在报告列表中，点击要删除的报告
2. 点击"删除"
3. 确认删除

**注意**：删除报告不会影响已发送的邮件。

## 常见问题

### Q: 如何批量导入公众号？

A: 可以使用CSV文件批量导入：

```bash
# 准备CSV文件（格式：name,wechat_id,description）
docker compose exec api-backend python /app/scripts/import_accounts.py /path/to/accounts.csv
```

### Q: 如何查看采集状态？

A: 在"公众号管理"页面，每个公众号都会显示：
- 文章总数
- 最后采集时间

如果最后采集时间超过1小时，可能采集进程有问题，请查看日志。

### Q: 如何手动触发采集？

A: 在管理后台的"公众号管理"页面，点击"立即采集"按钮。

### Q: 报告生成失败怎么办？

A: 1. 查看ai-worker的日志：`docker compose logs ai-worker`
2. 检查是否有足够的文章
3. 检查DASHSCOPE_API_KEY是否正确配置
4. 尝试手动重新生成报告

## 相关文档

- [晨报生成指南](./daily-reports.md)
- [故障排除](../troubleshooting/README.md)

