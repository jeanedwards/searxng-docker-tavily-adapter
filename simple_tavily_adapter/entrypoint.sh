#!/bin/bash
set -e

# Entrypoint script for Tavily Adapter
# Handles configuration injection for Azure Container Apps deployment

echo "=========================================="
echo "Tavily Adapter Entrypoint - Starting"
echo "=========================================="
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Available environment variables:"
env | grep -E "(CONFIG|SEARXNG|PORT)" || echo "No relevant env vars found"
echo "=========================================="

# Default config path expected by the application
CONFIG_PATH="/srv/searxng-docker/config.yaml"
CONFIG_DIR=$(dirname "$CONFIG_PATH")

# Create config directory if it doesn't exist
echo "INFO: Creating config directory: $CONFIG_DIR"
mkdir -p "$CONFIG_DIR"

# Check if CONFIG_YAML environment variable is set (Azure deployment)
if [ -n "$CONFIG_YAML" ]; then
    echo "INFO: CONFIG_YAML environment variable detected (length: ${#CONFIG_YAML} chars)"
    echo "INFO: Writing configuration to $CONFIG_PATH"
    
    # Write the config from environment variable to file
    echo "$CONFIG_YAML" > "$CONFIG_PATH"
    
    # Verify the file was created successfully
    if [ -f "$CONFIG_PATH" ]; then
        echo "INFO: Configuration file created successfully"
        echo "INFO: File size: $(wc -c < "$CONFIG_PATH") bytes"
        echo "INFO: Config file starts with:"
        head -n 10 "$CONFIG_PATH" | grep -v "secret_key" || echo "(config preview)"
    else
        echo "ERROR: Failed to create configuration file"
        exit 1
    fi
elif [ -f "$CONFIG_PATH" ]; then
    # Config file exists (Docker Compose with volume mount)
    echo "INFO: Using existing configuration file at $CONFIG_PATH"
    echo "INFO: File size: $(wc -c < "$CONFIG_PATH") bytes"
else
    # No config available - warn but continue (app will use defaults or fail)
    echo "WARNING: No configuration found!"
    echo "WARNING: CONFIG_YAML environment variable not set and no config file at $CONFIG_PATH"
    echo "WARNING: Application will attempt to use default configuration"
fi

# List files in app directory for debugging
echo "INFO: Files in /app directory:"
ls -la /app/ | head -n 15

# Start the application with uvicorn
echo "=========================================="
echo "INFO: Starting Tavily Adapter on 0.0.0.0:8000"
echo "=========================================="
exec uvicorn main:app --host 0.0.0.0 --port 8000

