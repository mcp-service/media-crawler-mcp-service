# 推荐方案：Poetry 导出 + pip 安装，支持MediaCrawler

# 第一阶段：使用 Poetry 导出完整的 requirements.txt
FROM python:3.11-slim AS req-generator

# 设置 Debian 镜像源
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

# 设置 PYPI 镜像
ARG PYPI_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PYPI_TRUSTED=pypi.tuna.tsinghua.edu.cn

# Poetry 环境变量
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# 安装 Poetry
RUN pip config set global.index-url ${PYPI_URL} && \
    pip config set install.trusted-host ${PYPI_TRUSTED} && \
    python -m pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir poetry==2.0.0 poetry-plugin-export==1.9.0

# 配置 Poetry
RUN poetry config virtualenvs.create false

WORKDIR /app
COPY pyproject.toml poetry.lock* ./

# 更新 lock 文件（如果 pyproject.toml 有变化）
RUN poetry lock --no-update || poetry lock

# 导出包含所有依赖的 requirements.txt
RUN poetry export \
    --format requirements.txt \
    --output requirements.txt \
    --without-hashes \
    --verbose

# 验证导出结果
RUN echo "=== 导出验证 ===" && \
    echo "总依赖数量: $(wc -l < requirements.txt)" && \
    echo "关键依赖检查:" && \
    grep -E "(fastmcp|playwright|httpx|pydantic)" requirements.txt | head -5 || echo "某些关键依赖可能缺失"

# 第二阶段：运行时镜像，支持Playwright浏览器
FROM python:3.11-slim AS runtime

# 设置 Debian 镜像源
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

# 环境变量设置
ENV API_VERSION=v1.0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION="python" \
    TZ=Asia/Shanghai \
    PYTHONPATH=/app:/app/media_crawler \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 设置 PYPI 镜像
ARG PYPI_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PYPI_TRUSTED=pypi.tuna.tsinghua.edu.cn

# 设置时区
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖 (Playwright需要的依赖)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制生成的 requirements.txt
COPY --from=req-generator /app/requirements.txt ./

# 配置 pip 并安装所有依赖
RUN pip config set global.index-url ${PYPI_URL} && \
    pip config set install.trusted-host ${PYPI_TRUSTED} && \
    python -m pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# 安装Playwright浏览器 (仅安装chromium)
RUN playwright install chromium && \
    playwright install-deps chromium

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/browser_data && \
    chmod -R 755 /app/data /app/logs /app/browser_data

# 创建非 root 用户
RUN adduser -u 5678 --disabled-password --gecos "" appuser && \
    chown -R appuser /app

USER appuser

# 暴露端口
EXPOSE 9090 9091

# 启动命令 (默认SSE模式 + Admin服务)
CMD ["python", "main.py", "--transport", "sse", "--admin"]