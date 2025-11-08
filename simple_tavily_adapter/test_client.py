"""
Тест для проверки совместимости с оригинальным Tavily API

Run from package root:
    python -m simple_tavily_adapter.test_client

Or inside Docker container:
    docker compose exec tavily-adapter python -m simple_tavily_adapter.test_client
"""
try:
    # Try relative import first (when run as module)
    from .tavily_client import TavilyClient
except ImportError:
    # Fall back to absolute import (when run as script)
    from tavily_client import TavilyClient

# Тест совместимости с оригинальным API
client = TavilyClient(api_key="fake-key")  # API ключ не используется
response = client.search(
    query="цена bmw x6",
    include_raw_content=True
)

print("Response:")
print(response)
print("\nResults count:", len(response["results"]))
if response["results"]:
    print("First result URL:", response["results"][0]["url"])
    print("First result title:", response["results"][0]["title"])
