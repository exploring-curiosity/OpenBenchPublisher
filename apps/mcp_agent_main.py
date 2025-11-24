"""
OpenBench Publisher - MCP Agent for Dataset Building

This MCP agent provides tools for building license-clean dataset slices using Tavily search.
Deploy it with: uvx mcp-agent deploy
Connect from ChatGPT Plus web app to build datasets via natural language.
"""

import asyncio
from typing import Optional, List
import json
from uuid import uuid4
import csv

from mcp_agent.app import MCPApp
from mcp_agent.core.context import Context as AppContext

from obp.agents.dataset_smith import dataset_smith
from obp.cards import card_publisher
from obp.export import exporter
from obp.agents.foundational_gatherer import FoundationalGatherer
from obp.downloader import FoundationalDownloader

# Create the MCPApp for OpenBench Publisher
app = MCPApp(
    name="openbench_publisher",
    description="MCP agent for building license-clean dataset slices using Tavily search",
)


@app.async_tool(name="build_dataset_slice")
async def build_dataset_slice(
    classes: List[str],
    total: int = 100,
    min_size: int = 256,
    license_filter: str = "CC-BY",
    app_ctx: Optional[AppContext] = None,
) -> str:
    """
    Build a license-clean dataset slice using Tavily image search.
    
    Args:
        classes: List of class names (e.g., ["cat", "dog"])
        total: Total number of images to collect (default: 100)
        min_size: Minimum image dimension in pixels (default: 256)
        license_filter: License requirement (default: "CC-BY")
    
    Returns:
        JSON string with dataset ID, stats, and Data Card
    """
    logger = app_ctx.app.logger
    logger.info(f"Building dataset slice: classes={classes}, total={total}")
    
    try:
        manifest = await dataset_smith.build_slice(
            classes=classes,
            total=total,
            split=[0.7, 0.15, 0.15],
            license_filter=license_filter,
            min_size=min_size,
        )
        
        # Publish Data Card
        data_card = card_publisher.publish_data_card(
            dataset_id=manifest["dataset_id"],
            manifest=manifest,
            classes=classes,
        )
        
        # Format response
        card_md = card_publisher.format_card_markdown(data_card)
        
        result = {
            "dataset_id": manifest["dataset_id"],
            "total_images": manifest["total"],
            "stats": manifest["stats"],
            "data_card_markdown": card_md,
            "message": f"✅ Dataset built successfully! {manifest['total']} images across {len(classes)} classes."
        }
        
        logger.info(f"Dataset built: {manifest['dataset_id']}")
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Failed to build dataset: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@app.tool(name="list_datasets")
async def list_datasets(app_ctx: Optional[AppContext] = None) -> str:
    """
    List all available datasets in MongoDB.
    
    Returns:
        JSON string with list of datasets
    """
    logger = app_ctx.app.logger
    logger.info("Listing datasets")
    
    try:
        datasets = exporter.list_datasets()
        return json.dumps({
            "datasets": datasets,
            "count": len(datasets)
        }, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@app.tool(name="export_dataset")
async def export_dataset(
    dataset_id: str,
    app_ctx: Optional[AppContext] = None,
) -> str:
    """
    Export a dataset to organized train/val/test folders.
    
    Args:
        dataset_id: MongoDB dataset ID to export
    
    Returns:
        JSON string with export summary and paths
    """
    logger = app_ctx.app.logger
    logger.info(f"Exporting dataset: {dataset_id}")
    
    try:
        summary = exporter.export_dataset(dataset_id=dataset_id)
        return json.dumps({
            "message": "✅ Dataset exported successfully!",
            "output_dir": summary["output_dir"],
            "exported_counts": summary["exported_counts"],
            "total_exported": summary["total_exported"],
        }, indent=2)
    except Exception as e:
        logger.error(f"Failed to export dataset: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@app.async_tool(name="build_labeled_text_corpus")
async def build_labeled_text_corpus(
    labels: List[str],
    queries: List[str],
    limit_per_class: int = 3,
    sample_per_class: int = 2,
    app_ctx: Optional[AppContext] = None,
) -> str:
    logger = app_ctx.app.logger
    logger.info(
        f"Building labeled text corpus: labels={labels}, limit_per_class={limit_per_class}, sample_per_class={sample_per_class}"
    )

    if len(labels) != len(queries):
        return json.dumps(
            {
                "error": "labels and queries must have the same length",
                "labels_len": len(labels),
                "queries_len": len(queries),
            },
            indent=2,
        )

    gatherer = FoundationalGatherer()
    downloader = FoundationalDownloader()
    specs = []

    for label, query in zip(labels, queries):
        request_id = str(uuid4())
        logger.info(
            f"Building text class '{label}' with query '{query}' (request_id={request_id})"
        )
        try:
            count = gatherer.gather_and_store(query, "text", request_id, limit=limit_per_class)
            logger.info(f"Gathered {count} items for label '{label}'")
            if count == 0:
                continue

            sampled = gatherer.sample_resources(request_id, count_per_modality=sample_per_class)
            logger.info(f"Sampled {sampled} items for label '{label}'")

            downloaded = downloader.download_all(request_id)
            logger.info(f"Downloaded {downloaded} items for label '{label}'")

            specs.append({"label": label, "request_id": request_id})
        except Exception as e:
            logger.error(f"Failed to build text class '{label}': {e}")
            continue

    if not specs:
        return json.dumps(
            {"error": "no labeled text corpora could be built", "labels": labels}, indent=2
        )

    path = exporter.build_labeled_corpus(specs, modality="text")
    if not path:
        return json.dumps(
            {"error": "failed to build labeled text corpus", "labels": labels}, indent=2
        )

    row_count = 0
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for _ in reader:
                row_count += 1
    except Exception as e:
        logger.error(f"Failed to count rows in labeled text corpus: {e}")

    result = {
        "labels": labels,
        "path": path,
        "row_count": row_count,
        "message": f"Built labeled text corpus with {row_count} rows across {len(specs)} classes.",
    }
    return json.dumps(result, indent=2)


@app.async_tool(name="build_labeled_numerical_corpus")
async def build_labeled_numerical_corpus(
    labels: List[str],
    queries: List[str],
    limit_per_class: int = 3,
    sample_per_class: int = 2,
    app_ctx: Optional[AppContext] = None,
) -> str:
    logger = app_ctx.app.logger
    logger.info(
        f"Building labeled numerical corpus: labels={labels}, limit_per_class={limit_per_class}, sample_per_class={sample_per_class}"
    )

    if len(labels) != len(queries):
        return json.dumps(
            {
                "error": "labels and queries must have the same length",
                "labels_len": len(labels),
                "queries_len": len(queries),
            },
            indent=2,
        )

    gatherer = FoundationalGatherer()
    downloader = FoundationalDownloader()
    specs = []

    for label, query in zip(labels, queries):
        request_id = str(uuid4())
        logger.info(
            f"Building numerical class '{label}' with query '{query}' (request_id={request_id})"
        )
        try:
            count = gatherer.gather_and_store(query, "numerical", request_id, limit=limit_per_class)
            logger.info(f"Gathered {count} items for label '{label}'")
            if count == 0:
                continue

            sampled = gatherer.sample_resources(request_id, count_per_modality=sample_per_class)
            logger.info(f"Sampled {sampled} items for label '{label}'")

            downloaded = downloader.download_all(request_id)
            logger.info(f"Downloaded {downloaded} items for label '{label}'")

            specs.append({"label": label, "request_id": request_id})
        except Exception as e:
            logger.error(f"Failed to build numerical class '{label}': {e}")
            continue

    if not specs:
        return json.dumps(
            {"error": "no labeled numerical corpora could be built", "labels": labels}, indent=2
        )

    path = exporter.build_labeled_corpus(specs, modality="numerical")
    if not path:
        return json.dumps(
            {"error": "failed to build labeled numerical corpus", "labels": labels}, indent=2
        )

    row_count = 0
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for _ in reader:
                row_count += 1
    except Exception as e:
        logger.error(f"Failed to count rows in labeled numerical corpus: {e}")

    result = {
        "labels": labels,
        "path": path,
        "row_count": row_count,
        "message": f"Built labeled numerical corpus with {row_count} rows across {len(specs)} classes.",
    }
    return json.dumps(result, indent=2)


async def main():
    """Test the dataset builder locally."""
    async with app.run() as agent_app:
        print("\n" + "="*80)
        print("OpenBench Publisher - Local Test")
        print("="*80 + "\n")
        
        # Test building a small dataset
        print("Building test dataset: 10 images (cat, dog)...\n")
        result = await build_dataset_slice(
            classes=["cat", "dog"],
            total=10,
            min_size=256,
            app_ctx=agent_app.context,
        )
        print("Result:")
        print(result)
        
        print("\n" + "="*80)
        print("✅ Local test complete!")
        print("="*80)
        print("\nTo deploy as MCP server:")
        print("  uvx mcp-agent deploy")
        print("\nThen connect from ChatGPT Plus web app!")


if __name__ == "__main__":
    asyncio.run(main())

# Deploy as MCP server:
# > uvx mcp-agent deploy
#
# Then connect from ChatGPT Plus web app:
# Settings → Integrations → Add MCP Server → Paste deployed URL
