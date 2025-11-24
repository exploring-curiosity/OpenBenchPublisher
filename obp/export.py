"""Export utilities for datasets."""

import json
import csv
import shutil
import re
from html import unescape
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
from bson import ObjectId
from gridfs import GridFS

from obp.db import (
    get_datasets_collection,
    get_assets_collection,
    get_cards_collection,
    get_db,
    get_requests_collection,
    get_resources_collection,
)

logger = logging.getLogger(__name__)


class DatasetExporter:
    """Export datasets to local filesystem."""
    
    def __init__(self, export_dir: Path = Path("./exports")):
        self.export_dir = export_dir
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def _html_to_text(self, html_content: str) -> str:
        """Best-effort HTML → plain text conversion for exported text corpora."""
        # Strip script/style blocks
        text = re.sub(r"<script.*?</script>", " ", html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        # Drop all remaining tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode entities and normalize whitespace
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    
    def export_dataset(
        self,
        dataset_id: str,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Export a complete dataset with images and metadata.
        
        Args:
            dataset_id: MongoDB dataset ID
            output_dir: Custom output directory (optional)
        
        Returns:
            Export summary with paths and stats
        """
        logger.info(f"Exporting dataset: {dataset_id}")
        
        # Get dataset document
        datasets_col = get_datasets_collection()
        # Convert string ID to ObjectId
        try:
            obj_id = ObjectId(dataset_id)
        except:
            raise ValueError(f"Invalid dataset ID format: {dataset_id}")
        
        dataset = datasets_col.find_one({"_id": obj_id})
        
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")
        
        # Create export directory
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = self.export_dir / f"dataset_{dataset_id}_{timestamp}"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all assets for this dataset
        assets_col = get_assets_collection()
        
        # Export structure
        train_dir = output_dir / "train"
        val_dir = output_dir / "val"
        test_dir = output_dir / "test"
        
        for split_dir in [train_dir, val_dir, test_dir]:
            split_dir.mkdir(exist_ok=True)
            # Create class subdirectories
            for class_name in dataset["spec"]["classes"]:
                (split_dir / class_name).mkdir(exist_ok=True)
        
        # Export images by split
        exported_counts = {"train": 0, "val": 0, "test": 0}
        manifest = {"train": [], "val": [], "test": []}
        
        # Query assets for THIS dataset only
        all_assets = list(assets_col.find({"dataset_id": obj_id}).sort("created_at", 1))
        
        if not all_assets:
            logger.warning(f"No assets found for dataset {dataset_id}")
            return {
                "dataset_id": dataset_id,
                "output_dir": str(output_dir),
                "exported_counts": exported_counts,
            }
        
        # Group assets by class for stratified splitting
        from collections import defaultdict
        import random
        
        assets_by_class = defaultdict(list)
        for asset in all_assets:
            assets_by_class[asset.get("class", "unknown")].append(asset)
            
        splits = {"train": [], "val": [], "test": []}
        
        # Split each class individually
        for class_name, class_assets in assets_by_class.items():
            # Shuffle to ensure random distribution
            random.shuffle(class_assets)
            
            total_class = len(class_assets)
            train_size = int(total_class * 0.7)
            val_size = int(total_class * 0.15)
            # Test gets the remainder to ensure no assets are lost
            
            splits["train"].extend(class_assets[:train_size])
            splits["val"].extend(class_assets[train_size:train_size + val_size])
            splits["test"].extend(class_assets[train_size + val_size:])
        
        # Copy images to split directories
        for split_name, assets in splits.items():
            split_dir = output_dir / split_name
            
            for asset in assets:
                class_name = asset["class"]
                src_path = Path(asset["uri"])
                
                if not src_path.exists():
                    logger.warning(f"Image not found: {src_path}")
                    continue
                
                # Copy to class subdirectory
                dst_path = split_dir / class_name / src_path.name
                shutil.copy2(src_path, dst_path)
                
                # Add to manifest
                manifest[split_name].append({
                    "path": str(dst_path.relative_to(output_dir)),
                    "class": class_name,
                    "url": asset.get("url", ""),
                    "source": asset.get("source_url", ""),
                    "width": asset.get("width", 0),
                    "height": asset.get("height", 0),
                })
                
                exported_counts[split_name] += 1
        
        # Save manifest
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump({
                "dataset_id": dataset_id,
                "spec": dataset["spec"],
                "stats": dataset["slice_stats"],
                "splits": manifest,
                "exported_at": datetime.utcnow().isoformat(),
            }, f, indent=2)
        
        # Save Data Card if exists
        cards_col = get_cards_collection()
        card = cards_col.find_one({"dataset_id": dataset_id})
        if card:
            from obp.cards import card_publisher
            card_md = card_publisher.format_card_markdown(card)
            card_path = output_dir / "DATA_CARD.md"
            with open(card_path, "w") as f:
                f.write(card_md)
        
        # Create README
        readme_path = output_dir / "README.md"
        with open(readme_path, "w") as f:
            f.write(self._generate_readme(dataset, exported_counts))
        
        summary = {
            "dataset_id": dataset_id,
            "output_dir": str(output_dir),
            "exported_counts": exported_counts,
            "total_exported": sum(exported_counts.values()),
            "manifest_path": str(manifest_path),
        }
        
        logger.info(f"Export complete: {summary['total_exported']} images")
        return summary
    
    def _generate_readme(self, dataset: Dict[str, Any], counts: Dict[str, int]) -> str:
        """Generate README for exported dataset."""
        spec = dataset["spec"]
        stats = dataset["slice_stats"]
        
        # Generate tree structure dynamically
        tree = ""
        for i, split in enumerate(['train', 'val', 'test']):
            tree += f"├── {split}/          # {counts[split]} images\n"
            for j, cls in enumerate(spec['classes']):
                prefix = "│   "
                connector = "└── " if j == len(spec['classes']) - 1 else "├── "
                tree += f"{prefix}{connector}{cls}/\n"
        
        readme = f"""# Dataset: {' vs '.join(spec['classes'])}

**Dataset ID:** `{dataset['_id']}`  
**License:** {spec['license']}  
**Total Images:** {spec['total']}

## Structure

```
.
{tree}├── manifest.json   # Full metadata
├── DATA_CARD.md    # Provenance and quality info
└── README.md       # This file
```

## Class Distribution

"""
        for cls, count in stats["class_distribution"].items():
            readme += f"- **{cls}:** {count} images\n"
        
        readme += f"""
## Usage

**PyTorch:**
```python
from torchvision import datasets, transforms

transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
])

train_dataset = datasets.ImageFolder('train', transform=transform)
val_dataset = datasets.ImageFolder('val', transform=transform)
test_dataset = datasets.ImageFolder('test', transform=transform)
```

**TensorFlow:**
```python
import tensorflow as tf

train_ds = tf.keras.utils.image_dataset_from_directory(
    'train',
    image_size=(224, 224),
    batch_size=32,
)
```

## Provenance

- **Source:** Tavily image search
- **Deduplication:** pHash + vector similarity
- **Quality:** Min 512px resolution
- **License:** CC-BY (attribution required)

See `DATA_CARD.md` for full details.
"""
        return readme
    
    def create_request_zip(self, request_id: str) -> Optional[str]:
        """Create a ZIP file for a Foundational request.

        Supports both legacy filesystem-backed resources (``local_path`` / ``sample_path``)
        and the new MongoDB GridFS-backed storage (``content_blob_id``). The "persist"
        flag on the corresponding request controls whether GridFS blobs are retained
        or deleted after a successful export.
        """

        resources_col = get_resources_collection()
        requests_col = get_requests_collection()
        db = get_db()
        fs = GridFS(db, collection="resources_files")

        # Determine persist behaviour from the request document. For old runs that
        # never set this flag, default to True (keep data) to avoid surprises.
        req_doc = requests_col.find_one({"request_id": request_id})
        if req_doc is not None:
            persist_flag = bool(req_doc.get("persist", False))
        else:
            persist_flag = True

        # Prefer fully downloaded resources; fall back to sampled if nothing.
        cursor = resources_col.find({"request_id": request_id, "status": "downloaded"})
        files = list(cursor)
        if not files:
            cursor = resources_col.find({"request_id": request_id, "status": "sampled"})
            files = list(cursor)

        if not files:
            logger.warning(f"No files found for request {request_id}")
            return None

        zip_name = f"request_{request_id}"
        output_path = self.export_dir / zip_name
        output_path.mkdir(parents=True, exist_ok=True)

        count = 0
        manifest_items: List[Dict[str, Any]] = []
        counts_by_modality: Dict[str, int] = {}

        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
        numerical_exts = {".csv", ".tsv", ".xlsx", ".xls", ".json"}
        audio_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
        video_exts = {".mp4", ".webm", ".m4v", ".mov", ".avi", ".mkv"}
        three_d_exts = {".obj", ".glb", ".gltf", ".stl", ".fbx", ".ply"}

        for doc in files:
            modality = doc.get("modality", "misc")
            mod_dir = output_path / modality
            mod_dir.mkdir(exist_ok=True)

            dst: Optional[Path] = None

            # --- Legacy path-based storage ---
            src_path: Optional[Path] = None
            if "local_path" in doc:
                src_path = Path(doc["local_path"])
            elif "sample_path" in doc:
                src_path = Path(doc["sample_path"])

            if src_path is not None and src_path.exists():
                ext = src_path.suffix.lower()

                # For image-style modalities, only keep real image files.
                if modality in {"image", "images"} and ext not in image_exts:
                    logger.info(
                        f"Skipping non-image file for modality '{modality}': {src_path} (ext={ext})"
                    )
                    continue

                # Numerical datasets: only keep tabular / structured data files.
                if modality == "numerical" and ext not in numerical_exts:
                    logger.info(
                        f"Skipping non-numerical file for modality '{modality}': {src_path} (ext={ext})"
                    )
                    continue

                # Audio datasets: keep only known audio formats.
                if modality == "audio" and ext not in audio_exts:
                    logger.info(
                        f"Skipping non-audio file for modality '{modality}': {src_path} (ext={ext})"
                    )
                    continue

                # Video datasets: keep only known video formats.
                if modality == "video" and ext not in video_exts:
                    logger.info(
                        f"Skipping non-video file for modality '{modality}': {src_path} (ext={ext})"
                    )
                    continue

                # 3D datasets: keep only known 3D mesh/model formats.
                if modality in {"3d", "3D"} and ext not in three_d_exts:
                    logger.info(
                        f"Skipping non-3D file for modality '{modality}': {src_path} (ext={ext})"
                    )
                    continue

                if ext == ".html" and modality in {"text", "news", "code"}:
                    try:
                        with open(src_path, "r", encoding="utf-8", errors="ignore") as hf:
                            html_content = hf.read()
                        text_content = self._html_to_text(html_content)
                        dst = mod_dir / f"{src_path.stem}.txt"
                        with open(dst, "w", encoding="utf-8") as tf:
                            tf.write(text_content)
                        logger.info(f"Converted HTML to TXT for {modality}: {src_path} -> {dst}")
                    except Exception as e:
                        logger.warning(f"Failed to convert HTML to TXT for {src_path}: {e}")
                        continue
                elif ext == ".html":
                    logger.info(f"Skipping HTML resource for modality '{modality}': {src_path}")
                    continue
                else:
                    dst = mod_dir / src_path.name
                    shutil.copy2(src_path, dst)

            # --- GridFS-backed storage ---
            elif doc.get("content_blob_id") is not None:
                blob_id = doc["content_blob_id"]
                try:
                    if not isinstance(blob_id, ObjectId):
                        blob_id = ObjectId(blob_id)
                    grid_file = fs.get(blob_id)
                except Exception as e:
                    logger.warning(f"Failed to fetch GridFS file for {blob_id}: {e}")
                    continue

                filename = doc.get("filename") or str(blob_id)
                ext = Path(filename).suffix.lower()

                # For image-style modalities, only keep real image files.
                if modality in {"image", "images"} and ext not in image_exts:
                    logger.info(
                        f"Skipping non-image GridFS file for modality '{modality}': {blob_id} (ext={ext})"
                    )
                    continue

                # Numerical datasets: only keep tabular / structured data files.
                if modality == "numerical" and ext not in numerical_exts:
                    logger.info(
                        f"Skipping non-numerical GridFS file for modality '{modality}': {blob_id} (ext={ext})"
                    )
                    continue

                # Audio datasets: keep only known audio formats.
                if modality == "audio" and ext not in audio_exts:
                    logger.info(
                        f"Skipping non-audio GridFS file for modality '{modality}': {blob_id} (ext={ext})"
                    )
                    continue

                # Video datasets: keep only known video formats.
                if modality == "video" and ext not in video_exts:
                    logger.info(
                        f"Skipping non-video GridFS file for modality '{modality}': {blob_id} (ext={ext})"
                    )
                    continue

                # 3D datasets: keep only known 3D mesh/model formats.
                if modality in {"3d", "3D"} and ext not in three_d_exts:
                    logger.info(
                        f"Skipping non-3D GridFS file for modality '{modality}': {blob_id} (ext={ext})"
                    )
                    continue

                if ext == ".html" and modality in {"text", "news", "code"}:
                    try:
                        raw_bytes = grid_file.read()
                        html_content = raw_bytes.decode("utf-8", errors="ignore")
                        text_content = self._html_to_text(html_content)
                        dst = mod_dir / f"{Path(filename).stem}.txt"
                        with open(dst, "w", encoding="utf-8") as tf:
                            tf.write(text_content)
                        logger.info(f"Converted HTML GridFS blob to TXT for {modality}: {blob_id} -> {dst}")
                    except Exception as e:
                        logger.warning(f"Failed to convert HTML GridFS blob {blob_id} to TXT: {e}")
                        continue
                elif ext == ".html":
                    logger.info(f"Skipping HTML GridFS resource for modality '{modality}': {blob_id}")
                    continue
                else:
                    dst = mod_dir / filename
                    try:
                        with open(dst, "wb") as f:
                            while True:
                                chunk = grid_file.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                    except Exception as e:
                        logger.warning(f"Failed to write GridFS blob {blob_id} to disk: {e}")
                        if dst.exists():
                            try:
                                dst.unlink()
                            except Exception:
                                pass
                        continue

            if dst is None or not dst.exists():
                continue

            count += 1
            counts_by_modality[modality] = counts_by_modality.get(modality, 0) + 1

            rel_path = str(dst.relative_to(output_path))
            manifest_items.append({
                "modality": modality,
                "path": rel_path,
                "url": doc.get("url", ""),
                "title": doc.get("title", ""),
                "content_snippet": doc.get("content_snippet", ""),
                "status": doc.get("status", ""),
            })

        if count == 0:
            return None

        manifest = {
            "request_id": request_id,
            "total_files": count,
            "counts_by_modality": counts_by_modality,
            "items": manifest_items,
            "exported_at": datetime.utcnow().isoformat(),
        }
        manifest_path = output_path / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        # Also write a simple CSV index for quick inspection / prototyping
        index_path = output_path / "index.csv"
        with open(index_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["modality", "path", "url", "title", "content_snippet", "status"])
            for item in manifest_items:
                writer.writerow([
                    item.get("modality", ""),
                    item.get("path", ""),
                    item.get("url", ""),
                    item.get("title", ""),
                    item.get("content_snippet", ""),
                    item.get("status", ""),
                ])

        # Build a lightweight text corpus index for text-like modalities
        try:
            text_like = [
                item for item in manifest_items
                if item.get("modality") in {"text", "news", "code"}
            ]
            if text_like:
                corpus_path = output_path / "text_corpus.csv"
                with open(corpus_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["modality", "path", "url", "title", "content_snippet", "status"])
                    for item in text_like:
                        writer.writerow([
                            item.get("modality", ""),
                            item.get("path", ""),
                            item.get("url", ""),
                            item.get("title", ""),
                            item.get("content_snippet", ""),
                            item.get("status", ""),
                        ])
        except Exception as e:
            logger.warning(f"Failed to build text_corpus.csv for request {request_id}: {e}")

        # Build a consolidated numerical_aggregated.csv for quick prototyping
        try:
            numerical_rows = []
            fieldnames = set()
            for item in manifest_items:
                if item.get("modality") != "numerical":
                    continue
                rel_path = item.get("path") or ""
                if not rel_path:
                    continue
                ext = Path(rel_path).suffix.lower()
                if ext not in {".csv", ".tsv"}:
                    continue
                file_path = output_path / rel_path
                if not file_path.exists():
                    logger.warning(f"Numerical file missing for aggregation: {file_path}")
                    continue
                delimiter = "\t" if ext == ".tsv" else ","
                try:
                    with open(file_path, newline="", encoding="utf-8") as nf:
                        reader = csv.DictReader(nf, delimiter=delimiter)
                        for row in reader:
                            row = dict(row)
                            row["__source_path"] = rel_path
                            row["__source_url"] = item.get("url", "")
                            row["__source_title"] = item.get("title", "")
                            numerical_rows.append(row)
                            fieldnames.update(row.keys())
                except Exception as e:
                    logger.warning(f"Failed to parse numerical file {file_path}: {e}")
                    continue

            if numerical_rows:
                agg_path = output_path / "numerical_aggregated.csv"
                ordered_fields = sorted(fieldnames)
                with open(agg_path, "w", newline="", encoding="utf-8") as af:
                    writer = csv.DictWriter(af, fieldnames=ordered_fields)
                    writer.writeheader()
                    for row in numerical_rows:
                        writer.writerow({k: row.get(k, "") for k in ordered_fields})
        except Exception as e:
            logger.warning(f"Failed to build numerical_aggregated.csv for request {request_id}: {e}")

        zip_file = shutil.make_archive(str(self.export_dir / zip_name), 'zip', output_path)

        shutil.rmtree(output_path)

        if not persist_flag:
            try:
                removed = 0
                cursor = resources_col.find({
                    "request_id": request_id,
                    "content_blob_id": {"$exists": True},
                })
                for rdoc in cursor:
                    blob_id = rdoc.get("content_blob_id")
                    if blob_id is None:
                        continue
                    try:
                        if not isinstance(blob_id, ObjectId):
                            blob_id = ObjectId(blob_id)
                        fs.delete(blob_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete GridFS blob {blob_id} for request {request_id}: {e}")
                        continue
                    resources_col.update_one({"_id": rdoc["_id"]}, {"$unset": {"content_blob_id": ""}})
                    removed += 1
                logger.info(f"Cleanup for request {request_id}: removed {removed} GridFS files (persist=False)")
            except Exception as e:
                logger.warning(f"Cleanup of GridFS blobs failed for request {request_id}: {e}")

        return zip_file

    def build_labeled_corpus(
        self,
        specs: List[Dict[str, str]],
        modality: str,
        output_basename: Optional[str] = None,
    ) -> Optional[str]:
        """Build a combined labeled CSV from multiple foundational requests.

        Each spec in ``specs`` should be a dict with keys:

        - ``label``: class label to assign (e.g., "people", "cars").
        - ``request_id``: foundational request ID whose export should be included.

        For ``modality == 'text'`` this merges all ``text_corpus.csv`` files.
        For ``modality == 'numerical'`` this merges all ``numerical_aggregated.csv`` files.

        Returns the path to the combined CSV, or ``None`` if nothing could be built.
        """
        import zipfile
        import io

        modality = modality.lower()
        if modality not in {"text", "numerical"}:
            logger.warning(f"build_labeled_corpus: unsupported modality '{modality}'")
            return None

        rows: List[Dict[str, Any]] = []
        fieldnames: set = set()

        for spec in specs:
            label = spec.get("label")
            request_id = spec.get("request_id")
            if not label or not request_id:
                logger.warning(f"build_labeled_corpus: skipping spec with missing label/request_id: {spec}")
                continue

            zip_path = self.create_request_zip(request_id)
            if not zip_path:
                logger.warning(f"build_labeled_corpus: no export zip for request {request_id}")
                continue

            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    names = set(zf.namelist())
                    if modality == "text":
                        csv_name = "text_corpus.csv"
                    else:  # numerical
                        csv_name = "numerical_aggregated.csv"

                    if csv_name not in names:
                        logger.warning(
                            f"build_labeled_corpus: '{csv_name}' not found in zip for request {request_id}"
                        )
                        continue

                    with zf.open(csv_name, "r") as f:
                        wrapper = io.TextIOWrapper(f, encoding="utf-8", newline="")
                        reader = csv.DictReader(wrapper)
                        for row in reader:
                            r = dict(row)
                            r["class"] = label
                            rows.append(r)
                            fieldnames.update(r.keys())
            except Exception as e:
                logger.warning(
                    f"build_labeled_corpus: failed to read export for request {request_id}: {e}"
                )
                continue

        if not rows:
            logger.warning("build_labeled_corpus: no rows collected; nothing to write")
            return None

        if output_basename is None:
            suffix = "text_corpus" if modality == "text" else "numerical_aggregated"
            output_basename = f"{modality}_labeled_{suffix}"

        output_path = self.export_dir / f"{output_basename}.csv"

        ordered_fields = ["class"] + sorted(f for f in fieldnames if f != "class")
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in ordered_fields})

        logger.info(
            f"build_labeled_corpus: wrote {len(rows)} rows for modality '{modality}' to {output_path}"
        )
        return str(output_path)

    def list_datasets(self) -> list:
        """List all available datasets."""
        datasets_col = get_datasets_collection()
        datasets = []
        
        for ds in datasets_col.find():
            classes = ds.get("spec", {}).get("classes", [])
            name = " vs ".join(classes) if classes else "Unknown Dataset"
            datasets.append({
                # Convert ObjectId to string so responses are JSON serialisable
                "_id": str(ds["_id"]),
                "name": name,
                "classes": classes,
                "total_samples": ds.get("spec", {}).get("total", 0),
                "created_at": ds.get("provenance", {}).get("created_at", "Unknown"),
            })
        
        return datasets


# Global exporter instance
exporter = DatasetExporter()
