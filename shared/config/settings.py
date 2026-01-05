"""
全局配置设置 - 按照设计文档更新
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    PROJECT_NAME: str = "Z-Pulse 财政信息AI晨报系统"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Web配置
    # 默认前端为 3000 端口（与 docker-compose.yml 一致）
    WEB_URL: str = Field(default="http://localhost:3000", env="WEB_URL")
    
    # 数据库配置
    POSTGRES_HOST: str = Field(..., env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, env="POSTGRES_PORT")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    @property
    def DATABASE_URL(self) -> str:
        """构建数据库连接URL"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # Redis配置
    REDIS_HOST: str = Field(default="redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    
    @property
    def REDIS_URL(self) -> str:
        """构建Redis连接URL"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # we-mp-rss (rss-bridge) 配置
    RSS_BRIDGE_URL: str = Field(
        default="http://rss-bridge:8001",
        env="RSS_BRIDGE_URL"
    )
    RSS_BASE_URL: str = Field(
        default="http://localhost:8080",
        env="RSS_BASE_URL"
    )
    WERSS_SECRET_KEY: str = Field(
        default="zpulse-rss",
        env="WERSS_SECRET_KEY"
    )
    
    # 阿里云DashScope (Qwen) 配置
    DASHSCOPE_API_KEY: str = Field(..., env="DASHSCOPE_API_KEY")
    DASHSCOPE_MODEL: str = Field(
        default="qwen-max-latest",
        env="DASHSCOPE_MODEL"
    )
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # 邮件服务配置
    # 支持: sendgrid, brevo (推荐), mailgun
    EMAIL_PROVIDER: str = Field(default="brevo", env="EMAIL_PROVIDER")  # 默认使用Brevo
    SENDGRID_API_KEY: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    BREVO_API_KEY: Optional[str] = Field(default=None, env="BREVO_API_KEY")  # Brevo (原Sendinblue)
    MAILGUN_API_KEY: Optional[str] = Field(default=None, env="MAILGUN_API_KEY")
    MAILGUN_DOMAIN: Optional[str] = Field(default=None, env="MAILGUN_DOMAIN")
    EMAIL_FROM: str = Field(default="noreply@zpulse.com", env="EMAIL_FROM")
    EMAIL_FROM_NAME: str = Field(default="浙财脉动", env="EMAIL_FROM_NAME")
    
    # PDF附件配置
    ENABLE_PDF_ATTACHMENT: bool = Field(default=True, env="ENABLE_PDF_ATTACHMENT")  # 是否在邮件中包含PDF附件
    
    # Worker配置
    POLL_INTERVAL: int = Field(default=1800, env="POLL_INTERVAL")  # 30分钟
    DAILY_REPORT_TIME: str = Field(default="22:00", env="DAILY_REPORT_TIME")
    WEEKLY_REPORT_DAY: str = Field(default="sunday", env="WEEKLY_REPORT_DAY")
    WEEKLY_REPORT_TIME: str = Field(default="22:00", env="WEEKLY_REPORT_TIME")
    
    # JWT配置
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # 通知Webhook（可选，用于we-mp-rss）
    DINGDING_WEBHOOK: Optional[str] = Field(default=None, env="DINGDING_WEBHOOK")
    WECHAT_WEBHOOK: Optional[str] = Field(default=None, env="WECHAT_WEBHOOK")
    FEISHU_WEBHOOK: Optional[str] = Field(default=None, env="FEISHU_WEBHOOK")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
