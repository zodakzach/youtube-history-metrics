import redis
import json
from typing import Optional
from dotenv import load_dotenv
import os
from .data_store import DataStore

# Load environment variables from .env file
load_dotenv()

# Prefer Upstash connection URL when available, otherwise fall back to the local Redis host.
upstash_url = os.getenv("UPSTASH_REDIS_URL")
if upstash_url:
    # Upstash issues TLS URLs, so redis.from_url will negotiate SSL automatically for rediss:// URIs.
    redis_client = redis.from_url(upstash_url, db=0)
else:
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)


def save_data_store(session_id: str, data_store: DataStore, expire: int = 3600):
    """Serialize and save the DataStore object in Redis."""
    redis_client.set(session_id, json.dumps(data_store.to_dict()), ex=expire)


def load_data_store(session_id: str) -> Optional[DataStore]:
    """Load and deserialize the DataStore object from Redis."""
    data = redis_client.get(session_id)
    if data:
        return DataStore.from_dict(json.loads(data))
    return None


def delete_data_store(session_id: str):
    """Delete the DataStore object from Redis."""
    redis_client.delete(session_id)
