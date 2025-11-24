from typing import List, Dict, Any, Optional
import logging
import re
import requests
from pathlib import Path
import hashlib
import mimetypes
from datetime import datetime

from obp.tavily_client import tavily_client
from obp.db import get_resources_collection, get_requests_collection
from obp.config import settings

logger = logging.getLogger(__name__)

class FoundationalGatherer:
    """
    A multi-modal data gathering agent using Tavily's advanced features.
    Supports: Text, Image, Audio, Video, 3D, Code, Numerical, News.
    Handles: Gathering links (Source), Sampling (Download), Storage (DB).
    """
    def __init__(self):
        self.client = tavily_client
        self.resources_col = get_resources_collection()
        self.requests_col = get_requests_collection()
        
        # Cache directory for samples
        self.sample_dir = settings.cache_dir / "samples"
        self.sample_dir.mkdir(parents=True, exist_ok=True)

    def _extract_asset_urls(
        self,
        item: Dict[str, Any],
        exts: tuple,
        allowed_hosts: Optional[List[str]] = None,
    ) -> List[str]:
        """Extract direct asset URLs (e.g., .mp3/.mp4/.obj) from Tavily result.

        Looks at both the primary URL and any URLs mentioned in the content/raw_content
        fields, then filters by extension and (optionally) host substring.
        """
        candidates: List[str] = []

        primary = item.get("url") or ""
        if primary:
            candidates.append(primary)

        content = item.get("content") or item.get("raw_content") or ""
        if content:
            for match in re.findall(r"https?://[^\s\"'<>]+", content):
                candidates.append(match)

        seen = set()
        urls: List[str] = []
        for u in candidates:
            lu = u.lower().strip()
            if not lu:
                continue
            if allowed_hosts and not any(host in lu for host in allowed_hosts):
                continue
            if not any(lu.endswith(ext) for ext in exts):
                continue
            if u in seen:
                continue
            seen.add(u)
            urls.append(u)

        return urls

    def gather_and_store(self, query: str, modality: str, request_id: str, limit: int = 10) -> int:
        """
        Step 1: Gather links and store metadata in DB (status='discovered').
        Does NOT download full content yet.
        """
        # Reuse any existing resources (regardless of status) to avoid duplicate Tavily calls
        existing = self.resources_col.count_documents({
            "request_id": request_id,
            "query": query,
            "modality": modality,
        })

        if existing >= limit:
            logger.info(
                f"Reuse existing resources for request={request_id}, query='{query}', modality={modality}: {existing} items"
            )
            return existing

        result = self.gather(query, modality, limit)
        data_items = result.get("data", [])
        
        stored_count = 0
        for item in data_items:
            # Dedupe logic (simple url hash)
            url = item.get("url", "")
            if not url: continue
            
            doc = {
                "request_id": request_id,
                "query": query,
                "modality": modality,
                "url": url,
                "title": item.get("title", ""),
                "content_snippet": item.get("content") or item.get("description", ""),
                "status": "discovered",
                "created_at": datetime.utcnow(),
                "metadata": item
            }
            
            # Upsert to avoid duplicates for same request
            self.resources_col.update_one(
                {"request_id": request_id, "url": url},
                {"$set": doc},
                upsert=True
            )
            stored_count += 1
            
        logger.info(f"Stored {stored_count} resources for request {request_id}")
        return stored_count

    def sample_resources(self, request_id: str, count_per_modality: int = 1) -> int:
        """
        Step 2: Download samples for discovered resources.
        Updates DB with sample_path.
        """
        # Find discovered items
        cursor = self.resources_col.find({"request_id": request_id, "status": "discovered"})
        
        processed = 0
        for doc in cursor:
            if processed >= count_per_modality:
                break
            
            url = doc["url"]
            modality = doc["modality"]
            
            try:
                logger.info(f"Marking sampled resource {url} ({modality}) without local download...")

                # For sampling in the UI, we only need metadata/snippets from MongoDB.
                # Avoid downloading files to the local filesystem; just mark as sampled.
                self.resources_col.update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "status": "sampled",
                            "sampled_at": datetime.utcnow()
                        }
                    }
                )
                processed += 1
                
            except Exception as e:
                logger.error(f"Failed to sample {url}: {e}")
                self.resources_col.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"status": "error", "error": str(e)}}
                )
                
        return processed

    def _download_file(self, url: str) -> Optional[Path]:
        """Download a file from URL to sample directory.

        Mirrors the extension heuristics in FoundationalDownloader so that
        media and 3D assets get correct file extensions instead of generic .bin.
        """
        try:
            headers = {"User-Agent": "DatasetSmith/1.0"}
            # Use stream=True to avoid loading large files in memory
            with requests.get(url, headers=headers, stream=True, timeout=15) as r:
                r.raise_for_status()

                # Determine extension
                content_type = r.headers.get("content-type", "").split(";")[0]
                ext = mimetypes.guess_extension(content_type) or ""

                # Fall back to URL-based heuristics for common formats
                if not ext:
                    lower = url.lower()
                    if lower.endswith((".jpg", ".jpeg")): ext = ".jpg"
                    elif lower.endswith(".png"): ext = ".png"
                    elif lower.endswith(".gif"): ext = ".gif"
                    elif lower.endswith(".webp"): ext = ".webp"
                    # Audio
                    elif lower.endswith(".mp3"): ext = ".mp3"
                    elif lower.endswith(".wav"): ext = ".wav"
                    elif lower.endswith(".flac"): ext = ".flac"
                    elif lower.endswith(".ogg"): ext = ".ogg"
                    elif lower.endswith(".m4a"): ext = ".m4a"
                    # Video
                    elif lower.endswith(".mp4"): ext = ".mp4"
                    elif lower.endswith(".webm"): ext = ".webm"
                    elif lower.endswith(".m4v"): ext = ".m4v"
                    elif lower.endswith(".mov"): ext = ".mov"
                    elif lower.endswith(".avi"): ext = ".avi"
                    elif lower.endswith(".mkv"): ext = ".mkv"
                    # 3D
                    elif lower.endswith(".obj"): ext = ".obj"
                    elif lower.endswith(".glb"): ext = ".glb"
                    elif lower.endswith(".gltf"): ext = ".gltf"
                    elif lower.endswith(".stl"): ext = ".stl"
                    elif lower.endswith(".fbx"): ext = ".fbx"
                    elif lower.endswith(".ply"): ext = ".ply"
                    # HTML (for text-like only; exporter decides whether to convert/skip)
                    elif ".html" in lower: ext = ".html"
                    else:
                        ext = ".bin"

                # Hash url for filename
                filename = hashlib.md5(url.encode()).hexdigest() + ext
                path = self.sample_dir / filename

                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)

                return path
        except Exception as e:
            logger.warning(f"Download failed for {url}: {e}")
            return None

    def gather(self, query: str, modality: str = "text", limit: int = 5) -> Dict[str, Any]:
        """
        Gather data based on modality.
        Modalities: text, image, audio, video, 3d, code, numerical, news, qna
        """
        logger.info(f"Gathering '{modality}' data for: {query}")
        
        modality = (modality or "text").lower()
        
        # Treat both "image" and "images" as the image modality so that
        # plans that return "images" still route through the image gatherer.
        if modality in ("image", "images"):
            return self._gather_images(query, limit)
        elif modality == "text":
            return self._gather_text(query, limit)
        elif modality == "news":
            return self._gather_news(query, limit)
        elif modality == "code":
            return self._gather_code(query, limit)
        elif modality == "audio":
            return self._gather_media(query, "audio", limit)
        elif modality == "video":
            return self._gather_media(query, "video", limit)
        elif modality == "3d":
            return self._gather_3d(query, limit)
        elif modality == "numerical":
            return self._gather_numerical(query, limit)
        elif modality == "qna":
            return self._gather_qna(query)
        else:
            return self._gather_text(query, limit)

    def _gather_images(self, query: str, limit: int) -> Dict[str, Any]:
        images = self.client.search_images(query, max_results=limit)
        return {"modality": "image", "count": len(images), "data": images}

    def _gather_text(self, query: str, limit: int) -> Dict[str, Any]:
        # Get comprehensive text context
        context = self.client.get_context(query)
        results = self.client.search(query, max_results=limit, include_raw_content=True)
        return {
            "modality": "text", 
            "count": len(results.get("results", [])),
            "summary_snippet": context[:500] + "..." if context else "",
            "full_context": context,
            "data": results.get("results", [])
        }

    def _gather_news(self, query: str, limit: int) -> Dict[str, Any]:
        results = self.client.search(query, topic="news", max_results=limit)
        return {
            "modality": "news",
            "count": len(results.get("results", [])),
            "data": results.get("results", [])
        }

    def _gather_code(self, query: str, limit: int) -> Dict[str, Any]:
        # Target code repositories
        refined_query = f"{query} site:github.com OR site:stackoverflow.com OR site:gitlab.com"
        results = self.client.search(refined_query, max_results=limit, include_raw_content=True)
        return {
            "modality": "code",
            "count": len(results.get("results", [])),
            "data": results.get("results", [])
        }

    def _gather_media(self, query: str, type_: str, limit: int) -> Dict[str, Any]:
        """Gather media links, resolving to direct downloadable assets when possible.

        Strategy:
        - Use Tavily with filetype filters and domain hints.
        - For each result, mine its content for direct asset URLs (.mp3/.wav/.mp4/etc.).
        - Return items whose `url` fields point at those assets.
        - Do NOT fall back to arbitrary HTML pages; if no assets are found, return 0.
        """
        if type_ == "audio":
            modifiers = (
                "audio sound music "
                "filetype:mp3 OR filetype:wav OR filetype:flac OR filetype:ogg "
            )
            exts = (".mp3", ".wav", ".flac", ".ogg", ".m4a")
        else:  # video
            modifiers = (
                "video "
                "filetype:mp4 OR filetype:webm OR filetype:m4v OR filetype:mov OR filetype:avi "
            )
            exts = (".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv")

        refined_query = f"{query} {modifiers}"
        max_results = max(limit * 3, 10)
        results = self.client.search(
            refined_query,
            max_results=max_results,
            include_raw_content=True,
        )

        raw_items = results.get("results", []) or []
        resolved: List[Dict[str, Any]] = []

        # Resolve asset URLs from Tavily results
        for item in raw_items:
            asset_urls = self._extract_asset_urls(item, exts, allowed_hosts=None)
            for asset_url in asset_urls:
                new_item = dict(item)
                new_item["url"] = asset_url
                resolved.append(new_item)
                if len(resolved) >= limit:
                    break
            if len(resolved) >= limit:
                break

        logger.info(
            f"Media gather ({type_}): {len(raw_items)} raw, {len(resolved)} resolved asset URLs"
        )

        return {
            "modality": type_,
            "count": len(resolved),
            "data": resolved,
        }

    def _gather_3d(self, query: str, limit: int) -> Dict[str, Any]:
        """Gather 3D assets, resolving to direct downloadable model files when possible."""
        modifiers = (
            "3d model download "
            "filetype:obj OR filetype:glb OR filetype:gltf OR filetype:stl OR filetype:fbx OR filetype:ply "
        )
        exts = (".obj", ".glb", ".gltf", ".stl", ".fbx", ".ply")

        refined_query = f"{query} {modifiers}"
        max_results = max(limit * 3, 10)
        results = self.client.search(
            refined_query,
            max_results=max_results,
            include_raw_content=True,
        )

        raw_items = results.get("results", []) or []
        resolved: List[Dict[str, Any]] = []

        # Resolve asset URLs from Tavily results
        for item in raw_items:
            asset_urls = self._extract_asset_urls(item, exts, allowed_hosts=None)
            for asset_url in asset_urls:
                new_item = dict(item)
                new_item["url"] = asset_url
                resolved.append(new_item)
                if len(resolved) >= limit:
                    break
            if len(resolved) >= limit:
                break

        logger.info(
            f"3D gather: {len(raw_items)} raw, {len(resolved)} resolved asset URLs"
        )

        return {
            "modality": "3d",
            "count": len(resolved),
            "data": resolved,
        }

    def _normalize_numerical_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rewrite known numerical dataset hosts to point to CSV/TSV endpoints.

        This is a best-effort normalization so downstream downloaders see
        real tabular files instead of HTML landing pages.
        """
        normalized: List[Dict[str, Any]] = []
        for item in items:
            url = item.get("url") or ""
            lower = url.lower()

            # Our World In Data grapher endpoints: allow CSV access by appending .csv
            if "ourworldindata.org/grapher/" in lower and not lower.endswith(".csv"):
                base, sep, query = url.partition("?")
                if not base.endswith(".csv"):
                    base = base + ".csv"
                new_url = base + (sep + query if sep else "")
                if new_url != url:
                    # Copy to avoid mutating shared dicts
                    item = dict(item)
                    item["url"] = new_url
                    logger.info(f"Rewriting numerical URL to CSV endpoint: {url} -> {new_url}")

            normalized.append(item)

        return normalized

    def _gather_numerical(self, query: str, limit: int) -> Dict[str, Any]:
        modifiers = "dataset statistics table data csv tsv xlsx xls json"
        refined_query = f"{query} {modifiers}"
        max_results = max(limit * 3, 10)
        results = self.client.search(
            refined_query,
            max_results=max_results,
            include_raw_content=True,
        )

        raw_items = results.get("results", []) or []
        raw_items = self._normalize_numerical_items(raw_items)

        preferred_exts = (".csv", ".tsv", ".xlsx", ".xls", ".json")
        preferred_substrings = (
            "/download",
            "/downloads",
            "/dataset",
            "/data",
            "api.",
            "/api/",
            "ourworldindata.org",
            "datahub.io",
        )

        filtered: List[Dict[str, Any]] = []

        for item in raw_items:
            url = (item.get("url") or "").lower()
            title = (item.get("title") or "").lower()
            content = (item.get("content") or item.get("raw_content") or "").lower()

            is_ext_match = any(url.endswith(ext) for ext in preferred_exts)
            is_url_hint = any(hint in url for hint in preferred_substrings)
            has_table_hint = "<table" in content or "csv" in content or "comma-separated" in content

            if is_ext_match or is_url_hint or has_table_hint:
                filtered.append(item)
                if len(filtered) >= limit:
                    break

        data_items = filtered if filtered else raw_items[:limit]

        return {
            "modality": "numerical",
            "count": len(data_items),
            "data": data_items,
        }

    def _gather_qna(self, query: str) -> Dict[str, Any]:
        answer = self.client.qna(query)
        return {
            "modality": "qna",
            "answer": answer,
            "data": [] # No resource data usually
        }
