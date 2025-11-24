"""Configuration management for OBP."""

import os
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load .env file
load_dotenv()


class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    
    # API Keys
    tavily_api_key: str
    voyage_api_key: Optional[str] = None
    
    # MongoDB
    mongodb_uri: str
    mongodb_db: str = "obp"
    
    # Object Storage (optional)
    object_store_bucket: Optional[str] = None
    object_store_region: Optional[str] = "us-east-1"
    
    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # Paths
    data_dir: Path = Path("./data")
    cache_dir: Path = Path("./cache")
    
    class Config:
        case_sensitive = False


# Load and fix MongoDB URI encoding
def fix_mongodb_uri(uri: str) -> str:
    """Fix MongoDB URI encoding for special characters in password."""
    if not uri or "mongodb" not in uri:
        return uri
    # Check if password has unencoded @ symbol
    if uri.count("@") > 1 and "://" in uri:
        try:
            protocol, rest = uri.split("://", 1)
            if "@" in rest:
                creds, host_part = rest.rsplit("@", 1)  # Split from right to get last @
                if ":" in creds:
                    user, pwd = creds.split(":", 1)
                    # Only replace @ in password, don't encode other chars
                    if "@" in pwd and "%40" not in pwd:
                        pwd = pwd.replace("@", "%40")
                    return f"{protocol}://{user}:{pwd}@{host_part}"
        except Exception as e:
            import logging
            logging.error(f"Failed to fix MongoDB URI: {e}")
    return uri

# Load settings from environment
settings = Settings(
    tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
    voyage_api_key=os.getenv("VOYAGE_API_KEY"),
    mongodb_uri=fix_mongodb_uri(os.getenv("MONGODB_URI", "")),
    mongodb_db=os.getenv("MONGODB_DB", "obp"),
    app_host=os.getenv("APP_HOST", "0.0.0.0"),
    app_port=int(os.getenv("APP_PORT", "8000")),
)

# Ensure directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.cache_dir.mkdir(parents=True, exist_ok=True)
