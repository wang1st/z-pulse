FROM python:3.11-slim

WORKDIR /app

# 配置 Debian 镜像源（使用阿里云镜像，加速国内访问）
# python:3.11-slim 基于 Debian 12 (bookworm)
# 先备份原有配置，然后替换为阿里云镜像
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
        sed -i 's|https://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list && \
        sed -i 's|https://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list && \
        sed -i 's|http://security.debian.org|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list; \
    else \
        echo "deb http://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
        echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
        echo "deb http://mirrors.aliyun.com/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
    fi

# 安装系统依赖和WeasyPrint依赖
# 优化：使用 --no-install-recommends 减少包数量，降低内存使用
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    curl \
    python3-dev \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件
COPY backend/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 预下载BERTopic使用的sentence-transformers模型（避免运行时下载）
# 使用中文（简体）语言模型，这是BERTopic在language="chinese (simplified)"时使用的模型
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')" || \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')" || \
    echo "Model download failed, will download at runtime"

# 复制shared模块（必须在backend之前）
COPY shared ./shared

# 复制backend应用代码
COPY backend ./backend

# 设置工作目录为backend
WORKDIR /app/backend

# 默认命令（可以被docker-compose覆盖）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

