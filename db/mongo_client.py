import os
from typing import Optional
from pymongo import MongoClient

# Simple MongoDB helper. Uses MONGO_URI and MONGO_DB environment variables.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB", "santa")

_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def get_mongo_db():
    """Return a pymongo database instance.

    Note: this will raise ImportError at import time if `pymongo` is not
    installed. Install with `pip install pymongo`.
    """
    client = get_mongo_client()
    return client[MONGO_DB_NAME]
