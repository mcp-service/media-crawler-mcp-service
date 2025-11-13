# multi-stage: build dependencies once, ship lightweight runtime
FROM python:3.13-slim AS builder

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==2.0.0

WORKDIR /app
COPY pyproject.toml poetry.lock* ./

# Install dependencies strictly from poetry.lock into the system env
RUN poetry install --only main --no-root --no-directory --no-ansi

FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    PYTHONPATH=/app:/app/media_crawler \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    APP_HOST=0.0.0.0 \
    APP_PORT=9090

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget gnupg \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libc6 libcairo2 \
    libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libglib2.0-0 \
    libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 \
    libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 \
    libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 \
   libxtst6 xdg-utils \
   && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages and entrypoints from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Install Playwright with increased timeout and retries
ENV PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=60000
RUN playwright install chromium --with-deps || \
    (sleep 5 && playwright install chromium --with-deps) || \
    (sleep 10 && playwright install chromium --with-deps)

COPY . .

RUN groupadd -g 1000 appgroup \
 && useradd -m -u 1000 -g appgroup appuser \
 && mkdir -p /app/data /app/logs /app/browser_data \
 && chown -R appuser:appgroup /app

USER appuser

EXPOSE 9090

CMD ["python", "main.py"]
