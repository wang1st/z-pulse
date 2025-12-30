-- 数据库初始化脚本

-- 创建数据库（如果不存在）
-- CREATE DATABASE zpulse;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于文本搜索

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 创建全文搜索配置（中文）
-- 注意：需要安装 zhparser 扩展来支持中文分词
-- CREATE TEXT SEARCH CONFIGURATION chinese (PARSER = zhparser);

