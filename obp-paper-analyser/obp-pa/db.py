from functools import lru_cache

from pymongo import MongoClient

from .config import settings


@lru_cache()
def get_mongo_client() -> MongoClient:
    if not settings.mongodb_uri:
        raise RuntimeError(
            "MONGODB_URI is not set. Add it to your .env, e.g. MONGODB_URI=\"mongodb+srv://user:pass@cluster.mongodb.net\"."
        )
    return MongoClient(settings.mongodb_uri)


def get_db():
    if not settings.mongodb_db:
        raise RuntimeError("MONGODB_DB is not set. Add it to your .env, e.g. MONGODB_DB=\"obp\".")
    client = get_mongo_client()
    return client[settings.mongodb_db]


def get_papers_collection():
    return get_db()["papers"]


def get_claims_collection():
    return get_db()["claims"]
