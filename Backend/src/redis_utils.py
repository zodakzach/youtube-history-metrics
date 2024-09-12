import redis
import json
from typing import Optional
from dotenv import load_dotenv  # Import load_dotenv to load .env file
import os
from .data_store import DataStore

# Load environment variables from .env file
load_dotenv()

# Get Redis host and port from environment variables
redis_host = os.getenv("REDIS_HOST", "localhost")  # Default to 'localhost' if not found
redis_port = int(os.getenv("REDIS_PORT", 6379))    # Default to 6379 if not found

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
