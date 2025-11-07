#!/bin/bash
set -e

# Entrypoint script for Tavily Adapter
# Handles configuration injection for Azure Container Apps deployment

# Default config path expected by the application
CONFIG_PATH="/srv/searxng-docker/config.yaml"
CONFIG_DIR=$(dirname "$CONFIG_PATH")

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Check if CONFIG_YAML environment variable is set (Azure deployment)
if [ -n "$CONFIG_YAML" ]; then
    echo "INFO: CONFIG_YAML environment variable detected"
    echo "INFO: Writing configuration to $CONFIG_PATH"
    
    # Write the config from environment variable to file
    echo "$CONFIG_YAML" > "$CONFIG_PATH"
    
    # Verify the file was created successfully
    if [ -f "$CONFIG_PATH" ]; then
        echo "INFO: Configuration file created successfully"
        # Display first few lines for verification (without sensitive data)
        echo "INFO: Config file starts with:"
        head -n 5 "$CONFIG_PATH"
    else
        echo "ERROR: Failed to create configuration file"
        exit 1
    fi
elif [ -f "$CONFIG_PATH" ]; then
    # Config file exists (Docker Compose with volume mount)
    echo "INFO: Using existing configuration file at $CONFIG_PATH"
else
    # No config available - warn but continue (app will use defaults or fail)
    echo "WARNING: No configuration found!"
    echo "WARNING: CONFIG_YAML environment variable not set and no config file at $CONFIG_PATH"
    echo "WARNING: Application will attempt to use default configuration"
fi

# Start the application with uvicorn
echo "INFO: Starting Tavily Adapter on 0.0.0.0:8000"
exec uvicorn main:app --host 0.0.0.0 --port 8000

