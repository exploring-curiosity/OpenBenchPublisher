"""Dagster definitions for DatasetSmith."""

from dagster import Definitions, asset, AssetExecutionContext
from obp.agents.dataset_smith import get_dataset_smith
from obp.db import get_resources_collection, get_requests_collection
import logging

logger = logging.getLogger(__name__)


@asset
def sample_dataset(context: AssetExecutionContext) -> dict:
    """Sample a dataset by collecting a few images per class."""
    context.log.info("Starting dataset sampling")
    
    # This is a placeholder - in real usage, this would be triggered by the API
    return {
        "status": "sampled",
        "message": "Dataset sampling completed"
    }


@asset
def full_dataset_download(context: AssetExecutionContext, sample_dataset: dict) -> dict:
    """Download full dataset after sampling is complete."""
    context.log.info("Starting full dataset download")
    
    # This is a placeholder - in real usage, this would be triggered by the API
    return {
        "status": "downloaded",
        "message": "Full dataset download completed"
    }


# Define the Dagster definitions
defs = Definitions(
    assets=[sample_dataset, full_dataset_download],
)
