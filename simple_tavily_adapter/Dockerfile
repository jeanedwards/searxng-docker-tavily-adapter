FROM python:3.12-slim

# Base system packages + curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/simple_tavily_adapter/requirements.txt
RUN pip install --no-cache-dir -r /app/simple_tavily_adapter/requirements.txt

# Download Playwright Chromium browser binaries for crawl4ai
# Includes all required system dependencies
RUN python -m playwright install --with-deps chromium

# Copy all package files into proper package structure
COPY . /app/simple_tavily_adapter/

# Make entrypoint script executable
RUN chmod +x /app/simple_tavily_adapter/entrypoint.sh

EXPOSE 8001

# Use entrypoint script to handle config injection for Azure deployment
ENTRYPOINT ["/app/simple_tavily_adapter/entrypoint.sh"]
