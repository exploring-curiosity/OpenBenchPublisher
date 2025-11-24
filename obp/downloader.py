import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import requests
import mimetypes
import hashlib

from gridfs import GridFS

from obp.db import get_resources_collection, get_db

logger = logging.getLogger(__name__)

class FoundationalDownloader:
    """
    Separate functionality for downloading full datasets.
    Triggered independently or via pipeline.
    """
    def __init__(self):
        self.resources_col = get_resources_collection()
        # Store full downloaded content in MongoDB via GridFS instead of local disk
        self._db = get_db()
        self._fs = GridFS(self._db, collection="resources_files")

    def download_all(self, request_id: str) -> int:
        """Download all discovered resources for a request and store bytes in MongoDB.

        Each successfully downloaded resource is written to a GridFS collection and
        the corresponding resource document is updated with:

        - status: "downloaded"
        - content_blob_id: ObjectId of the GridFS file
        - content_type: best-effort MIME type
        - filename: stable hashed filename with extension
        - downloaded_at: timestamp
        """
        logger.info(f"Starting full download for request {request_id}")
        cursor = self.resources_col.find({
            "request_id": request_id,
            "status": {"$in": ["discovered", "sampled"]},
        })

        count = 0
        for doc in cursor:
            url = doc["url"]
            try:
                logger.info(f"Downloading {url}...")
                result = self._download_file(url)
                if result:
                    blob_id, content_type, filename = result
                    self.resources_col.update_one(
                        {"_id": doc["_id"]},
                        {
                            "$set": {
                                "status": "downloaded",
                                "content_blob_id": blob_id,
                                "content_type": content_type,
                                "filename": filename,
                                "downloaded_at": datetime.utcnow(),
                            }
                        },
                    )
                    count += 1
            except Exception as e:
                logger.error(f"Download failed {url}: {e}")

        logger.info(f"Downloaded {count} files for request {request_id}")
        return count

    def _download_file(self, url: str) -> Optional[Tuple[object, str, str]]:
        """Download a single URL and stream it directly into GridFS.

        Returns a tuple of (blob_id, content_type, filename) on success, or None on failure.
        """
        try:
            headers = {"User-Agent": "DatasetSmith/1.0"}
            with requests.get(url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                content_type = r.headers.get("content-type", "").split(";")[0]
                ext = mimetypes.guess_extension(content_type) or ""

                # Fall back to URL-based heuristics for common media / 3D formats
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

                filename = hashlib.md5(url.encode()).hexdigest() + ext

                grid_in = self._fs.new_file(filename=filename, content_type=content_type, url=url)
                try:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            grid_in.write(chunk)
                finally:
                    grid_in.close()

                blob_id = grid_in._id
                return blob_id, content_type, filename
        except Exception as e:
            logger.warning(f"Download error for {url}: {e}")
            return None
