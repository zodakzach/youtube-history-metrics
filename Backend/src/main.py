import json
import uuid
import asyncio
import logging
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import models
from . import data_processing
from . import api_handling
from . import analytics
from . import visualization
from .redis_utils import save_data_store, load_data_store, delete_data_store
from .data_store import DataStore, DataStoreState

app = FastAPI()

# Mount the "static" directory at the path "/static"
app.mount("/static", StaticFiles(directory="../Frontend/static"), name="static")

templates = Jinja2Templates(directory="../Frontend/templates")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SESSION_COOKIE_NAME = "session_id"


# Middleware to manage session ID
@app.middleware("http")
async def add_session_id(request: Request, call_next):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    response = await call_next(request)
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(key=SESSION_COOKIE_NAME, value=session_id, httponly=True)
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context=context)


def _new_session_id() -> str:
    return str(uuid.uuid4())


async def _load_store(session_id: str) -> Optional["DataStore"]:
    return await asyncio.to_thread(load_data_store, session_id)


async def _save_store(session_id: str, store: "DataStore") -> None:
    await asyncio.to_thread(save_data_store, session_id, store)


async def _delete_store(session_id: str) -> None:
    await asyncio.to_thread(delete_data_store, session_id)


def _ensure_datastore(store: Optional["DataStore"]) -> "DataStore":
    if store is None:
        return DataStore()
    return store


def _template_with_cookie(
    template_name: str,
    request: Request,
    session_id: str,
    context: Optional[dict] = None,
):
    # Helper to set cookie on TemplateResponse
    if context is None:
        context = {}
    context["request"] = request
    response = templates.TemplateResponse(template_name, context=context)
    if not request.cookies.get(SESSION_COOKIE_NAME):
        # Set a durable cookie if not present
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            secure=False,  # set True if served over HTTPS
            max_age=60 * 60 * 24 * 7,
        )
    return response


@app.post("/loadData", response_class=HTMLResponse)
async def load_data(
    file_input: UploadFile, request: Request, background_tasks: BackgroundTasks
):
    # 1) Ensure session_id exists
    session_id = request.cookies.get(SESSION_COOKIE_NAME) or _new_session_id()

    # 2) If a store exists for this session, delete it so we start fresh
    existing_store = await _load_store(session_id)
    if existing_store:
        try:
            await _delete_store(session_id)
        except Exception as e:
            # Not fatal, but log it
            logger.warning(
                "Failed to delete existing DataStore for session %s: %s",
                session_id,
                e,
            )

    # 3) Create a fresh store
    data_store = DataStore()
    data_store.error_message = ""
    # Ensure queue exists before clear
    if hasattr(data_store, "state_queue"):
        data_store.state_queue.clear()
    data_store.update_state(DataStoreState.REQUESTING_DATA)

    try:
        # Basic validation of file input
        if not file_input:
            raise ValueError("No file provided.")

        # 4) Read and parse the input file
        raw = await file_input.read()
        if not raw:
            raise ValueError("Uploaded file is empty.")
        decoded = raw.decode("utf-8")
        json_data = json.loads(decoded)

        # Validate and normalize items
        watched_items = [models.WatchedItem.model_validate(item) for item in json_data]

        # 5) Filter/preprocess
        (
            data_store.filtered_json_data,
            data_store.removed_video_count,
        ) = data_processing.filter_data(watched_items)

        # 6) Persist initial store state
        await _save_store(session_id, data_store)

        # 7) Kick off the background pipeline
        background_tasks.add_task(process_data_pipeline, session_id)

        # 8) Return next-step template; set cookie if needed
        return _template_with_cookie(
            "partials/steps/verify_and_extract.html",
            request,
            session_id,
        )

    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as e:
        # Known/expected failures
        error_message = f"{type(e).__name__}: {e}"
        logger.error("Load data error: %s", error_message)
        data_store.error_message = error_message
        try:
            await _save_store(session_id, data_store)
        except Exception as persist_err:
            logger.error("Failed to persist error state: %s", persist_err)

        return _template_with_cookie(
            "partials/steps/verify_and_extract.html",
            request,
            session_id,
            {"error": error_message},
        )
    except Exception as e:
        # Unexpected failures
        error_message = "An unexpected error occurred while loading data."
        logger.exception("Unexpected error in load_data: %s", e)
        data_store.error_message = error_message
        try:
            await _save_store(session_id, data_store)
        except Exception as persist_err:
            logger.error("Failed to persist error state: %s", persist_err)

        return _template_with_cookie(
            "partials/steps/verify_and_extract.html",
            request,
            session_id,
            {"error": error_message},
        )


async def process_data_pipeline(session_id: str):
    """Handles requesting data from APIs and generating analytics."""
    try:
        # Step 1: Request Data from API
        data_ready = await request_data(session_id)

        if not data_ready:
            # request_data already recorded the failure; stop the pipeline here
            return

        # Step 2: Generate Analytics
        await generate_analytics(session_id)
    except Exception as e:
        # Ensure failures are recorded in the store so UI can read them via /status
        logger.exception("Pipeline error for session %s: %s", session_id, e)
        store = await _load_store(session_id)
        store = _ensure_datastore(store)
        store.error_message = "Failed to process data pipeline."
        try:
            await _save_store(session_id, store)
        except Exception as persist_err:
            logger.error(
                "Failed to persist pipeline error for session %s: %s",
                session_id,
                persist_err,
            )


async def request_data(session_id: str) -> bool:
    store = await _load_store(session_id)
    store = _ensure_datastore(store)

    try:
        if not getattr(store, "filtered_json_data", None):
            raise ValueError("No filtered data found to request details for.")

        # Convert filtered_json_data to domain objects
        youtube_videos = data_processing.json_to_youtube_videos(
            store.filtered_json_data
        )

        if not youtube_videos:
            raise ValueError("No videos available after filtering.")

        # Request data for YouTube videos (assumed async)
        vid_info_df = await api_handling.request_data(youtube_videos)

        # Merge video data with additional info
        store.complete_data = data_processing.merge_data(
            vid_info_df=vid_info_df, videos=youtube_videos
        )

        # Advance the state machine into the analytics phase
        store.process_next_state()
        store.update_state(DataStoreState.GENERATING_ANALYTICS)

        await _save_store(session_id, store)
        return True

    except json.JSONDecodeError as e:
        logger.error("JSON decoding error during request_data: %s", e)
        store.error_message = "Invalid JSON encountered while requesting data."
        await _save_store(session_id, store)
        return False

    except ValueError as e:
        logger.error("Validation error during request_data: %s", e)
        store.error_message = str(e)
        await _save_store(session_id, store)
        return False

    except Exception as e:
        # Covers API/network or any unexpected failures
        logger.exception("Error during request_data: %s", e)
        store.error_message = f"Request step failed: {e}"
        await _save_store(session_id, store)
        return False


async def generate_analytics(session_id: str):
    """Generates analytics and updates Redis."""
    store = await _load_store(session_id)
    store = _ensure_datastore(store)

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

        # Example analytics code
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

        # Move state machine to COMPLETE after finishing analytics
        store.process_next_state()
        store.update_state(DataStoreState.COMPLETE)

        await _save_store(session_id, store)

    except ValueError as e:
        logger.error("Validation error generating analytics: %s", e)
        store.error_message = str(e)
        await _save_store(session_id, store)

    except Exception as e:
        logger.exception("Error generating analytics: %s", e)
        store.error_message = "Failed to generate analytics."
        await _save_store(session_id, store)


async def generate_analytics_context(session_id: str) -> dict:
    """Generates the context for the analytics template."""
    store = await _load_store(session_id)
    store = _ensure_datastore(store)

    if getattr(store, "complete_data", None) is None:
        # Provide a minimal safe context if missing to prevent template errors
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


@app.post("/status", response_class=HTMLResponse)
async def status(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        # No session yet; instruct the client to upload first
        return templates.TemplateResponse(
            "partials/steps/verify_and_extract.html", context={"request": request}
        )

    store = await _load_store(session_id)
    store = _ensure_datastore(store)

    current_state = store.current_state()
    logger.info("Session %s state: %s", session_id, current_state)

    # If there is an error, show request_data step with error
    if store.error_message:
        error_template = (
            "partials/steps/request_data.html"
            if current_state
            in (
                DataStoreState.GENERATING_ANALYTICS,
                DataStoreState.COMPLETE,
            )
            else "partials/steps/verify_and_extract.html"
        )
        return _template_with_cookie(
            error_template,
            request,
            session_id,
            {"error": store.error_message},
        )

    # No errors, show the appropriate step for the current state
    if current_state == DataStoreState.COMPLETE:
        store.process_next_state()
        await _save_store(session_id, store)
        context = await generate_analytics_context(session_id)
        return _template_with_cookie(
            "partials/analytics.html", request, session_id, context
        )

    if current_state == DataStoreState.GENERATING_ANALYTICS:
        return _template_with_cookie(
            "partials/steps/request_data.html", request, session_id
        )

    # Default to the verify/extract step for new or requesting sessions
    return _template_with_cookie(
        "partials/steps/verify_and_extract.html", request, session_id
    )


@app.get("/instructions", response_class=HTMLResponse)
async def instructions(request: Request):
    return templates.TemplateResponse("instructions.html", {"request": request})


@app.post("/nextTablePage", response_class=HTMLResponse)
async def next_table_page(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return templates.TemplateResponse(
            "partials/error.html",
            context={
                "request": request,
                "error": "No session found. Please reload data.",
            },
        )

    data_store = await _load_store(session_id)
    if not data_store:
        return templates.TemplateResponse(
            "partials/error.html",
            context={
                "request": request,
                "error": "No session found. Please reload data.",
            },
        )

    # Clamp to valid range
    if data_store.num_of_pages is None or data_store.num_of_pages <= 0:
        data_store.page_num = 1
    else:
        if data_store.page_num < data_store.num_of_pages:
            data_store.page_num += 1
        data_store.page_num = max(1, min(data_store.page_num, data_store.num_of_pages))

    await _save_store(session_id, data_store)

    total = len(data_store.unique_vids) if data_store.unique_vids else 0
    start_index = (data_store.page_num - 1) * data_store.max_rows
    end_index = min(start_index + data_store.max_rows, total)

    context = {
        "request": request,
        "start_index": start_index,
        "unique_vids": data_store.unique_vids[start_index:end_index]
        if data_store.unique_vids
        else [],
    }

    return templates.TemplateResponse("partials/vids_table.html", context=context)


@app.post("/prevTablePage", response_class=HTMLResponse)
async def prev_table_page(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return templates.TemplateResponse(
            "partials/error.html",
            context={
                "request": request,
                "error": "No session found. Please reload data.",
            },
        )

    data_store = await _load_store(session_id)
    if not data_store:
        return templates.TemplateResponse(
            "partials/error.html",
            context={
                "request": request,
                "error": "No session found. Please reload data.",
            },
        )

    if data_store.page_num > 1:
        data_store.page_num -= 1
    data_store.page_num = max(1, data_store.page_num)

    await _save_store(session_id, data_store)

    total = len(data_store.unique_vids) if data_store.unique_vids else 0
    start_index = (data_store.page_num - 1) * data_store.max_rows
    end_index = min(start_index + data_store.max_rows, total)

    context = {
        "request": request,
        "start_index": start_index,
        "unique_vids": data_store.unique_vids[start_index:end_index]
        if data_store.unique_vids
        else [],
    }

    return templates.TemplateResponse("partials/vids_table.html", context=context)
