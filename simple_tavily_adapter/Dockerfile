FROM python:3.11-slim

# Базовые пакеты + curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скачиваем браузеры Playwright для crawl4ai
# Скачиваем браузеры Playwright + системные зависимости
RUN python -m playwright install --with-deps chromium

COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

EXPOSE 8000

# Use entrypoint script to handle config injection for Azure deployment
ENTRYPOINT ["/app/entrypoint.sh"]
