# Multi-stage build: 依赖安装 + 运行时镜像
FROM python:3.13-slim AS builder

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONUNBUFFERED=1

# 设置 Debian 和 PyPI 镜像源
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip install --no-cache-dir poetry==2.0.0

WORKDIR /app
COPY pyproject.toml poetry.lock* ./

# 直接安装依赖到系统环境
RUN poetry install --only main --no-root --no-directory --no-ansi

# 运行时镜像
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    PYTHONPATH=/app:/app/media_crawler \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 设置 Debian 镜像源
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

# 安装 Playwright 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libc6 libcairo2 \
    libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libglib2.0-0 \
    libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 \
    libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 \
    libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 \
    libxtst6 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从 builder 复制已安装的 Python 包
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 安装 Playwright 浏览器
RUN playwright install chromium && playwright install-deps chromium

# 复制应用代码
COPY . .

# 复制环境配置文件
COPY .env.example .env

# 创建必要的目录和用户
RUN groupadd -g 1000 appgroup \
    && useradd -m -u 1000 -g appgroup appuser \
    && mkdir -p /app/data /app/logs /app/browser_data \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 9090

CMD ["python", "main.py"]