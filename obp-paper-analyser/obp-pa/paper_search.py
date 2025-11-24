from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from .tavily_client import get_tavily_client


DEFAULT_PAPER_DOMAINS = [
    "arxiv.org",
    "openaccess.thecvf.com",
    "paperswithcode.com",
]


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def search_papers(
    query: str,
    *,
    search_depth: str = "advanced",
    time_range: Optional[str] = "day",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    max_results: int = 10,
    include_raw_content: bool = True,
    auto_parameters: bool = False,
    topic: str = "general",
) -> Dict[str, Any]:
    client = get_tavily_client()

    if include_domains is None:
        include_domains = DEFAULT_PAPER_DOMAINS

    tavily_kwargs: Dict[str, Any] = {
        "search_depth": search_depth,
        "max_results": max_results,
        "include_raw_content": include_raw_content,
        "include_answer": False,
        "include_images": False,
        "include_image_descriptions": False,
        "include_domains": include_domains,
        "exclude_domains": exclude_domains or [],
        "topic": topic,
        "auto_parameters": auto_parameters,
    }

    if start_date and end_date:
        tavily_kwargs["start_date"] = start_date
        tavily_kwargs["end_date"] = end_date
    elif time_range:
        tavily_kwargs["time_range"] = time_range

    response = client.search(query=query, **tavily_kwargs)

    papers: List[Dict[str, Any]] = []

    for idx, r in enumerate(response.get("results", [])):
        url = r.get("url") or ""
        domain = _extract_domain(url)

        if include_domains and domain not in include_domains:
            if not any(domain.endswith(d) for d in include_domains):
                continue

        papers.append(
            {
                "id": idx,
                "title": r.get("title"),
                "url": url,
                "domain": domain,
                "content": r.get("content"),
                "raw_content": r.get("raw_content"),
                "score": r.get("score"),
                "published_date": r.get("published_date"),
            }
        )

    return {
        "query": response.get("query", query),
        "papers": papers,
        "tavily_meta": {
            "auto_parameters": response.get("auto_parameters"),
            "response_time": response.get("response_time"),
            "request_id": response.get("request_id"),
        },
    }
