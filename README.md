# Z-Pulse 浙财脉动-AI晨报系统 V2.1

[![Version](https://img.shields.io/badge/version-2.1.0-indigo.svg)](https://github.com/wang1st/z-pulse)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](docker-compose.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-14-black.svg)](https://nextjs.org/)

> 基于阿里云Qwen、BERTopic主题分析和Next.js的智能财政信息晨报与周报系统

## 📖 项目简介

Z-Pulse 是一个智能化的财政信息采集与分析系统，能够自动从浙江省内地市级和县级政府官方微信公众号采集财政相关文章，使用AI技术生成结构化的晨报和周报，并通过邮件推送给订阅用户。

系统每天09:45自动生成晨报，每周一晨报生成后自动触发周报生成（覆盖过去7天内容），为财政工作者提供及时、精准的信息服务。

### 核心价值

- 🤖 **智能分析**: 混合AI架构（BERTopic主题聚类 + 阿里云Qwen深度解读）
- 📊 **自动化流程**: 全自动采集、分析、生成、推送
- 🎨 **现代化界面**: 统一的靛蓝/紫色主题（Indigo/Purple），Next.js 14 SSR/ISR
- 📧 **标准订阅**: Double Opt-In邮件订阅流程
- 🐳 **一键部署**: Docker Compose编排，8服务协同
- 🔒 **生产就绪**: 健康检查、网络隔离、安全规范

## 🏗️ 系统架构

```
                         外部用户
                            ↓
                  ┌─────────────────┐
                  │  Nginx (80/443) │ ← 单一入口（反向代理）
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
         ┌────▼─────┐             ┌────▼─────┐
         │ Next.js  │             │ FastAPI  │
         │ 前端界面  │ :3000       │ 后端API  │ :8000
         └──────────┘             └────┬─────┘
                                       │
                    ┌──────────────────┼───────────────┐
                    │                  │               │
              ┌─────▼─────┐     ┌─────▼──────┐  ┌────▼────┐
              │Ingestion  │     │ AI Worker  │  │ Redis   │
              │Worker     │     │ (Qwen+     │  │ 缓存    │
              │(RSS→DB)   │     │ BERTopic)  │  └─────────┘
              └─────┬─────┘     └─────┬──────┘
                    │                 │
                    └────────┬────────┘
                             │
                    ┌────────▼─────────┐
                    │   PostgreSQL 15   │
                    │   数据中心        │
                    └──────────────────┘
                             ▲
                             │
                    ┌────────┴────────┐
                    │   we-mp-rss     │
                    │   (rss-bridge)  │
                    │   微信采集器    │ :8080/:3001
                    └─────────────────┘
```

## 🎯 核心服务（8个）

| # | 服务名 | 容器名 | 技术栈 | 端口 | 职责 |
|---|--------|--------|--------|------|------|
| 1 | **postgres-db** | zpulse-db | PostgreSQL 15 | 5432 | 数据中心，存储所有业务数据 |
| 2 | **api-backend** | zpulse-api | FastAPI | 8000 | REST API，业务逻辑核心 |
| 3 | **frontend-web** | zpulse-web | Next.js 14 | 3000 | 用户界面，SSR/ISR优化 |
| 4 | **rss-bridge** | zpulse-rss | we-mp-rss | 8080/3001 | 微信公众号采集器 |
| 5 | **ingestion-worker** | zpulse-ingest-worker | Python | - | RSS采集工作节点（后台自动运行） |
| 6 | **ai-worker** | zpulse-ai-worker | Python+Qwen+BERTopic | - | AI报告生成工作节点（支持异步任务） |
| 7 | **redis** | zpulse-redis | Redis 7 | 6379 | 缓存和会话存储 |
| 8 | **reverse-proxy** | zpulse-proxy | Nginx | 80/443 | 反向代理，路由分发 |

## 📚 文档

完整的文档请访问 [文档中心](docs/README.md)，包含：

- 📖 [使用指南](docs/guides/README.md) - 管理后台、报告生成、数据采集、邮件服务
- 🚀 [部署指南](docs/deployment/README.md) - 云主机部署、Docker安装、服务管理
- 🔧 [故障排除](docs/troubleshooting/README.md) - 常见问题解决方案

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ 可用内存
- 阿里云Qwen API密钥（[获取地址](https://dashscope.aliyuncs.com/)）
- 邮件服务API密钥（SendGrid或Brevo）

### 5分钟快速启动

```bash
# 1. 克隆项目 (GitHub 或 Gitee)
git clone git@github.com:wang1st/z-pulse.git
# 或者
git clone https://gitee.com/wang1st/z-pulse.git

cd z-pulse

# 2. 配置环境变量
cp env.example .env
# 编辑 .env，至少配置以下必需项：
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
# - DASHSCOPE_API_KEY（阿里云Qwen）
# - BREVO_API_KEY 或 SENDGRID_API_KEY
# - EMAIL_FROM

# 3. 启动所有服务
docker-compose up -d

# 4. 初始化数据库
docker-compose exec api-backend python scripts/init_db.py

# 5. 访问系统
# - 前端界面: http://localhost
# - API文档: http://localhost/docs
# - we-mp-rss UI: http://localhost:3001
```

### 验证部署

```bash
# 查看所有服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f api-backend
docker-compose logs -f ingestion-worker
docker-compose logs -f ai-worker

# 检查健康状态
curl http://localhost/api/health
```

## 📖 技术栈

### 前端层
- **Next.js 14**: SSR/ISR、SEO优化、Standalone输出
- **React 18**: 组件化开发
- **TypeScript**: 类型安全
- **Tailwind CSS**: 现代化样式系统
- **Radix UI**: 无障碍组件库
- **UI风格**: 统一的靛蓝/紫色（Indigo/Purple）渐变主题

### 后端层
- **FastAPI**: 高性能异步API框架
- **SQLAlchemy 2.0**: 现代ORM
- **Pydantic**: 数据验证和序列化
- **Uvicorn**: ASGI服务器
- **Asyncio**: 全异步任务处理

### AI/ML层
- **阿里云Qwen**: 大语言模型（兼容OpenAI接口）
  - `qwen-plus`: 晨报生成（默认）
  - `qwen-flash`: 快速筛选和关键词提取
  - `qwen-max-latest`: 周报深度分析
- **BERTopic**: 主题建模和聚类
- **sentence-transformers**: BERT embeddings
- **jieba**: 中文分词和词性标注
- **提示词工程**: 精心设计的系统提示词，确保生成符合财政领域要求的高质量报告

### 数据层
- **PostgreSQL 15**: 主数据库
- **Redis 7**: 缓存和会话存储
- **SQLite**: we-mp-rss内部数据库

### 基础设施
- **Docker & Docker Compose**: 容器化部署
- **Nginx**: 反向代理和负载均衡
- **we-mp-rss**: 微信公众号RSS桥接器

### 邮件服务
- **Brevo** (原Sendinblue): 推荐，免费额度300封/天
- **SendGrid**: 备选方案
- **Mailgun**: 支持（需配置）

## 💡 核心功能

### 1. 智能数据采集

**数据流**: `微信公众号 → we-mp-rss → RSS Feed → Ingestion Worker → PostgreSQL`

**特性**:
- ✅ **全自动后台运行**: `ingestion-worker` 默认每30分钟自动采集，无需人工干预
- ✅ **智能去重**: 基于URL去重，避免重复存储
- ✅ **全文抓取**: 自动抓取文章全文（替代点查看再回源）
- ✅ **SQLite直读**: 支持直接读取we-mp-rss SQLite数据库，避免HTTP超时
- ✅ **采集状态追踪**: 详细的错误处理和日志记录
- ✅ **时间窗口限制**: 支持 `MIN_ARTICLE_DATE` 配置

**配置**:
```env
POLL_INTERVAL=1800              # 采集间隔（秒）
INGEST_OFFSET_MINUTES=5         # 错峰偏移（分钟）
FETCH_FULL_CONTENT=True         # 自动抓取全文
USE_WERSS_DB=True              # 使用SQLite直读
MIN_ARTICLE_DATE=2025-12-15     # 最早采集日期
```

### 2. AI报告生成

#### 晨报生成（每天09:45）

**流程**:
1. 筛选指定日期发布的财政相关文章（AI判断）
2. 生成一句话摘要、今日焦点、近日热点、关键词
3. 自动发送邮件

**提示词策略**：
- 采用 **Smart Brevity** 风格，融合 Axios 的"模块化、视觉焦点、直击要害"理念
- 强制**事实优先**，严禁编造金额/数字/政策细则
- **单一焦点**原则，避免拼盘式罗列，确保每个晨报都有明确的核心事件
- **覆盖面控制**，引用至少3篇材料，覆盖至少2个地市，确保代表性

#### 周报生成（每周一晨报后自动触发）

**混合分析管线**:
```
文章集合 → BERTopic主题聚类 → 识别核心主题 → Qwen深度分析 → 结构化报告
```

**提示词策略**：
- **"跳出财政看财政"**，从宏观经济、社会趋势、政策周期等更广阔视角分析
- **全局视角**识别最有价值的1个核心洞察，而非逐一罗列事件
- **严格字数控制**（550-650字），确保精炼且有深度
- **跨领域连接**，将财政动态与更宏观的背景联系起来

**特性**:
- ✅ **后台异步任务**: 生成过程不阻塞API，支持长时间运行
- ✅ **自动触发**: 周一晨报生成后自动生成周报，覆盖过去7天内容
- ✅ **深度洞察**: 无监督主题发现 + LLM深度分析

### 3. Double Opt-In订阅系统

**流程**:
```
1. 用户提交邮箱 → is_active=False
2. 生成安全令牌 → secrets.token_urlsafe(32)
3. 后台发送验证邮件 → BackgroundTasks（异步）
4. 用户点击验证链接 → is_active=True
5. 开始接收报告邮件
```

### 4. 现代化Web界面

**特性**:
- 📱 响应式设计（移动端适配）
- ⚡ 极速加载（ISR增量静态生成）
- 🔍 SEO优化（SSR服务端渲染）
- 🎨 **统一UI风格**: 全站采用 Indigo/Purple 渐变主题，视觉体验一致
- 📄 **分页支持**: 所有列表页面（文章、公众号、订阅者、报告）均支持分页

**页面**:
- `/`: 首页（最新报告概览）
- `/reports/[id]`: 报告详情
- `/admin/*`: 管理后台（统一风格）

### 5. 管理后台

**功能**:
- 📊 **仪表盘**: 实时数据统计和监控
- 📰 **文章管理**: 查看文章列表、筛选状态（采集全自动，无需手动操作）
- 👥 **订阅管理**: 订阅用户列表、分页查询
- 📝 **报告管理**: 查看历史报告、重新生成（支持按日期重跑）
- ⚙️ **公众号管理**: 管理采集源，支持批量导入/导出

## 📊 数据模型

### 核心表结构

```sql
-- 1. 公众号目标清单
official_accounts
├── id (PK)
├── name (公众号名称)
├── wechat_id (微信ID, UNIQUE)
├── werss_feed_id (we-mp-rss订阅ID, UNIQUE)
├── is_active (是否启用)
└── last_collection_time (最后采集时间)

-- 2. 原始文章
scraped_articles
├── id (PK)
├── account_id (FK → official_accounts)
├── title (标题)
├── article_url (URL, UNIQUE) ⭐ 去重关键
├── content (全文内容)
├── published_at (发布时间)
├── status (处理状态: pending/processed/failed)
└── processed_at (处理时间)

-- 3. AI生成报告
ai_generated_reports
├── id (PK)
├── report_type (daily/weekly)
├── report_date (报告日期, UNIQUE per type) ⭐
├── summary_markdown (摘要Markdown)
├── analysis_markdown (分析Markdown)
├── article_count (文章数量)
└── generated_at (生成时间)

-- 4. 订阅用户
subscribers
├── id (PK)
├── email (邮箱, UNIQUE) ⭐
├── is_active (是否激活) ⭐ Double Opt-In
├── verification_token (验证令牌) ⭐
├── verified_at (验证时间)
└── subscribed_at (订阅时间)
```

## ⏰ 定时任务

| 任务 | 时间 | 服务 | 说明 |
|------|------|------|------|
| RSS采集 | 每30分钟（:00/:30） | ingestion-worker | 自动采集新文章 |
| 晨报生成 | 每天09:45 | ai-worker | 生成并发送晨报 |
| 周报生成 | 每周一09:45后自动触发 | ai-worker | 晨报生成后自动生成周报（覆盖过去7天） |

**配置位置**: `.env`文件中的`DAILY_REPORT_TIME`、`WEEKLY_REPORT_DAY`等

## 🎯 AI提示词工程

Z-Pulse 采用了一套精心设计的提示词系统，确保生成高质量、专业且符合财政领域要求的报告。

### 晨报生成提示词（Smart Brevity 风格）

**核心理念**：融合 Axios Smart Brevity 的"模块化、视觉焦点、直击要害"风格，保持专业严谨与事实准确。

**关键约束**：
- ✅ **事实优先**：只使用材料中出现的事实，严禁编造金额/数字/机构/政策细则
- ✅ **单一焦点**：今日焦点必须围绕"最具省级影响的单一事件/政策动作"，禁止拼盘式罗列
- ✅ **覆盖面要求**：引用至少3篇材料，覆盖至少2个地市（杭州/宁波/温州/嘉兴/湖州/绍兴/金华/衢州/舟山/台州/丽水）
- ✅ **标题粒度**：最低粒度为"市级"，禁止出现具体"县/区/镇/乡"等过细地名
- ✅ **简洁精炼**：总字数控制在400字以内（不含sources），每句话都有信息量

**输出结构**（JSON格式）：
```json
{
  "schema": "smart_brevity_v1",
  "focus_topic": "今日焦点主题（不超过12字）",
  "visual_focus": "common_issue|high_impact_event",
  "header": {
    "title": "不超过20字的实词标题",
    "date": "YYYY-MM-DD",
    "lede": "核心事实（不超过50字）",
    "lede_citations": [1,2]
  },
  "why_it_matters": "财政视角的影响/抓手",
  "why_citations": [1,2,3],
  "big_picture": "关注点/风险点/落地要害",
  "big_picture_citations": [2,4],
  "keywords": [
    {"word":"关键词","weight":100,"source_ids":[1,2]}
  ],
  "sources": [...]
}
```

**提示词位置**：`backend/app/services/daily_briefing/prompts.py:8`

### 近日热点提取提示词

**核心理念**：将每篇文章压缩成"可聚类的事件标签"，用于生成【近日热点】模块。

**质量规则**：
- ✅ **结构化输出**：one_liner（<=20字）+ tags（财政/民生/科创评分）+ keep（是否进入热点）
- ✅ **事件性要求**：必须是"对象+动作/政策工具+动作"结构（如"发放育儿补贴""开通医保报销"）
- ✅ **去模板化**：避免"补贴申领/补助申请"等泛化短语，必须点明具体对象
- ✅ **排除规则**：会议/党建/人事任免；领导活动；纯地名/人名；口号/成效类

**输出格式**：
```json
{
  "one_liner": "发放育儿补贴",
  "tags": {
    "finance": 2,
    "minsheng": 3,
    "tech": 0
  },
  "keep": true
}
```

**提示词位置**：`backend/app/services/daily_briefing/hotspots.py:52`

### 热点聚类提示词

**核心理念**：将相似事件聚成少量热点，并给出编辑级别的事件命名。

**强制规则**：
- ✅ **事件名长度**：优先4-8字（最多12字），必须像事件（对象+动作/政策工具+动作）
- ✅ **来源多样性**：每个事件必须给出2-6个来源，且必须来自输入
- ✅ **真实热点**：必须"重复出现/覆盖多来源"才算热点，孤立事件不输出
- ✅ **去同义**：不同事件之间不能只是换说法（避免"育儿补贴申领"和"申领育儿补贴"同时存在）
- ✅ **多样性约束**：在候选充足时，尽量覆盖民生/财政工具/消费促进/科创等类别

**输出格式**：
```json
{
  "events": [
    {
      "event": "育儿补贴发放",
      "source_ids": [1,2,3],
      "why_hot": "多地集中发放",
      "category": "welfare"
    }
  ]
}
```

**提示词位置**：`backend/app/services/daily_briefing/hotspots.py:293`

### 周报深度洞察提示词

**核心理念**："跳出财政看财政"，从宏观经济、社会趋势、政策周期、区域发展等更广阔视角提供深度洞察。

**核心要求**：
- ✅ **全局视角**：不要逐一分析事件，要从全局视角识别本周最有价值的1个核心洞察
- ✅ **深度洞察**：只有真正发现深刻洞察时才写，要有深度和说服力，有逻辑支撑
- ✅ **跨领域连接**：将财政动态与宏观经济、社会趋势、政策周期、区域发展等更宏观背景联系起来
- ✅ **严格字数控制**：核心洞察550-650字，绝对不能超过700字
- ✅ **自然融入证据**：在分析过程中自然融入2-3个关键事件或数据点，不单独列出"关键证据"部分

**分析维度**：
1. **宏观背景**：本周财政动态反映了什么宏观经济趋势？
2. **政策周期**：在政策周期中的位置和意义？
3. **社会趋势**：与民生、就业、区域发展等社会趋势的关系？
4. **系统性逻辑**：财政资源配置背后的系统性逻辑是什么？
5. **未来影响**：可能带来的影响和趋势？

**提示词位置**：`backend/app/workers/ai_generate.py:2002`

### 提示词版本管理

系统支持提示词版本管理，通过环境变量配置：
- `RECENT_HOTSPOTS_ONELINER_PROMPT_VERSION`：近日热点提取提示词版本（默认：v1）
- 提示词版本变更时会自动重新计算，确保历史数据的一致性

### 提示词优化原则

1. **事实准确**：严禁编造数据，材料未给出的信息必须留空或标注"未披露"
2. **简洁精炼**：删除行政套话（如"进一步、深入、切实、全面、贯彻精神"等）
3. **结构化输出**：使用严格JSON格式，便于程序解析和渲染
4. **覆盖面控制**：确保地域和主题的多样性，避免过度集中单一地区或主题
5. **读者导向**：从读者视角组织信息，优先呈现读者最关心的内容

## 🔑 环境变量配置

请参考项目根目录的`env.example`文件。

## 🛠️ 常用命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f [service-name]

# 重启服务
docker-compose restart [service-name]

# 停止所有服务
docker-compose down
```

### 手动触发任务（调试用）

```bash
# 手动触发采集（通常不需要，系统会自动运行）
docker-compose exec api-backend python -m app.workers.ingest

# 手动生成晨报
docker-compose exec api-backend python -c "from app.workers.ai_generate import AIWorker; AIWorker().generate_daily_report()"
```

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [we-mp-rss](https://github.com/rachelos/we-mp-rss) - 优秀的微信公众号RSS工具
- [阿里云Qwen](https://qwen.ai/) - 强大的中文AI模型
- [BERTopic](https://github.com/MaartenGr/BERTopic) - 主题建模库
- [Next.js](https://nextjs.org/) - React生产框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代Python Web框架

## 📞 支持与反馈

- 📧 **问题反馈**: [GitHub Issues](https://github.com/wang1st/z-pulse/issues)
- 📖 **文档**: [文档中心](docs/README.md)

---

**⭐ 如果这个项目对您有帮助，请给我们一个Star！**
