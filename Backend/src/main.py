import json
import logging
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import data_processing, models
from .api_routes import router as api_router
from .constants import SESSION_COOKIE_NAME
from .data_store import DataStore, DataStoreState
from .session_pipeline import (
    delete_store,
    ensure_datastore,
    generate_analytics_context,
    load_store,
    new_session_id,
    process_data_pipeline,
    save_store,
)

app = FastAPI()

# Mount the "static" directory at the path "/static"
app.mount("/static", StaticFiles(directory="../Frontend/static"), name="static")

templates = Jinja2Templates(directory="../Frontend/templates")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app.include_router(api_router)
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
    session_id = request.cookies.get(SESSION_COOKIE_NAME) or new_session_id()

    # 2) If a store exists for this session, delete it so we start fresh
    existing_store = await load_store(session_id)
    if existing_store:
        try:
            await delete_store(session_id)
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
        await save_store(session_id, data_store)

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
            await save_store(session_id, data_store)
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
            await save_store(session_id, data_store)
        except Exception as persist_err:
            logger.error("Failed to persist error state: %s", persist_err)

        return _template_with_cookie(
            "partials/steps/verify_and_extract.html",
            request,
            session_id,
            {"error": error_message},
        )


@app.post("/status", response_class=HTMLResponse)
async def status(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        # No session yet; instruct the client to upload first
        return templates.TemplateResponse(
            "partials/steps/verify_and_extract.html", context={"request": request}
        )

    store = await load_store(session_id)
    store = ensure_datastore(store)

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
        await save_store(session_id, store)
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

    data_store = await load_store(session_id)
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

    await save_store(session_id, data_store)

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

    data_store = await load_store(session_id)
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

    await save_store(session_id, data_store)

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
