"""
Configuration loader for Tavily adapter.

Looks for config.yaml in this order:
1. Environment variable CONFIG_PATH
2. ./config.yaml (local development)
3. /srv/searxng-docker/config.yaml (Docker)
4. Falls back to default config
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any

class Config:
    def __init__(self, config_path: str = None):
        # Determine config path in order of priority
        if config_path:
            # Explicitly provided path
            self.config_path = Path(config_path)
        elif os.getenv("CONFIG_PATH"):
            # Environment variable override
            self.config_path = Path(os.getenv("CONFIG_PATH"))
        elif Path("./config.yaml").exists():
            # Local development (project root)
            self.config_path = Path("./config.yaml")
        elif Path("/srv/searxng-docker/config.yaml").exists():
            # Docker container path
            self.config_path = Path("/srv/searxng-docker/config.yaml")
        else:
            # No config found, will use defaults
            self.config_path = None
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from unified YAML file.
        
        Returns default config if file not found.
        """
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    print(f"✓ Loaded config from: {self.config_path}")
                    return config_data
            except Exception as e:
                print(f"✗ Error loading config from {self.config_path}: {e}")
        else:
            print(f"⚠ Config file not found, using defaults (searxng:8080)")
            if self.config_path:
                print(f"  Tried: {self.config_path}")
        
        # Return default config if file not found or error occurred
        # Fallback to default config (Docker-oriented)
        return {
            "adapter": {
                "searxng_url": "http://searxng:8080",
                "server": {"host": "0.0.0.0", "port": 8000},
                "scraper": {
                    "timeout": 10,
                    "max_content_length": 2500,
                    "user_agent": "Mozilla/5.0 (compatible; TavilyBot/1.0)"
                },
                "search": {
                    "default_max_results": 10,
                    "default_engines": "google,duckduckgo,brave",
                    "cache_ttl_seconds": 120,
                    "cache_max_entries": 256,
                    "response_cache_ttl_seconds": 60,
                    "response_cache_max_entries": 128,
                },
                "extract": {
                    "max_urls": 20,
                    "timeout_basic": 12,
                    "timeout_advanced": 25,
                    "default_format": "markdown"
                }
            }
        }
    
    @property
    def searxng_url(self) -> str:
        # Environment variable override for Azure Container Apps sidecar deployment
        env_url = os.getenv("SEARXNG_URL")
        if env_url:
            return env_url
        return self._config.get("adapter", {}).get("searxng_url", "http://searxng:8080")
    
    @property
    def server_host(self) -> str:
        return self._config.get("adapter", {}).get("server", {}).get("host", "0.0.0.0")
    
    @property
    def server_port(self) -> int:
        return self._config.get("adapter", {}).get("server", {}).get("port", 8000)
    
    @property
    def scraper_timeout(self) -> int:
        return self._config.get("adapter", {}).get("scraper", {}).get("timeout", 10)
    
    @property
    def scraper_max_length(self) -> int:
        return self._config.get("adapter", {}).get("scraper", {}).get("max_content_length", 2500)
    
    @property
    def scraper_user_agent(self) -> str:
        return self._config.get("adapter", {}).get("scraper", {}).get("user_agent", "Mozilla/5.0 (compatible; TavilyBot/1.0)")
    
    @property
    def default_max_results(self) -> int:
        return self._config.get("adapter", {}).get("search", {}).get("default_max_results", 10)
    
    @property
    def default_engines(self) -> str:
        return self._config.get("adapter", {}).get("search", {}).get("default_engines", "google,duckduckgo,brave")

    @property
    def search_cache_ttl(self) -> int:
        return self._config.get("adapter", {}).get("search", {}).get("cache_ttl_seconds", 120)

    @property
    def search_cache_max_entries(self) -> int:
        return self._config.get("adapter", {}).get("search", {}).get("cache_max_entries", 256)

    @property
    def search_response_cache_ttl(self) -> int:
        return self._config.get("adapter", {}).get("search", {}).get("response_cache_ttl_seconds", 60)

    @property
    def search_response_cache_max_entries(self) -> int:
        return self._config.get("adapter", {}).get("search", {}).get("response_cache_max_entries", 128)

    @property
    def extract_max_urls(self) -> int:
        return self._config.get("adapter", {}).get("extract", {}).get("max_urls", 20)

    @property
    def extract_timeout_basic(self) -> int:
        return self._config.get("adapter", {}).get("extract", {}).get("timeout_basic", 12)

    @property
    def extract_timeout_advanced(self) -> int:
        return self._config.get("adapter", {}).get("extract", {}).get("timeout_advanced", 25)

    @property
    def extract_default_format(self) -> str:
        return self._config.get("adapter", {}).get("extract", {}).get("default_format", "markdown")

# Global config singleton used across the adapter
config = Config()
