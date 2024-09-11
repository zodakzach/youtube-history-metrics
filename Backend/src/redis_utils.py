import redis
import json
from typing import Optional
from .data_store import DataStore

# Initialize Redis connection
redis_client = redis.Redis(host="localhost", port=6379, db=0)


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
