"""
AI处理器
"""
from datetime import datetime
from typing import Dict, List
from sqlalchemy.orm import Session
from openai import OpenAI
import json

from shared.config import settings
from shared.database import (
    Article, Report, ReportItem, OfficialAccount,
    ArticleStatus, ReportType
)
from shared.utils import get_logger

logger = get_logger("ai-processor.processor")


class ArticleProcessor:
    """文章处理器"""
    
    def __init__(self, db: Session):
        """
        初始化处理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
    
    def process_article(self, article_id: int) -> Dict:
        """
        处理文章
        
        分析文章内容，提取：
        1. 摘要
        2. 关键词
        3. 分类
        4. 情感分数
        5. 重要性分数
        
        Args:
            article_id: 文章ID
        
        Returns:
            处理结果
        """
        article = self.db.query(Article).filter(
            Article.id == article_id
        ).first()
        
        if not article:
            raise ValueError(f"Article {article_id} not found")
        
        try:
            logger.info(f"Processing article {article_id}: {article.title[:50]}...")
            
            # 构建提示词
            prompt = self._build_analysis_prompt(article)
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的财政信息分析专家，擅长分析财政相关的新闻和公告。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            # 解析结果
            result = json.loads(response.choices[0].message.content)
            
            # 更新文章
            article.summary = result.get("summary", "")
            article.keywords = result.get("keywords", [])
            article.category = result.get("category", "")
            article.sentiment_score = result.get("sentiment_score", 0)
            article.importance_score = result.get("importance_score", 50)
            article.status = ArticleStatus.PROCESSED
            article.processed_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Article {article_id} processed successfully")
            
            return {
                "article_id": article_id,
                "summary": article.summary,
                "keywords": article.keywords,
                "category": article.category,
                "importance_score": article.importance_score
            }
            
        except Exception as e:
            logger.error(f"Failed to process article {article_id}: {str(e)}")
            article.status = ArticleStatus.FAILED
            article.error_message = str(e)
            self.db.commit()
            raise
    
    def _build_analysis_prompt(self, article: Article) -> str:
        """
        构建分析提示词
        
        Args:
            article: 文章对象
        
        Returns:
            提示词字符串
        """
        return f"""
请分析以下财政信息文章，返回JSON格式的结果：

标题：{article.title}

内容：
{article.content[:2000]}  # 限制长度

请提供以下分析结果（JSON格式）：
{{
    "summary": "文章摘要（100-200字）",
    "keywords": ["关键词1", "关键词2", "关键词3", ...],  // 3-5个关键词
    "category": "分类",  // 如：预算管理、财政政策、税收政策、专项资金、绩效评价等
    "sentiment_score": 0,  // 情感分数 -100到100，0表示中性
    "importance_score": 50  // 重要性分数 0-100
}}

注意：
1. 摘要应该提炼文章的核心内容
2. 关键词要具体且相关
3. 分类要准确
4. 重要性评分要根据文章的影响范围和政策意义
"""


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, db: Session):
        """
        初始化生成器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
    
    def generate_report(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
        regions: List[str] = None
    ) -> Report:
        """
        生成报告
        
        Args:
            report_type: 报告类型 (daily/weekly/monthly)
            start_date: 开始日期
            end_date: 结束日期
            regions: 地区列表（可选）
        
        Returns:
            报告对象
        """
        logger.info(
            f"Generating {report_type} report from {start_date} to {end_date}"
        )
        
        # 获取时间范围内的文章
        query = self.db.query(Article).filter(
            Article.published_at >= start_date,
            Article.published_at <= end_date,
            Article.status == ArticleStatus.PROCESSED
        )
        
        # 如果指定了地区，进行过滤
        if regions:
            query = query.join(OfficialAccount).filter(
                OfficialAccount.region.in_(regions)
            )
        
        # 按重要性排序
        articles = query.order_by(
            Article.importance_score.desc()
        ).limit(50).all()
        
        if not articles:
            raise ValueError("No articles found in the specified date range")
        
        # 生成报告内容
        report_content = self._generate_report_content(
            articles,
            report_type,
            start_date,
            end_date
        )
        
        # 创建报告
        report = Report(
            title=self._generate_report_title(report_type, start_date, end_date),
            report_type=ReportType(report_type),
            content=report_content,
            article_count=len(articles),
            start_date=start_date,
            end_date=end_date,
            generated_by="ai-processor"
        )
        
        self.db.add(report)
        self.db.flush()
        
        # 添加报告项目
        for index, article in enumerate(articles):
            report_item = ReportItem(
                report_id=report.id,
                article_id=article.id,
                order=index,
                weight=article.importance_score
            )
            self.db.add(report_item)
        
        self.db.commit()
        
        logger.info(f"Report generated: {report.id}")
        
        return report
    
    def _generate_report_title(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """
        生成报告标题
        
        Args:
            report_type: 报告类型
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            标题字符串
        """
        type_name = {
            "daily": "日报",
            "weekly": "周报",
            "monthly": "月报"
        }.get(report_type, "报告")
        
        return f"财政信息{type_name} - {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
    
    def _generate_report_content(
        self,
        articles: List[Article],
        report_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """
        生成报告内容
        
        Args:
            articles: 文章列表
            report_type: 报告类型
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            报告内容（Markdown格式）
        """
        # 准备文章摘要
        articles_summary = []
        for article in articles[:20]:  # 只取前20篇最重要的
            articles_summary.append({
                "title": article.title,
                "summary": article.summary,
                "category": article.category,
                "account": article.account.name,
                "importance": article.importance_score
            })
        
        # 构建提示词
        prompt = f"""
请基于以下财政信息文章，生成一份{report_type}报告（{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}）。

文章列表：
{json.dumps(articles_summary, ensure_ascii=False, indent=2)}

报告要求：
1. 使用Markdown格式
2. 包含以下章节：
   - 摘要（总体概述）
   - 重要政策动态
   - 分类汇总（按类别分组）
   - 重点关注事项
3. 语言专业、简洁
4. 突出重点信息
5. 字数控制在1000-2000字

请生成报告内容：
"""
        
        # 调用OpenAI API
        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的财政分析师，擅长撰写财政信息报告。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content
        
        # 添加文章列表附录
        content += "\n\n## 附录：文章列表\n\n"
        for index, article in enumerate(articles, 1):
            content += f"{index}. **{article.title}**\n"
            content += f"   - 来源：{article.account.name}\n"
            content += f"   - 分类：{article.category}\n"
            content += f"   - 摘要：{article.summary}\n\n"
        
        return content

