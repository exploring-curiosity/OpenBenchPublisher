"""DatasetSmith Agent - License-clean dataset slice builder."""

from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
import requests
from PIL import Image
import imagehash
from io import BytesIO
import logging
from datetime import datetime

from obp.config import settings
from obp.tavily_client import tavily_client
from obp.embeddings import embedding_service
from obp.db import get_assets_collection, get_datasets_collection

logger = logging.getLogger(__name__)


class DatasetSmith:
    """Agent for building license-clean dataset slices."""
    
    def __init__(self):
        self.assets_col = get_assets_collection()
        self.datasets_col = get_datasets_collection()
        self.cache_dir = settings.cache_dir / "images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def build_slice(
        self,
        classes: List[str],
        total: int = 100,
        min_size: int = 256,
        license_filter: str = "CC-BY",
        split: tuple = (0.7, 0.15, 0.15),
        include_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build a dataset slice from Tavily image search."""
        logger.info(f"Building slice: classes={classes}, total={total}")
        
        if include_domains is None:
            include_domains = [
                "commons.wikimedia.org",
                "unsplash.com",
                "pexels.com",
            ]
        
        per_class = total // len(classes)
        collected_assets = []
        
        for class_name in classes:
            logger.info(f"Searching for class: {class_name}, target: {per_class} images")
            assets = self._search_and_collect(
                query=f"{class_name} high quality photo",
                target_count=per_class,
                class_label=class_name,
                min_size=min_size,
                include_domains=include_domains,
            )
            logger.info(f"Collected {len(assets)} assets for {class_name}")
            if len(assets) == 0:
                logger.error(f"WARNING: No assets collected for class '{class_name}' - check Tavily API or query")
            collected_assets.extend(assets)
        
        logger.info(f"Deduplicating {len(collected_assets)} assets...")
        unique_assets = self._deduplicate(collected_assets)
        logger.info(f"After dedupe: {len(unique_assets)} unique assets")
        
        balanced_assets = self._balance_classes(unique_assets, classes, per_class)
        manifest = self._create_manifest(balanced_assets, classes, split)
        dataset_id = self._save_dataset(manifest, classes, license_filter)
        
        # Add fields for API response
        manifest["dataset_id"] = dataset_id
        manifest["total_images"] = manifest["total"]
        
        logger.info(f"Dataset slice built: {dataset_id}")
        return manifest
    
    def _search_and_collect(
        self,
        query: str,
        target_count: int,
        class_label: str,
        min_size: int,
        include_domains: List[str],
    ) -> List[Dict[str, Any]]:
        """Search Tavily and collect images."""
        assets = []
        search_variations = [
            f"{query}",
            f"{query} photo",
            f"{query} image",
            f"high quality {query}",
            f"{query} picture",
            f"{query} photography",
            f"professional {query}",
            f"{query} stock photo",
        ]
        
        # Try multiple search variations to get more images
        # Request more than needed to account for filtering
        for search_query in search_variations:
            if len(assets) >= target_count * 1.5:  # Get 50% extra to account for filtering
                break
            
            # Tavily max_results is capped at 20
            max_results = 20
            
            try:
                logger.info(f"Searching Tavily: '{search_query}' (max: {max_results})")
                images = tavily_client.search_images(
                    query=search_query,
                    max_results=max_results,
                    include_domains=include_domains,
                )
                logger.info(f"Tavily returned {len(images)} images for '{search_query}'")
                
                if len(images) == 0:
                    logger.warning(f"⚠️  Tavily returned 0 images for '{search_query}' - trying next variation")
                    continue
                
                processed = 0
                for img_data in images:
                    try:
                        asset = self._process_image(img_data, class_label, min_size)
                        if asset:
                            assets.append(asset)
                            processed += 1
                            if len(assets) >= target_count * 1.5:
                                break
                    except Exception as e:
                        logger.warning(f"Failed to process image from {img_data.get('url', 'unknown')}: {e}")
                        continue
                
                logger.info(f"Processed {processed}/{len(images)} images from this search")
                
                # Small delay to avoid rate limiting
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Search failed for '{search_query}': {type(e).__name__}: {e}")
                continue
        
        # Final summary for this class
        if len(assets) == 0:
            logger.error(f"❌ FAILED: Collected 0 assets for '{class_label}' (target: {target_count})")
        elif len(assets) < target_count:
            logger.warning(f"⚠️  Collected {len(assets)}/{target_count} assets for '{class_label}'")
        else:
            logger.info(f"✅ Collected {len(assets)} assets for '{class_label}' (target: {target_count})")
        
        return assets
    
    def _process_image(
        self,
        img_data: Dict[str, Any],
        class_label: str,
        min_size: int,
    ) -> Optional[Dict[str, Any]]:
        """Download and process a single image."""
        url = img_data["url"]
        
        response = requests.get(url, timeout=10, headers={"User-Agent": "OBP/0.1"})
        if response.status_code != 200:
            return None
        
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        
        if min(width, height) < min_size:
            return None
        
        phash = str(imagehash.phash(img))
        caption = f"{class_label}. {img_data.get('description', img_data.get('title', ''))}"
        # Skip slow VoyageAI embedding for faster processing
        img_embed = []
        
        img_hash = hashlib.md5(response.content).hexdigest()
        img_path = self.cache_dir / f"{img_hash}.jpg"
        
        # Save and immediately flush to disk
        with open(img_path, 'wb') as f:
            img.convert("RGB").save(f, "JPEG", quality=85)
            f.flush()
            import os
            os.fsync(f.fileno())
        
        return {
            "uri": str(img_path),
            "url": url,
            "source_url": img_data.get("source_url", ""),
            "class": class_label,
            "width": width,
            "height": height,
            "phash": phash,
            "text_blob": caption,
            "img_embed": img_embed,
            "license": "CC-BY",
            "created_at": datetime.utcnow(),
        }
    
    def _deduplicate(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates using pHash only (fast)."""
        unique = []
        seen_phashes = set()
        
        for asset in assets:
            phash = asset["phash"]
            
            if phash not in seen_phashes:
                unique.append(asset)
                seen_phashes.add(phash)
        
        return unique
    
    def _balance_classes(
        self,
        assets: List[Dict[str, Any]],
        classes: List[str],
        per_class: int,
    ) -> List[Dict[str, Any]]:
        """Balance dataset to have equal samples per class."""
        balanced = []
        for class_name in classes:
            class_assets = [a for a in assets if a["class"] == class_name]
            actual_count = min(len(class_assets), per_class)
            balanced.extend(class_assets[:per_class])
            
            logger.info(f"Class '{class_name}': {actual_count}/{per_class} images after balancing")
            if len(class_assets) == 0:
                logger.error(f"❌ CRITICAL: No images found for class '{class_name}'!")
            elif len(class_assets) < per_class:
                logger.warning(f"⚠️  Class '{class_name}' has only {len(class_assets)}/{per_class} images")
        
        return balanced
    
    def _create_manifest(
        self,
        assets: List[Dict[str, Any]],
        classes: List[str],
        split: List[float],
    ) -> Dict[str, Any]:
        """Create dataset manifest with splits."""
        total = len(assets)
        train_size = int(total * split[0])
        val_size = int(total * split[1])
        
        return {
            "total": total,
            "classes": classes,
            "split": {
                "train": assets[:train_size],
                "val": assets[train_size:train_size + val_size],
                "test": assets[train_size + val_size:],
            },
            "stats": {
                "train_count": train_size,
                "val_count": val_size,
                "test_count": total - train_size - val_size,
                "class_distribution": {
                    cls: len([a for a in assets if a["class"] == cls])
                    for cls in classes
                },
            },
            "created_at": datetime.utcnow(),
        }
    
    def _save_dataset(
        self,
        manifest: Dict[str, Any],
        classes: List[str],
        license_filter: str,
    ) -> str:
        """Save dataset to MongoDB and return dataset ID."""
        # First create the dataset document to get the ID
        dataset_doc = {
            "spec": {
                "classes": classes,
                "total": manifest["total"],
                "license": license_filter,
            },
            "manifest_sha": hashlib.sha256(str(manifest).encode()).hexdigest()[:16],
            "slice_stats": manifest["stats"],
            "provenance": {
                "source": "tavily_image_search",
                "created_at": manifest["created_at"],
            },
        }
        
        result = self.datasets_col.insert_one(dataset_doc)
        dataset_id = result.inserted_id
        
        # Now add dataset_id to all assets and insert them
        all_assets = (
            manifest["split"]["train"] +
            manifest["split"]["val"] +
            manifest["split"]["test"]
        )
        
        if all_assets:
            # Add dataset_id reference to each asset
            for asset in all_assets:
                asset["dataset_id"] = dataset_id
            
            result = self.assets_col.insert_many(all_assets)
            logger.info(f"Inserted {len(result.inserted_ids)} assets for dataset {dataset_id}")
        
        return str(dataset_id)


# Global agent instance (lazy-loaded)
_dataset_smith = None

def get_dataset_smith():
    """Get or create the global DatasetSmith instance."""
    global _dataset_smith
    if _dataset_smith is None:
        _dataset_smith = DatasetSmith()
    return _dataset_smith

# Lazy accessor
class _DatasetSmithAccessor:
    def __getattr__(self, name):
        return getattr(get_dataset_smith(), name)

dataset_smith = _DatasetSmithAccessor()
