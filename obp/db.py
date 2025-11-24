"""MongoDB Atlas client and helpers."""

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from typing import Optional
import logging

from obp.config import settings

logger = logging.getLogger(__name__)


class MongoDBClient:
    """MongoDB Atlas client wrapper."""
    
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
    
    def connect(self) -> Database:
        """Connect to MongoDB Atlas and return database instance."""
        if self._db is not None:
            return self._db
        
        logger.info(f"Connecting to MongoDB Atlas: {settings.mongodb_db}")
        self._client = MongoClient(settings.mongodb_uri)
        self._db = self._client[settings.mongodb_db]
        
        # Ping to verify connection
        self._client.admin.command('ping')
        logger.info("Successfully connected to MongoDB Atlas")
        
        return self._db
    
    def get_collection(self, name: str) -> Collection:
        """Get a collection by name."""
        if self._db is None:
            self.connect()
        return self._db[name]
    
    def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")


# Global client instance (lazy-loaded)
_db_client = None

def get_db_client():
    """Get or create the global MongoDB client instance."""
    global _db_client
    if _db_client is None:
        _db_client = MongoDBClient()
    return _db_client

# Lazy accessor
class _MongoDBClientAccessor:
    def __getattr__(self, name):
        return getattr(get_db_client(), name)

db_client = _MongoDBClientAccessor()


def get_db() -> Database:
    """Get MongoDB database instance."""
    return db_client.connect()


def get_collection(name: str) -> Collection:
    """Get a MongoDB collection."""
    return db_client.get_collection(name)


# Collection helpers
def get_papers_collection() -> Collection:
    """Get papers collection."""
    return get_collection("papers")


def get_claims_collection() -> Collection:
    """Get claims collection."""
    return get_collection("claims")


def get_assets_collection() -> Collection:
    """Get assets collection."""
    return get_collection("assets")


def get_datasets_collection() -> Collection:
    """Get datasets collection."""
    return get_collection("datasets")


def get_runs_collection() -> Collection:
    """Get runs collection."""
    return get_collection("runs")


def get_cards_collection() -> Collection:
    """Get cards collection."""
    return get_collection("cards")


def get_resources_collection() -> Collection:
    """Get foundational resources collection."""
    return get_collection("resources")


def get_requests_collection() -> Collection:
    """Get foundational requests collection."""
    return get_collection("requests")


def get_chats_collection() -> Collection:
    """Get chats collection for persistent chat storage."""
    return get_collection("chats")
