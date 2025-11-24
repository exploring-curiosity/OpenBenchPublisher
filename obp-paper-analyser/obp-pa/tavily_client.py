from typing import Optional

from tavily import TavilyClient

from .config import settings


_client: Optional[TavilyClient] = None


def get_tavily_client() -> TavilyClient:
    global _client

    if _client is None:
        if not settings.has_tavily_key:
            raise RuntimeError(
                "TAVILY_API_KEY is not set. Export it before running."
            )
        _client = TavilyClient(api_key=settings.tavily_api_key)

    return _client
