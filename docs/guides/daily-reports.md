# 晨报生成指南

## 📅 定时生成时间

**默认配置：**
- **晨报生成时间**：每天 **09:45**（早上）
- **周报生成时间**：每周日 **22:00**（晚上10点）

**配置位置：**
- 环境变量：`DAILY_REPORT_TIME=09:45`
- 配置文件：`.env` 文件或 `docker-compose.yml`

## 🚀 手动触发晨报生成

### 方法 1: 使用管理后台 API（推荐）

在管理后台页面，可以通过 API 端点手动触发：

```bash
# 触发晨报生成
curl -X POST http://localhost/api/admin/reports/generate/daily \
  -H "Authorization: Bearer YOUR_TOKEN"

# 触发周报生成
curl -X POST http://localhost/api/admin/reports/generate/weekly \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 方法 2: 直接在容器中执行

```bash
# 进入 ai-worker 容器
docker compose exec ai-worker python -c "
from app.workers.ai_generate import AIWorker
worker = AIWorker()
worker.generate_daily_report()
print('✅ 晨报生成完成')
"
```

### 方法 3: 使用 Python 脚本

```bash
# 在容器中执行
docker compose exec ai-worker python -m app.workers.ai_generate
```

## 📊 生成流程说明

### 晨报生成流程

1. **查询文章**：从数据库中查询今天的所有文章（`status = PROCESSED`）
2. **筛选财政相关内容**：使用 AI 判断每篇文章是否与财政相关
   - 只保留与财政相关的文章
   - 记录筛选统计信息
3. **生成报告**：将符合窗口口径的财政相关文章输入 AI，生成结构化晨报
4. **保存报告**：将生成的晨报保存到数据库

### 生成条件

- 必须有已处理的文章（`status = PROCESSED`）
- 必须有与财政相关的文章（经过 AI 筛选后）
- 如果没有任何财政相关文章，会记录警告但不生成报告

## 🔍 查看生成状态

### 查看日志

```bash
# 实时查看 AI Worker 日志
docker compose logs -f ai-worker

# 查看最近的日志
docker compose logs --tail=50 ai-worker
```

### 检查报告

在管理后台的"报告管理"页面，可以查看已生成的晨报和周报。

## 📝 报告格式

### Smart Brevity 格式（当前使用）

晨报采用 Smart Brevity 财政信息聚合格式，包含：

- **今日焦点**（3句段落）:
  - 第1句（lede）：核心事实，不超过50字
  - 第2句（why_it_matters）：财政视角的影响/抓手
  - 第3句（big_picture）：关注点/风险点/落地要害
- **近日热点**：近3天的事件聚类，展示覆盖文档数、账号数、热度等
- **今日关键词**：从热点中提取的关键词
- **引用来源**：所有引用的文章列表

### 旧版格式（已废弃）

- `voice`: 旧版"口播稿分段"结构（已废弃，仅作为兼容回滚）

## ⚙️ 配置选项

### 环境变量

```bash
# AI模型配置
QWEN_DAILY_MODEL=qwen-plus          # 晨报生成模型
QWEN_FILTER_MODEL=qwen-flash        # 文章筛选模型
QWEN_WEEKLY_MODEL=qwen-max-latest   # 周报生成模型

# 生成时间配置
DAILY_REPORT_TIME=09:45             # 晨报生成时间
WEEKLY_REPORT_DAY=sunday             # 周报生成日期
WEEKLY_REPORT_TIME=22:00             # 周报生成时间

# 报告格式
DAILY_REPORT_FORMAT=smart_brevity   # 晨报格式（smart_brevity/voice）
```

## 🐛 故障排除

### 报告生成失败

1. **检查日志**：查看 `ai-worker` 容器的日志
2. **检查文章**：确保有足够的已处理文章
3. **检查API密钥**：确认 `DASHSCOPE_API_KEY` 正确配置
4. **检查模型可用性**：确认阿里云Qwen服务正常

### 报告内容为空

1. **检查文章筛选**：查看日志中的筛选统计
2. **检查财政相关性**：可能需要调整筛选标准
3. **检查时间范围**：确认查询的文章日期正确

### 报告生成缓慢

1. **检查模型选择**：`qwen-plus` 比 `qwen-max-latest` 更快
2. **检查文章数量**：文章过多会导致生成缓慢
3. **检查网络**：确认到阿里云的网络连接正常

## 相关文档

- [管理后台使用指南](./admin.md)
- [故障排除](../troubleshooting/README.md)

