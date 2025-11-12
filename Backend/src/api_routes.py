import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import data_processing, models
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["api"])


@router.post("/load-data")
async def api_load_data(
    request: Request, file_input: UploadFile, background_tasks: BackgroundTasks
):
    session_id = request.cookies.get(SESSION_COOKIE_NAME) or new_session_id()

    existing_store = await load_store(session_id)
    if existing_store:
        try:
            await delete_store(session_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to delete existing API session store %s: %s", session_id, exc
            )

    data_store = DataStore()
    data_store.error_message = ""
    if hasattr(data_store, "state_queue"):
        data_store.state_queue.clear()
    data_store.update_state(DataStoreState.REQUESTING_DATA)

    try:
        if not file_input:
            raise ValueError("No file provided.")

        raw = await file_input.read()
        if not raw:
            raise ValueError("Uploaded file is empty.")
        decoded = raw.decode("utf-8")
        json_data = json.loads(decoded)

        watched_items = [models.WatchedItem.model_validate(item) for item in json_data]
        (
            data_store.filtered_json_data,
            data_store.removed_video_count,
        ) = data_processing.filter_data(watched_items)

        await save_store(session_id, data_store)
        background_tasks.add_task(process_data_pipeline, session_id)

        return _json_with_cookie(
            request,
            session_id,
            {
                "status": "ok",
                "sessionId": session_id,
                "state": DataStoreState.REQUESTING_DATA.value,
                "removedVideoCount": data_store.removed_video_count,
            },
        )

    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        logger.error("API load_data error: %s", error_message)
        data_store.error_message = error_message
        try:
            await save_store(session_id, data_store)
        except Exception as persist_err:  # pragma: no cover - defensive logging
            logger.error("Failed to persist API error state: %s", persist_err)

        return _json_with_cookie(
            request,
            session_id,
            {"status": "error", "error": error_message},
            status_code=400,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        error_message = "An unexpected error occurred while loading data."
        logger.exception("Unexpected API error in load_data: %s", exc)
        data_store.error_message = error_message
        try:
            await save_store(session_id, data_store)
        except Exception as persist_err:
            logger.error("Failed to persist unexpected API error: %s", persist_err)

        return _json_with_cookie(
            request,
            session_id,
            {"status": "error", "error": error_message},
            status_code=500,
        )


@router.get("/status")
async def api_status(request: Request, session_id: Optional[str] = None):
    resolved_session = session_id or request.cookies.get(SESSION_COOKIE_NAME)
    if not resolved_session:
        raise HTTPException(status_code=400, detail="Session not found. Upload data first.")

    store = await load_store(resolved_session)
    store = ensure_datastore(store)

    current_state = store.current_state()
    payload = {
        "sessionId": resolved_session,
        "state": current_state.value,
        "removedVideoCount": store.removed_video_count,
        "hasFilteredData": bool(store.filtered_json_data),
        "error": store.error_message or None,
    }

    if store.error_message:
        return JSONResponse(payload, status_code=400)

    if current_state == DataStoreState.COMPLETE:
        store.process_next_state()
        await save_store(resolved_session, store)
        payload["ready"] = True

    return _json_with_cookie(request, resolved_session, payload)


@router.get("/analytics")
async def api_analytics(request: Request, session_id: Optional[str] = None):
    resolved_session = session_id or request.cookies.get(SESSION_COOKIE_NAME)
    if not resolved_session:
        raise HTTPException(status_code=400, detail="Session not found. Upload data first.")

    store = await load_store(resolved_session)
    if not store or store.current_state() != DataStoreState.COMPLETE:
        raise HTTPException(status_code=409, detail="Analytics are not ready yet.")

    context = await generate_analytics_context(resolved_session)
    return _json_with_cookie(
        request,
        resolved_session,
        {"sessionId": resolved_session, "analytics": context},
    )


@router.get("/videos")
async def api_videos(
    request: Request, page: int = 1, session_id: Optional[str] = None
):
    resolved_session = session_id or request.cookies.get(SESSION_COOKIE_NAME)
    if not resolved_session:
        raise HTTPException(status_code=400, detail="Session not found. Upload data first.")

    store = await load_store(resolved_session)
    store = ensure_datastore(store)

    if not store.unique_vids:
        return _json_with_cookie(
            request,
            resolved_session,
            {"sessionId": resolved_session, "videos": [], "page": 1, "totalPages": 0},
        )

    total_pages = max(store.num_of_pages, 1)
    current_page = max(1, min(page, total_pages))
    start_index = (current_page - 1) * store.max_rows
    end_index = min(start_index + store.max_rows, len(store.unique_vids))

    store.page_num = current_page
    await save_store(resolved_session, store)

    items = [
        {
            "index": absolute_index + 1,
            "title": video[0],
            "channel": video[1],
        }
        for absolute_index, video in enumerate(
            store.unique_vids[start_index:end_index], start=start_index
        )
    ]

    return _json_with_cookie(
        request,
        resolved_session,
        {
            "sessionId": resolved_session,
            "videos": items,
            "page": current_page,
            "totalPages": total_pages,
            "pageSize": store.max_rows,
            "totalRecords": len(store.unique_vids),
        },
    )


def _json_with_cookie(
    request: Request, session_id: str, payload: dict, status_code: int = 200
) -> JSONResponse:
    response = JSONResponse(payload, status_code=status_code)
    if not request.cookies.get(SESSION_COOKIE_NAME):
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 60 * 24 * 7,
        )
    return response

