# Z-Pulse 开发指南

## 目录

- [开发环境设置](#开发环境设置)
- [项目结构](#项目结构)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [测试](#测试)
- [调试](#调试)

## 开发环境设置

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置开发环境变量

创建`.env`文件：

```env
ENVIRONMENT=development
DEBUG=true
DATABASE_ECHO=true
LOG_LEVEL=DEBUG
```

### 3. 启动开发服务器

```bash
# API网关
cd services/api-gateway
python -m app.main

# 数据采集服务
cd services/collector
python -m app.main

# AI处理服务
cd services/ai-processor
python -m app.main

# 邮件服务
cd services/email-sender
python -m app.main
```

## 项目结构

```
z-pulse/
├── services/               # 微服务
│   ├── api-gateway/       # API网关
│   ├── collector/         # 数据采集服务
│   ├── ai-processor/      # AI处理服务
│   └── email-sender/      # 邮件发送服务
├── shared/                # 共享模块
│   ├── database/          # 数据库模型
│   ├── config/            # 配置
│   └── utils/             # 工具函数
├── docs/                  # 文档
├── scripts/               # 脚本
├── tests/                 # 测试
└── docker-compose.yml     # Docker配置
```

## 开发流程

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发

- 遵循代码规范
- 编写单元测试
- 添加文档注释

### 3. 测试

```bash
pytest tests/
```

### 4. 提交代码

```bash
git add .
git commit -m "feat: add new feature"
```

### 5. 推送并创建Pull Request

```bash
git push origin feature/your-feature-name
```

## 代码规范

### Python代码规范

遵循PEP 8规范：

```bash
# 格式化代码
black .

# 检查代码风格
flake8 .

# 类型检查
mypy .

# 排序import
isort .
```

### 提交信息规范

遵循Conventional Commits规范：

- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

示例：
```
feat(collector): add RSS collector
fix(api): fix authentication bug
docs: update README
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_collector.py

# 运行带覆盖率的测试
pytest --cov=app tests/
```

### 编写测试

```python
# tests/test_example.py
import pytest
from app.main import app

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

## 调试

### 使用Python调试器

```python
import pdb; pdb.set_trace()
```

### 查看日志

```python
from shared.utils import get_logger

logger = get_logger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

### 使用FastAPI调试

访问交互式API文档：

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## API开发

### 添加新路由

1. 在`services/api-gateway/app/routers/`创建新文件
2. 定义路由和请求/响应模型
3. 在`main.py`中注册路由

示例：

```python
# routers/example.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from shared.database import get_db

router = APIRouter()

@router.get("/example")
async def get_example(db: Session = Depends(get_db)):
    return {"message": "example"}
```

```python
# main.py
from .routers import example
app.include_router(example.router, prefix="/api/v1/example", tags=["Example"])
```

## 数据库开发

### 创建数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "Add new table"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 修改模型

1. 在`shared/database/models.py`修改模型
2. 创建迁移
3. 应用迁移

## Celery任务开发

### 添加新任务

```python
# services/collector/app/tasks.py
from celery import shared_task

@shared_task
def new_task(param):
    # 任务逻辑
    return result
```

### 调用任务

```python
from app.tasks import new_task

# 异步调用
result = new_task.delay(param)

# 同步调用
result = new_task.apply(args=[param])
```

## 常见问题

### Q: 如何添加新的依赖？

A: 在对应服务的`requirements.txt`中添加，然后重新构建镜像。

### Q: 如何调试Celery任务？

A: 使用`CELERY_ALWAYS_EAGER=True`在当前进程同步执行任务。

### Q: 如何重置数据库？

A: 
```bash
docker-compose down -v
docker-compose up -d postgres
python scripts/init_db.py
```

## 资源

- [FastAPI文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
- [Celery文档](https://docs.celeryproject.org/)
- [PostgreSQL文档](https://www.postgresql.org/docs/)

