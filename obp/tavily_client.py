"""Tavily API client wrapper with advanced search parameters."""

from typing import List, Dict, Any, Optional
from tavily import TavilyClient
import logging

from obp.config import settings

logger = logging.getLogger(__name__)


class TavilySearchClient:
    """Enhanced Tavily client with full parameter support."""
    
    def __init__(self):
        self.client = TavilyClient(api_key=settings.tavily_api_key)
    
    def search(
        self,
        query: str,
        search_depth: str = "advanced",
        topic: str = "general",
        time_range: Optional[str] = None,
        max_results: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_raw_content: bool = True,
        include_images: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute Tavily search with advanced parameters."""
        params = {
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
        }
        
        if time_range:
            params["days"] = {"day": 1, "week": 7, "month": 30, "year": 365}.get(time_range, 7)
        
        if include_domains:
            params["include_domains"] = include_domains
        
        if exclude_domains:
            params["exclude_domains"] = exclude_domains
        
        logger.info(f"Tavily search: query='{query}', depth={search_depth}")
        
        try:
            results = self.client.search(**params)
            logger.info(f"Tavily returned {len(results.get('results', []))} results")
            return results
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            raise
    
    def qna(self, query: str, **kwargs) -> str:
        """Execute QnA search to get a direct answer."""
        logger.info(f"Tavily QnA: '{query}'")
        try:
            # qna_search returns a string answer
            return self.client.qna_search(query=query, **kwargs)
        except Exception as e:
            logger.error(f"Tavily QnA failed: {e}")
            return ""

    def get_context(self, query: str, max_tokens: int = 4000, **kwargs) -> str:
        """Get search context (concatenated content) for RAG."""
        logger.info(f"Tavily Context: '{query}'")
        try:
            return self.client.get_search_context(query=query, max_tokens=max_tokens, **kwargs)
        except Exception as e:
            logger.error(f"Tavily Context failed: {e}")
            return ""
            
    def search_images(
        self,
        query: str,
        max_results: int = 20,
        include_domains: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for images using Tavily."""
        results = self.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_domains=include_domains,
            include_images=True,
        )
        
        # Images are in top-level 'images' array
        image_urls = results.get("images", [])
        text_results = results.get("results", [])
        
        images = []
        for i, img_url in enumerate(image_urls[:max_results]):
            # Try to match with text results for context
            context = text_results[i] if i < len(text_results) else {}
            images.append({
                "url": img_url,
                "source_url": context.get("url", ""),
                "title": context.get("title", ""),
                "description": context.get("content", "")[:200],  # Truncate
            })
        
        logger.info(f"Found {len(images)} images for query: {query}")
        return images


# Global client instance (lazy-loaded)
_tavily_client = None

def get_tavily_client():
    """Get or create the global Tavily client instance."""
    global _tavily_client
    if _tavily_client is None:
        _tavily_client = TavilySearchClient()
    return _tavily_client

# Lazy accessor
class _TavilyClientAccessor:
    def __getattr__(self, name):
        return getattr(get_tavily_client(), name)

tavily_client = _TavilyClientAccessor()
