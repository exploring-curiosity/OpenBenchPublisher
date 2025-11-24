from dagster import asset, Definitions, Config, define_asset_job, AssetSelection
from typing import List, Dict, Any, Optional
import logging
import os
import json
import yaml
from uuid import uuid4
from datetime import datetime

try:
    from openai import OpenAI
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

from obp.agents.foundational_gatherer import FoundationalGatherer
from obp.downloader import FoundationalDownloader
from obp.db import get_requests_collection

# Configure logging
logger = logging.getLogger("dagster")

# --- Config ---

class UserRequest(Config):
    query: str
    total_items: int = 20
    data_type: str = "auto"  # "images", "text", "auto"
    request_id: Optional[str] = None
    persist: bool = False


class FullDownloadRequest(Config):
    """Config for running a pure download step on an existing foundational request.

    This does not perform planning or sourcing; it only downloads content for
    the given ``request_id`` using the resources stored in MongoDB.
    """

    request_id: str
    persist: bool = False

# --- Helpers ---

def get_llm_client():
    """Return an OpenAI client and model name for dataset planning.

    Priority:
    1) OPENAI_API_KEY env var
    2) mcp_agent.secrets.yaml: openai.api_key or OPENAI_API_KEY
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            with open("mcp_agent.secrets.yaml") as f:
                secrets = yaml.safe_load(f) or {}
                if "openai" in secrets and isinstance(secrets["openai"], dict):
                    api_key = secrets["openai"].get("api_key")
                elif "OPENAI_API_KEY" in secrets:
                    api_key = secrets["OPENAI_API_KEY"]
        except Exception:
            pass

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set and no openai.api_key/OPENAI_API_KEY found in mcp_agent.secrets.yaml; "
            "OpenAI is required for dataset planning."
        )

    if not HAS_LLM:
        raise RuntimeError(
            "openai Python library is not installed; install openai to enable OpenAI-based planning."
        )

    model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    client = OpenAI(api_key=api_key)
    return client, model_name

# --- Assets ---

@asset
def dataset_plan(context, config: UserRequest) -> Dict[str, Any]:
    """
    Foundational Step: Analyze the user's high-level request and plan the dataset.
    """
    context.log.info(f"Planning dataset for query: '{config.query}'")
    request_id = config.request_id or str(uuid4())

    try:
        client, model_name = get_llm_client()
    except Exception as e:
        context.log.error(f"LLM planning is required but unavailable: {e}")
        raise

    system_prompt = (
        "You are a Dataset Architect. You design small, well-structured datasets for evaluation. "
        "Given a user's request, you decide the data modality, classes, and search queries."
    )

    user_prompt = f"""
Act as a Dataset Architect. Plan a dataset based on this request: "{config.query}"
Target count: {config.total_items}

Supported data types: "images", "text", "numerical", "audio", "video", "3d", "code", "news".
The current user selection for data_type is "{config.data_type}".

- If data_type is "auto", you must infer the best single data type from the request.
- If data_type is one of the supported values above, you MUST use that exact type in the plan.

Determine:
1. Data Type: exactly one of the supported values above.
2. Classes/Categories: Break down the topic into 2-5 distinct visual or semantic classes.
3. Search Queries: For each class, generate 3 diverse search queries to find high-quality data.

Return JSON ONLY (no markdown, no explanations around it):
{{
  "explanation": "Brief reasoning",
  "type": "<one of: images, text, numerical, audio, video, 3d, code, news>",
  "classes": ["class1", "class2"],
  "queries": {{
    "class1": ["query1", "query2", "query3"],
    "class2": ["query1", "query2", "query3"]
  }}
"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        text = (response.choices[0].message.content or "").strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        plan = json.loads(text)
        context.log.info(f"Plan generated: {json.dumps(plan, indent=2)}")

        # Persist high-level request + plan for dashboard and reuse
        try:
            requests_col = get_requests_collection()
            requests_col.update_one(
                {"request_id": request_id},
                {"$set": {
                    "request_id": request_id,
                    "query": config.query,
                    "plan": plan,
                    "type": plan.get("type", config.data_type),
                    "total": plan.get("total", config.total_items),
                    "persist": bool(config.persist),
                    "created_at": datetime.utcnow(),
                }},
                upsert=True,
            )
        except Exception as db_err:
            context.log.warning(f"Failed to persist request metadata for {request_id}: {db_err}")

        # Include persist flag in the asset output so downstream assets/exporters can see it.
        return {**plan, "request_id": request_id, "total": config.total_items, "persist": bool(config.persist)}
    except Exception as e:
        context.log.error(f"LLM planning failed and no fallback is configured: {e}")
        raise

@asset
def sourced_links(context, dataset_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Source links for all classes and store in DB (discovered).
    Does NOT download full content.
    """
    gatherer = FoundationalGatherer()
    req_id = dataset_plan["request_id"]
    classes = dataset_plan.get("classes", [])
    queries_map = dataset_plan.get("queries", {})
    data_type = dataset_plan.get("type", "text")
    total = int(dataset_plan.get("total", 20) or 1)

    # Build a flat list of (class, query) pairs we plan to source.
    pairs: List[Tuple[str, str]] = []
    for cls in classes:
        qs = queries_map.get(cls, [cls]) or [cls]
        for q in qs:
            pairs.append((cls, q))

    # Fallback: if the plan has no explicit classes/queries, just use the
    # request as a single generic query.
    if not pairs:
        pairs.append(("", dataset_plan.get("query", "")))

    slots_remaining = max(1, total)
    total_sourced = 0

    for idx, (cls, q) in enumerate(pairs):
        if slots_remaining <= 0:
            break

        pairs_left = len(pairs) - idx
        # Evenly distribute remaining slots across remaining (class, query) pairs.
        per_pair_limit = max(1, slots_remaining // pairs_left)

        context.log.info(
            f"Sourcing links for class='{cls}' query='{q}' (type={data_type}, limit={per_pair_limit})..."
        )

        count = gatherer.gather_and_store(q, data_type, req_id, limit=per_pair_limit)
        total_sourced += count

        # gather_and_store may reuse existing resources and return a count larger
        # than the new budget for this pair. Clamp the budget decrement so that
        # we don't overshoot the global target for new requests.
        used_slots = min(per_pair_limit, count)
        slots_remaining -= used_slots

    context.log.info(
        f"Total sourced links for request {req_id}: {total_sourced} (requested total={total})"
    )
    return {"request_id": req_id, "count": total_sourced, "plan": dataset_plan}

@asset
def sampled_data(context, sourced_links: Dict[str, Any]) -> Dict[str, Any]:
    """
    Download a few samples per class to verify quality.
    """
    gatherer = FoundationalGatherer()
    req_id = sourced_links["request_id"]
    
    context.log.info(f"Sampling resources for request {req_id}...")
    # Sample 3 items total for quick check
    sampled_count = gatherer.sample_resources(req_id, count_per_modality=3)
    
    context.log.info(f"Sampled {sampled_count} items.")
    return {"request_id": req_id, "sampled_count": sampled_count, "plan": sourced_links["plan"]}

@asset
def full_dataset(context, sampled_data: Dict[str, Any]):
    """
    Trigger full download of the dataset.
    This separate functionality can be controlled or triggered here.
    """
    downloader = FoundationalDownloader()
    req_id = sampled_data["request_id"]
    persist = sampled_data.get("plan", {}).get("persist", False)

    context.log.info(f"Starting full download for {req_id} (persist={persist})...")
    count = downloader.download_all(req_id)

    context.log.info(f"✅ Full Dataset Downloaded: {count} files (persist={persist}).")
    return req_id


@asset
def full_download(context, config: FullDownloadRequest) -> str:
    """Download all data for an existing foundational request.

    This asset reuses links already written to MongoDB by the sourcing step.
    It does not call the planner or Tavily again, and can be run independently
    of the plan/sample pipeline.
    """
    downloader = FoundationalDownloader()
    req_id = config.request_id
    persist = bool(config.persist)

    context.log.info(
        f"[full_download] Starting full download for existing request {req_id} (persist={persist})..."
    )
    count = downloader.download_all(req_id)
    context.log.info(
        f"[full_download] ✅ Downloaded {count} resources for request {req_id} (persist={persist})"
    )

    # Ensure persist flag is up to date on the request document so exporters
    # can decide whether to retain or clean up GridFS blobs.
    try:
        requests_col = get_requests_collection()
        requests_col.update_one(
            {"request_id": req_id},
            {"$set": {"persist": persist, "updated_at": datetime.utcnow()}},
            upsert=True,
        )
    except Exception as db_err:
        context.log.warning(
            f"[full_download] Failed to update persist flag for {req_id}: {db_err}"
        )

    return req_id

# --- Jobs ---

# Legacy all-in-one job (plan + source + sample + download).
dataset_job = define_asset_job(
    name="foundational_dataset_job",
    selection=AssetSelection.all(),
)

# Preview job: plan + source + sample, used by the UI's Plan & Preview.
preview_job = define_asset_job(
    name="foundational_preview_job",
    selection=AssetSelection.keys("dataset_plan", "sourced_links", "sampled_data"),
)

# Download-only job: just run the full_download asset for an existing request.
download_job = define_asset_job(
    name="foundational_download_job",
    selection=AssetSelection.keys("full_download"),
)

defs = Definitions(
    assets=[dataset_plan, sourced_links, sampled_data, full_dataset, full_download],
    jobs=[dataset_job, preview_job, download_job],
)
