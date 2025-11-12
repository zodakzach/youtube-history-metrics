import asyncio
import json
import logging
import uuid
from typing import Optional

from . import analytics, api_handling, data_processing, visualization
from .data_store import DataStore, DataStoreState
from .redis_utils import delete_data_store, load_data_store, save_data_store

logger = logging.getLogger(__name__)


async def load_store(session_id: str) -> Optional[DataStore]:
    """Fetch a DataStore object from Redis on a worker thread."""
    return await asyncio.to_thread(load_data_store, session_id)


async def save_store(session_id: str, store: DataStore) -> None:
    """Persist the DataStore to Redis on a worker thread."""
    await asyncio.to_thread(save_data_store, session_id, store)


async def delete_store(session_id: str) -> None:
    """Remove the stored DataStore from Redis."""
    await asyncio.to_thread(delete_data_store, session_id)


def ensure_datastore(store: Optional[DataStore]) -> DataStore:
    """Return a DataStore instance, creating one when missing."""
    return store if store is not None else DataStore()


def new_session_id() -> str:
    return str(uuid.uuid4())


async def process_data_pipeline(session_id: str) -> None:
    """Run the data ingestion + analytics pipeline."""
    try:
        data_ready = await request_data(session_id)

        if not data_ready:
            return

        await generate_analytics(session_id)
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Pipeline error for session %s: %s", session_id, e)
        store = await load_store(session_id)
        store = ensure_datastore(store)
        store.error_message = "Failed to process data pipeline."
        try:
            await save_store(session_id, store)
        except Exception as persist_err:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to persist pipeline error for session %s: %s",
                session_id,
                persist_err,
            )


async def request_data(session_id: str) -> bool:
    store = await load_store(session_id)
    store = ensure_datastore(store)

    try:
        if not getattr(store, "filtered_json_data", None):
            raise ValueError("No filtered data found to request details for.")

        youtube_videos = data_processing.json_to_youtube_videos(
            store.filtered_json_data
        )

        if not youtube_videos:
            raise ValueError("No videos available after filtering.")

        vid_info_df = await api_handling.request_data(youtube_videos)

        store.complete_data = data_processing.merge_data(
            vid_info_df=vid_info_df, videos=youtube_videos
        )

        store.process_next_state()
        store.update_state(DataStoreState.GENERATING_ANALYTICS)

        await save_store(session_id, store)
        return True

    except json.JSONDecodeError as e:
        logger.error("JSON decoding error during request_data: %s", e)
        store.error_message = "Invalid JSON encountered while requesting data."
        await save_store(session_id, store)
        return False

    except ValueError as e:
        logger.error("Validation error during request_data: %s", e)
        store.error_message = str(e)
        await save_store(session_id, store)
        return False

    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error during request_data: %s", e)
        store.error_message = f"Request step failed: {e}"
        await save_store(session_id, store)
        return False


async def generate_analytics(session_id: str) -> None:
    """Generates analytics and updates Redis."""
    store = await load_store(session_id)
    store = ensure_datastore(store)

    try:
        complete_data = getattr(store, "complete_data", None)
        if complete_data is None:
            raise ValueError("No complete data available to generate analytics.")
        if not hasattr(complete_data, "columns"):
            raise ValueError("Stored dataset is invalid; expected tabular data.")

        required_columns = {"title", "channelTitle"}
        missing_columns = [
            col for col in required_columns if col not in complete_data.columns
        ]
        if missing_columns:
            raise ValueError(
                "Complete data missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        store.page_num = 1
        store.unique_vids = (
            complete_data[["title", "channelTitle"]]
            .drop_duplicates()
            .to_records(index=False)
            .tolist()
        )
        store.num_of_pages = (
            len(store.unique_vids) + store.max_rows - 1
        ) // store.max_rows

        store.process_next_state()
        store.update_state(DataStoreState.COMPLETE)

        await save_store(session_id, store)

    except ValueError as e:
        logger.error("Validation error generating analytics: %s", e)
        store.error_message = str(e)
        await save_store(session_id, store)

    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Error generating analytics: %s", e)
        store.error_message = "Failed to generate analytics."
        await save_store(session_id, store)


async def generate_analytics_context(session_id: str) -> dict:
    """Generates the context for the analytics template."""
    store = await load_store(session_id)
    store = ensure_datastore(store)

    if getattr(store, "complete_data", None) is None:
        return {
            "start_index": 0,
            "num_of_pages": 0,
            "unique_vids": [],
            "total_vids": 0,
            "total_unique_channels": 0,
        }

    context = {
        "start_index": 0,
        "num_of_pages": store.num_of_pages,
        "unique_vids": store.unique_vids[: store.max_rows],
        "total_vids": int(getattr(store.complete_data, "shape", [0, 0])[0]),
        "total_unique_channels": analytics.unique_channels(store.complete_data),
    }

    updated_context = visualization.prepare_visualizations(store.complete_data, context)
    final_context = analytics.calculate_total_watch_time(
        store.complete_data["duration"].tolist(), updated_context
    )

    return final_context

