"""
Compatibility smoke test for the Tavily adapter.

Run from package root:
    python -m simple_tavily_adapter.test_client

Or inside Docker:
    docker compose exec tavily-adapter python -m simple_tavily_adapter.test_client
"""
try:
    # Try relative import first (when run as module)
    from .tavily_client import TavilyClient
except ImportError:
    # Fall back to absolute import (when run as script)
    from tavily_client import TavilyClient

# Compatibility check against the original API contract
client = TavilyClient(api_key="fake-key")  # Adapter ignores the API key
response = client.search(
    query="bmw x6 price",
    include_raw_content=True
)

print("Response:")
print(response)
print("\nResults count:", len(response["results"]))
if response["results"]:
    print("First result URL:", response["results"][0]["url"])
    print("First result title:", response["results"][0]["title"])
