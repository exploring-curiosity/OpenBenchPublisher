"""Simple web interface for OpenBench Publisher."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import shutil
import zipfile
import io
import logging
import os
import json
import yaml
import traceback

# Try to import OpenAI client
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from obp.agents.dataset_smith import get_dataset_smith
from obp.export import exporter
from obp.config import settings
from obp.db import get_resources_collection, get_requests_collection, get_chats_collection
from obp.embeddings import embedding_service

app = FastAPI(title="OpenBench Publisher")
logger = logging.getLogger(__name__)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Check MongoDB connection
        req_col = get_requests_collection()
        req_col.find_one()
        
        return {
            "status": "healthy",
            "service": "datasetsmith-backend",
            "mongodb": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


# Load secrets to get OpenAI API Key
def load_openai_api_key():
    # Check env var first
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    # Check secrets file
    secrets_path = Path("mcp_agent.secrets.yaml")
    if secrets_path.exists():
        try:
            with open(secrets_path) as f:
                secrets = yaml.safe_load(f) or {}
                # Check flat key
                if "OPENAI_API_KEY" in secrets:
                    return secrets["OPENAI_API_KEY"]
                # Check nested openai.api_key
                if "openai" in secrets and isinstance(secrets["openai"], dict):
                    return secrets["openai"].get("api_key")
        except Exception as e:
            logger.warning(f"Failed to load secrets: {e}")
    return None

# Configure OpenAI for lightweight intent parsing (chat endpoint)
OPENAI_API_KEY = load_openai_api_key()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_CLIENT = None
if HAS_OPENAI and OPENAI_API_KEY:
    OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("✅ OpenAI client configured for intent parsing")
else:
    logger.warning("⚠️ OpenAI API Key not found or library missing. Smart parsing disabled.")


class ChatMessage(BaseModel):
    message: str


class DatasetBuildRequest(BaseModel):
    query: str
    total_items: int = 20
    data_type: str = "auto"  # "images", "text", "auto"


class FullRunRequest(BaseModel):
    request_id: str
    persist: bool = True
    query: Optional[str] = None
    total_items: Optional[int] = None
    data_type: Optional[str] = None


async def parse_intent_with_llm(message: str):
    """Parse user intent using Gemini."""
    if not OPENAI_CLIENT:
        logger.warning("LLM parsing unavailable, falling back to keyword parsing")
        return None

    try:
        prompt = f"""
You are a helper for a dataset creation tool.
Extract the dataset classes and total image count from the user's request.

Request: "{message}"

Return ONLY a JSON object with these keys:
- classes: list of strings (e.g. ["cats", "dogs"])
- total: int (default to 20 if not specified)

Do not include markdown formatting like ```json. Just the raw JSON string.
"""

        response = OPENAI_CLIENT.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You extract structured parameters for dataset creation."},
                {"role": "user", "content": prompt},
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        # Clean up markdown if present
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        logger.info(f"LLM Parsed: {data}")
        return data
    except Exception as e:
        logger.error(f"LLM parsing failed: {e}")
        return None

@app.post("/chat")
async def chat(msg: ChatMessage):
    """Process chat messages."""
    message = msg.message.lower()
    
    triggers = ["build", "create", "download", "gather", "collect", "find", "search", "get"]
    if any(t in message for t in triggers):
        logger.info(f"Processing build request: {message}")
        
        # Try LLM parsing first
        parsed = await parse_intent_with_llm(msg.message)
        
        classes = []
        total = 20
        
        if parsed:
            classes = parsed.get("classes", [])
            total = parsed.get("total", 20)
        else:
            # Fallback to keyword parsing
            logger.info("Falling back to keyword parsing")
            words = msg.message.split()
            
            # Parse total
            for word in words:
                if word.isdigit():
                    total = int(word)
                    break
            
            # Parse classes - look for "of"
            for i, word in enumerate(words):
                if word.lower() == "of":
                    remaining = " ".join(words[i+1:])
                    class_parts = remaining.replace(",", " and ").split(" and ")
                    for c in class_parts:
                        c = c.strip()
                        for suffix in ["images", "image", "photos", "photo", "pictures", "picture"]:
                            if c.endswith(f" {suffix}"):
                                c = c[:-len(f" {suffix}")].strip()
                        if c and all(ch.isalpha() or ch.isspace() for ch in c):
                            classes.append(c)
                    break
        
        logger.info(f"Target: {classes}, Total: {total}")
        
        if not classes:
            # If generic parsing failed or we want to use the pipeline's planner
            # We pass the raw message to the pipeline
            pass
        
        try:
            # Execute via Dagster Pipeline
            logger.info("🚀 Triggering Dagster Pipeline...")
            from dagster import materialize
            from obp.pipeline import dataset_plan, sourced_links, sampled_data, full_dataset
            
            # Run the pipeline in-process
            result = materialize(
                assets=[dataset_plan, sourced_links, sampled_data, full_dataset],
                run_config={
                    "ops": {
                        "dataset_plan": {
                            "config": {
                                "query": msg.message,
                                "total_items": total,
                                "data_type": "images"
                            }
                        }
                    }
                }
            )
            
            if result.success:
                # Pipeline returns request_id from full_dataset asset
                dataset_id = result.output_for_node("full_dataset")
                
                # Get the plan to show what classes were picked
                plan = result.output_for_node("dataset_plan")
                planned_classes = plan.get("classes", [])
                
                return {"response": f"""
                    ✅ **Dataset Built via Dagster!**<br>
                    <strong>Query:</strong> "{msg.message}"<br>
                    <strong>Planned Classes:</strong> {', '.join(planned_classes)}<br>
                    <strong>ID:</strong> {dataset_id}<br>
                    <a href="/download/{dataset_id}">📥 Download ZIP</a><br>
                    <small>View pipeline run in <a href="http://localhost:3000" target="_blank">Dagster UI</a></small>
                """}
            else:
                return {"response": "❌ Pipeline Failed. Check Dagster logs."}

        except Exception as e:
            logger.error(f"Build failed: {e}")
            traceback.print_exc()
            return {"response": f"❌ Error: {str(e)}"}
    
    elif "list" in message:
        try:
            datasets = exporter.list_datasets()
            if not datasets:
                return {"response": "📭 No datasets found"}
            
            response = "<strong>Your Datasets:</strong><br>"
            for ds in datasets[:5]:
                response += f"• {ds['name']} ({ds['total_samples']} images) "
                response += f"<a href='/download/{str(ds['_id'])}'>Download</a><br>"
            return {"response": response}
        except Exception as e:
            logger.error(f"List failed: {e}")
            traceback.print_exc()
            return {"response": f"❌ Error: {str(e)}"}
    
    return {"response": "💡 Try: 'Build a dataset with 20 images of cats and dogs' or 'List my datasets'"}


@app.post("/api/plan-and-sample")
async def api_plan_and_sample(req: DatasetBuildRequest):
    """Run Dagster planning + sourcing + sampling, and return plan + samples.

    We use a real DagsterInstance so runs are recorded in run storage (and can
    be inspected from a Dagster UI that points at the same instance).
    """
    from dagster import materialize, DagsterInstance
    from obp.pipeline import dataset_plan, sourced_links, sampled_data

    try:
        run_config = {
            "ops": {
                "dataset_plan": {
                    "config": {
                        "query": req.query,
                        "total_items": req.total_items,
                        "data_type": req.data_type,
                    }
                }
            }
        }

        instance = DagsterInstance.get()
        result = materialize(
            assets=[dataset_plan, sourced_links, sampled_data],
            run_config=run_config,
            instance=instance,
        )
        if not result.success:
            raise HTTPException(status_code=500, detail="Dagster plan/sample failed")

        plan = result.output_for_node("dataset_plan")
        sampled_info = result.output_for_node("sampled_data")
        request_id = plan.get("request_id") or sampled_info.get("request_id")

        # Fetch sampled resources from MongoDB
        samples: List[dict] = []
        if request_id:
            col = get_resources_collection()
            cursor = col.find({"request_id": request_id, "status": "sampled"}).limit(10)
            for doc in cursor:
                samples.append({
                    "url": doc.get("url", ""),
                    "modality": doc.get("modality", ""),
                    "title": doc.get("title", ""),
                    "content_snippet": doc.get("content_snippet", ""),
                })

        return {
            "dagster_run_id": getattr(result, "run_id", None),
            "request_id": request_id,
            "plan": {
                "type": plan.get("type", req.data_type),
                "classes": plan.get("classes", []),
                "total": plan.get("total", req.total_items),
                "queries": plan.get("queries", {}),
            },
            "samples": samples,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"plan-and-sample failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/start-full-run")
async def api_start_full_run(req: FullRunRequest):
    """Run a download-only Dagster job for an existing request and return run metadata.

    This uses a shared DagsterInstance so the run is visible in Dagster's run
    storage, but it does **not** rerun planning or sourcing; it only executes the
    ``full_download`` asset for the given ``request_id``.
    """
    from dagster import materialize, DagsterInstance
    from obp.pipeline import full_download

    try:
        run_config = {
            "ops": {
                "full_download": {
                    "config": {
                        "request_id": req.request_id,
                        "persist": req.persist,
                    }
                }
            }
        }

        instance = DagsterInstance.get()
        result = materialize(
            assets=[full_download],
            run_config=run_config,
            instance=instance,
        )
        if not result.success:
            raise HTTPException(status_code=500, detail="Dagster full run failed")

        full_request_id = result.output_for_node("full_download")
        dagster_run_id = getattr(result, "run_id", None)

        return {
            "request_id": full_request_id,
            "dagster_run_id": dagster_run_id,
            "message": "Full dataset download completed.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"start-full-run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/run-status")
async def api_run_status(run_id: str):
    """Return the Dagster run status for a given run_id.

    This lets the UI poll for live run status every few seconds.
    """
    from dagster import DagsterInstance
    from dagster._core.storage.dagster_run import DagsterRunStatus, FINISHED_STATUSES

    try:
        instance = DagsterInstance.get()
        run = instance.get_run_by_id(run_id)
        if run is None:
            return {"state": "NOT_FOUND", "is_finished": True}

        status = run.status
        if isinstance(status, DagsterRunStatus):
            state = status.value
            is_finished = status in FINISHED_STATUSES
        else:
            state = str(status)
            is_finished = state in {"SUCCESS", "FAILURE", "CANCELED"}

        return {"state": state, "is_finished": is_finished}
    except Exception as e:
        logger.error(f"api_run_status failed for {run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-progress")
async def api_download_progress(request_id: str):
    """Return download progress for a given foundational request.

    Uses the resources collection to compute how many items have
    status="sampled" or "downloaded" vs total discovered items.
    """
    try:
        req_col = get_requests_collection()
        res_col = get_resources_collection()
        
        # Get request to check status
        req = req_col.find_one({"request_id": request_id})
        
        # Count total resources
        total = res_col.count_documents({
            "request_id": request_id,
            "status": {"$in": ["discovered", "sampled", "downloaded"]},
        })
        
        # Count sampled resources (for sampling progress)
        sampled = res_col.count_documents({
            "request_id": request_id,
            "status": {"$in": ["sampled", "downloaded"]},
        })
        
        # Count fully downloaded resources
        downloaded = res_col.count_documents({
            "request_id": request_id,
            "status": "downloaded",
        })
        
        # Get some sample URLs if available
        samples = []
        if sampled > 0:
            sample_docs = res_col.find({
                "request_id": request_id,
                "status": {"$in": ["sampled", "downloaded"]}
            }).limit(3)
            samples = [{"url": doc.get("url"), "type": doc.get("type")} for doc in sample_docs]
        
        # Determine status
        status = "running"
        if req:
            req_status = req.get("status", "pending")
            if req_status == "completed" or sampled >= total:
                status = "completed"
        
        return {
            "request_id": request_id,
            "downloaded": sampled,  # For progress bar, show sampled count
            "total": total,
            "fully_downloaded": downloaded,
            "samples": samples,
            "status": status
        }
    except Exception as e:
        logger.error(f"api_download_progress failed for {request_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/requests")
async def api_list_requests():
    """List foundational requests planned via the Dagster pipeline."""
    try:
        col = get_requests_collection()
        rows = []
        for r in col.find().sort("created_at", -1):
            plan = r.get("plan", {})
            rows.append({
                "_id": str(r.get("_id")),
                "request_id": r.get("request_id"),
                "query": r.get("query", ""),
                "classes": plan.get("classes", []),
                "type": plan.get("type", "text"),
                "total": plan.get("total", 0),
                "created_at": r.get("created_at"),
            })
        return {"requests": rows}
    except Exception as e:
        logger.error(f"api_list_requests failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs")
async def api_list_runs():
    """Return recent run activity for the dashboard."""
    try:
        req_col = get_requests_collection()
        runs = []
        
        # Get recent requests with their status
        for r in req_col.find().sort("created_at", -1).limit(10):
            req_id = r.get("request_id")
            if not req_id:
                continue
            
            status = r.get("status", "pending")
            created_at = r.get("created_at")
            query = r.get("query", "Unknown")
            
            # Map status to UI status
            ui_status = "pending"
            if status == "completed":
                ui_status = "success"
            elif status in ["running", "in_progress"]:
                ui_status = "running"
            elif status == "failed":
                ui_status = "error"
            
            # Calculate time ago
            import datetime
            time_str = "Unknown"
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        created_dt = created_at
                    now = datetime.datetime.now(datetime.timezone.utc)
                    delta = now - created_dt
                    
                    if delta.days > 0:
                        time_str = f"{delta.days}d ago"
                    elif delta.seconds >= 3600:
                        time_str = f"{delta.seconds // 3600}h ago"
                    elif delta.seconds >= 60:
                        time_str = f"{delta.seconds // 60}m ago"
                    else:
                        time_str = f"{delta.seconds}s ago"
                except:
                    time_str = "Unknown"
            
            runs.append({
                "id": req_id,
                "action": "Dataset Build",
                "name": query[:50],
                "status": ui_status,
                "time": time_str,
                "timestamp": str(created_at) if created_at else ""
            })
        
        return {"runs": runs}
    except Exception as e:
        logger.error(f"api_list_runs failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs/{request_id}")
async def api_get_run_details(request_id: str):
    """Get detailed information about a specific run."""
    try:
        req_col = get_requests_collection()
        res_col = get_resources_collection()
        
        # Get request document
        req = req_col.find_one({"request_id": request_id})
        if not req:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Count resources
        total_resources = res_col.count_documents({
            "request_id": request_id,
            "status": {"$in": ["discovered", "sampled", "downloaded"]},
        })
        downloaded_resources = res_col.count_documents({
            "request_id": request_id,
            "status": "downloaded",
        })
        
        # Determine status
        status = req.get("status", "pending")
        if status == "completed":
            ui_status = "success"
        elif status in ["running", "sampling", "downloading"]:
            ui_status = "running"
        elif status in ["failed", "error"]:
            ui_status = "error"
        else:
            ui_status = "pending"
        
        return {
            "request_id": request_id,
            "query": req.get("query", ""),
            "status": ui_status,
            "created_at": str(req.get("created_at", "")),
            "updated_at": str(req.get("updated_at", "")) if req.get("updated_at") else None,
            "total_items": req.get("total_items", 0),
            "downloaded": downloaded_resources,
            "classes": req.get("classes", []),
            "data_type": req.get("data_type", ""),
            "error": req.get("error", None),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"api_get_run_details failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/datasets")
async def api_list_datasets():
    """Return a JSON view of available datasets for the dashboard.
    
    Separates datasets into:
    - datasets: Fully downloaded datasets ready for use
    - pending_datasets: Sampled-only datasets that need full download
    """
    try:
        # Classic image-slice datasets stored in the "datasets" collection
        image_datasets = exporter.list_datasets()

        # Foundational datasets: derive dataset-like rows from requests/resources
        fully_downloaded = []
        pending_download = []
        req_col = get_requests_collection()
        res_col = get_resources_collection()

        for r in req_col.find().sort("created_at", -1):
            req_id = r.get("request_id")
            if not req_id:
                continue

            # Count sampled and downloaded resources
            sampled_count = res_col.count_documents({
                "request_id": req_id,
                "status": {"$in": ["sampled", "downloaded"]},
            })
            downloaded_count = res_col.count_documents({
                "request_id": req_id,
                "status": "downloaded",
            })
            
            if sampled_count == 0:
                continue

            plan = r.get("plan", {})
            dataset_obj = {
                "_id": req_id,
                "name": r.get("query") or f"Request {req_id}",
                "classes": plan.get("classes", []),
                "total_samples": sampled_count,
                "downloaded_samples": downloaded_count,
                "created_at": r.get("created_at"),
                "data_type": plan.get("type", "unknown"),
            }
            
            # If all samples are downloaded, it's a complete dataset
            if downloaded_count > 0 and downloaded_count == sampled_count:
                fully_downloaded.append(dataset_obj)
            else:
                # Otherwise it's pending full download
                pending_download.append(dataset_obj)

        return {
            "datasets": image_datasets + fully_downloaded,
            "pending_datasets": pending_download
        }
    except Exception as e:
        logger.error(f"api_list_datasets failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/datasets/{dataset_id}")
async def api_delete_dataset(dataset_id: str):
    """Delete a dataset and all its associated resources."""
    try:
        req_col = get_requests_collection()
        res_col = get_resources_collection()
        
        # Delete the request
        req_result = req_col.delete_one({"request_id": dataset_id})
        
        # Delete all associated resources
        res_result = res_col.delete_many({"request_id": dataset_id})
        
        if req_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        logger.info(f"Deleted dataset {dataset_id}: {res_result.deleted_count} resources removed")
        
        return {
            "success": True,
            "message": f"Dataset deleted successfully",
            "resources_deleted": res_result.deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"api_delete_dataset failed for {dataset_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[dict] = []
    chat_id: Optional[str] = None


class ChatCreateRequest(BaseModel):
    title: str = "New Chat"


@app.post("/api/chat")
async def api_chat(request: ChatRequest):
    """Chat endpoint that uses OpenAI with RAG and persistence."""
    if not OPENAI_CLIENT:
        raise HTTPException(status_code=503, detail="OpenAI client not configured")
    
    try:
        import datetime
        import uuid
        
        chats_col = get_chats_collection()
        
        # Get or create chat
        chat_id = request.chat_id
        chat_doc = None
        
        if chat_id:
            chat_doc = chats_col.find_one({"chat_id": chat_id})
        
        if not chat_doc:
            # Create new chat
            chat_id = str(uuid.uuid4())
            chat_doc = {
                "chat_id": chat_id,
                "title": "New Chat",  # Will be updated with first message
                "messages": [],
                "created_at": datetime.datetime.now(datetime.timezone.utc),
                "updated_at": datetime.datetime.now(datetime.timezone.utc),
            }
            chats_col.insert_one(chat_doc)
        
        # RAG: Retrieve relevant context from past conversations
        rag_context = ""
        try:
            # Generate embedding for current message
            query_embedding = embedding_service.embed_text(request.message)
            
            # Search for similar messages in past chats (vector search)
            # Note: This requires MongoDB Atlas Search index on embeddings field
            # For now, we'll do a simple text search as fallback
            similar_chats = chats_col.find({
                "chat_id": {"$ne": chat_id},  # Exclude current chat
            }).limit(3)
            
            contexts = []
            for chat in similar_chats:
                for msg in chat.get("messages", []):
                    if msg.get("role") == "assistant" and "plan" in msg:
                        contexts.append(f"Previous plan: {msg.get('content', '')[:200]}")
            
            if contexts:
                rag_context = "\n\nRelevant context from past conversations:\n" + "\n".join(contexts[:2])
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
        
        # Build conversation with system prompt
        system_content = """You are a dataset planning assistant for DatasetSmith. 
Your job is to help users plan and create datasets.

When a user describes what dataset they want, you should:
1. Ask clarifying questions if needed
2. Extract the key parameters: classes/categories, total items, data type (images/text/numerical)
3. When you have enough information, respond with a JSON plan in this EXACT format:

{
  "action": "create_plan",
  "query": "brief description",
  "classes": ["class1", "class2"],
  "total_items": 50,
  "data_type": "images"
}

For example, if user says "I want a cats and dogs dataset with 10 images":
{
  "action": "create_plan",
  "query": "cats and dogs image dataset",
  "classes": ["cats", "dogs"],
  "total_items": 10,
  "data_type": "images"
}

Be conversational and helpful. Only output the JSON when you have all the information needed."""
        
        if rag_context:
            system_content += rag_context
        
        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history from DB
        for msg in chat_doc.get("messages", []):
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Call OpenAI
        response = OPENAI_CLIENT.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
        )
        
        assistant_message = response.choices[0].message.content or ""
        
        # Try to parse if it's a JSON plan
        plan = None
        request_id = None
        if "{" in assistant_message and "action" in assistant_message:
            try:
                json_start = assistant_message.find("{")
                json_end = assistant_message.rfind("}") + 1
                json_str = assistant_message[json_start:json_end]
                plan = json.loads(json_str)
                
                if plan.get("action") == "create_plan":
                    logger.info(f"Plan extracted: {plan}")
                else:
                    plan = None
            except:
                plan = None
        
        # Generate embeddings for messages
        try:
            user_embedding = embedding_service.embed_text(request.message)
            assistant_embedding = embedding_service.embed_text(assistant_message)
        except:
            user_embedding = None
            assistant_embedding = None
        
        # Save messages to DB
        user_msg_doc = {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "embedding": user_embedding
        }
        
        assistant_msg_doc = {
            "role": "assistant",
            "content": assistant_message,
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "embedding": assistant_embedding,
            "plan": plan,
            "request_id": request_id
        }
        
        # Update chat title if this is the first message
        update_data = {
            "$push": {
                "messages": {
                    "$each": [user_msg_doc, assistant_msg_doc]
                }
            },
            "$set": {
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
        }
        
        if len(chat_doc.get("messages", [])) == 0:
            # Set title from first message
            title = request.message[:50] + ("..." if len(request.message) > 50 else "")
            update_data["$set"]["title"] = title
        
        chats_col.update_one(
            {"chat_id": chat_id},
            update_data
        )
        
        return {
            "response": assistant_message,
            "plan": plan,
            "chat_id": chat_id,
            "request_id": request_id
        }
        
    except Exception as e:
        logger.error(f"Chat API failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chats")
async def api_list_chats():
    """List all chats."""
    try:
        chats_col = get_chats_collection()
        chats = []
        
        for chat in chats_col.find().sort("updated_at", -1):
            chats.append({
                "id": chat.get("chat_id"),
                "title": chat.get("title", "Untitled Chat"),
                "createdAt": chat.get("created_at").isoformat() if chat.get("created_at") else None,
                "updatedAt": chat.get("updated_at").isoformat() if chat.get("updated_at") else None,
                "messageCount": len(chat.get("messages", []))
            })
        
        return {"chats": chats}
    except Exception as e:
        logger.error(f"List chats failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chats/{chat_id}")
async def api_get_chat(chat_id: str):
    """Get a specific chat with all messages."""
    try:
        chats_col = get_chats_collection()
        chat = chats_col.find_one({"chat_id": chat_id})
        
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        messages = []
        for idx, msg in enumerate(chat.get("messages", [])):
            # Create unique ID using timestamp + index to avoid duplicates
            timestamp_str = msg.get("timestamp").isoformat() if msg.get("timestamp") else str(idx)
            messages.append({
                "id": f"msg-{timestamp_str}-{idx}",
                "role": msg.get("role"),
                "content": msg.get("content"),
                "timestamp": msg.get("timestamp").isoformat() if msg.get("timestamp") else None,
                "plan": msg.get("plan"),
                "request_id": msg.get("request_id")
            })
        
        return {
            "id": chat.get("chat_id"),
            "title": chat.get("title", "Untitled Chat"),
            "messages": messages,
            "createdAt": chat.get("created_at").isoformat() if chat.get("created_at") else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chats/{chat_id}")
async def api_delete_chat(chat_id: str):
    """Delete a chat."""
    try:
        chats_col = get_chats_collection()
        result = chats_col.delete_one({"chat_id": chat_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/datasets/{dataset_id}/preview")
async def api_dataset_preview(dataset_id: str):
    """Get preview samples for a dataset."""
    try:
        res_col = get_resources_collection()
        req_col = get_requests_collection()
        
        # Try to find as request_id first
        request_doc = req_col.find_one({"request_id": dataset_id})
        
        if request_doc:
            # Get some sample resources
            samples = []
            resources = res_col.find({
                "request_id": dataset_id,
                "status": {"$in": ["sampled", "downloaded"]}
            }).limit(6)
            
            for res in resources:
                samples.append({
                    "url": res.get("url"),
                    "title": res.get("title"),
                    "text": res.get("text"),
                    "content": res.get("content"),
                })
            
            plan = request_doc.get("plan", {})
            data_type = plan.get("type", "unknown")
            
            return {
                "samples": samples,
                "data_type": data_type,
                "total": len(samples)
            }
        
        # Fallback: return empty preview
        return {
            "samples": [],
            "data_type": "unknown",
            "total": 0
        }
        
    except Exception as e:
        logger.error(f"Preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{dataset_id}")
async def download(dataset_id: str):
    """Download dataset as ZIP."""
    try:
        # Try exporting as foundational request (UUID)
        if len(dataset_id) == 36:
            zip_path = exporter.create_request_zip(dataset_id)
            if zip_path:
                return FileResponse(
                    path=zip_path, 
                    filename=f"dataset_{dataset_id}.zip", 
                    media_type='application/zip'
                )
        
        # Fallback to old dataset export (ObjectId)
        temp_dir = Path(f"/tmp/ds_{dataset_id}")
        # Clean up if exists
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        exporter.export_dataset(dataset_id, output_dir=temp_dir)
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            has_files = False
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(temp_dir))
                    has_files = True
            
            if not has_files:
                # Add a placeholder file if empty
                zf.writestr("README.txt", "This dataset contains no images. Check logs for errors.")
        
        shutil.rmtree(temp_dir)
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=dataset_{dataset_id}.zip"}
        )
    except Exception as e:
        logger.error(f"Download failed for {dataset_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    print("\n🎨 OpenBench Publisher")
    print("📱 http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
