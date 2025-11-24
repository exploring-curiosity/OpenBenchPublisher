"""MCP Server for OpenBench Publisher."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import uvicorn

from obp.config import settings
from obp.agents.dataset_smith import dataset_smith
from obp.cards import card_publisher
from obp.db import get_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenBench Publisher MCP Server",
    description="MCP-native research agent",
    version="0.1.0",
)


class SliceBuildRequest(BaseModel):
    """Request to build a dataset slice."""
    classes: List[str]
    total: int = 500
    split: List[float] = [0.7, 0.15, 0.15]
    license_filter: str = "CC-BY"
    min_size: int = 512
    include_domains: Optional[List[str]] = None


class SliceBuildResponse(BaseModel):
    """Response from slice build."""
    dataset_id: str
    manifest: Dict[str, Any]
    data_card: Dict[str, Any]
    data_card_markdown: str


@app.post("/tools/obp.slice.build", response_model=SliceBuildResponse)
async def build_slice(request: SliceBuildRequest):
    """Build a license-clean dataset slice (MCP Tool: obp.slice.build)."""
    try:
        logger.info(f"Building slice: {request.classes}")
        
        manifest = dataset_smith.build_slice(
            classes=request.classes,
            total=request.total,
            split=request.split,
            license_filter=request.license_filter,
            min_size=request.min_size,
            include_domains=request.include_domains,
        )
        
        data_card = card_publisher.publish_data_card(
            dataset_id=manifest["dataset_id"],
            manifest=manifest,
            classes=request.classes,
        )
        
        card_md = card_publisher.format_card_markdown(data_card)
        
        return SliceBuildResponse(
            dataset_id=manifest["dataset_id"],
            manifest=manifest,
            data_card=data_card,
            data_card_markdown=card_md,
        )
    
    except Exception as e:
        logger.error(f"Slice build failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = get_db()
        db.command('ping')
        return {"status": "healthy", "mongodb": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "OpenBench Publisher MCP Server",
        "version": "0.1.0",
        "tools": ["/tools/obp.slice.build"],
    }


def main():
    """Start the MCP server."""
    logger.info(f"Starting OBP MCP Server on {settings.app_host}:{settings.app_port}")
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)


if __name__ == "__main__":
    main()
