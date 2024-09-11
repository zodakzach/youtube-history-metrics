import json
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
import uuid
from .redis_utils import save_data_store, load_data_store, delete_data_store
from .data_store import DataStore, DataStoreState
import asyncio

app = FastAPI()

# Mount the "static" directory at the path "/static"
app.mount("/static", StaticFiles(directory="../Frontend/static"), name="static")

templates = Jinja2Templates(directory="../Frontend/templates")


# Middleware to manage session ID
@app.middleware("http")
async def add_session_id(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response = await call_next(request)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response
    response = await call_next(request)
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context=context)


@app.post("/loadData", response_class=HTMLResponse)
async def load_data(
    file_input: UploadFile, request: Request, background_tasks: BackgroundTasks
):
    session_id = request.cookies.get("session_id")
    data_store = load_data_store(session_id)
    if data_store:
        await asyncio.to_thread(delete_data_store, session_id)  # Function to delete the DataStore

    data_store = DataStore()
        
    try:
        data = await file_input.read()
        decoded_data = data.decode("utf-8")
        json_data = json.loads(decoded_data)
        watched_items = [models.WatchedItem.model_validate(item) for item in json_data]
        (
            data_store.filtered_json_data,
            data_store.removed_video_count,
        ) = data_processing.filter_data(watched_items)

        data_store.state_queue.clear()

        data_store.update_state(DataStoreState.REQUESTING_DATA)

        # Save updated DataStore to Redis
        await asyncio.to_thread(
            save_data_store, session_id, data_store
        )  # Run in thread

        # Add background task to process the remaining steps
        background_tasks.add_task(process_data_pipeline, session_id)
        return templates.TemplateResponse(
            "partials/steps/verify_and_extract.html", context={"request": request}
        )
    except (OSError, json.JSONDecodeError, ValidationError) as e:
        error_message = str(e)
        data_store.error_message = error_message  # Update error state in DataStore
        await asyncio.to_thread(
            save_data_store, session_id, data_store
        )  # Run in thread
        print("Error:", error_message)
        return templates.TemplateResponse(
            "partials/steps/verify_and_extract.html",
            context={"request": request, "error": error_message},
        )


async def process_data_pipeline(session_id: str):
    """Handles requesting data from APIs and generating analytics."""
    # Step 1: Request Data from API
    await request_data(session_id)

    # Step 2: Generate Analytics
    await generate_analytics(session_id)


async def request_data(session_id):
    data_store = load_data_store(session_id)
    try:
        # Convert filtered_json_data from JSON to YouTubeVideo objects
        youtube_videos = data_processing.json_to_youtube_videos(
            data_store.filtered_json_data
        )

        # Request data for YouTube videos
        vid_info_df = await api_handling.request_data(youtube_videos)

        # Merge video data with additional info
        data_store.complete_data = data_processing.merge_data(
            vid_info_df=vid_info_df, videos=youtube_videos
        )

        data_store.update_state(DataStoreState.GENERATING_ANALYTICS)

        # Save updated DataStore to Redis
        await asyncio.to_thread(
            save_data_store, session_id, data_store
        )  # Run in thread

    except json.JSONDecodeError as e:
        # Handle JSON decode errors
        print(f"JSON decoding error: {e}")
        data_store.error_message = "JSON decoding error occurred."
        await asyncio.to_thread(
            save_data_store, session_id, data_store
        )  # Run in thread

    except api_handling.RequestError as e:
        # Handle errors specific to the API request
        print(f"API request error: {e}")
        data_store.error_message = "API request error occurred."
        await asyncio.to_thread(
            save_data_store, session_id, data_store
        )  # Run in thread

    except Exception as e:
        # Handle any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        data_store.error_message = "An unexpected error occurred."
        await asyncio.to_thread(
            save_data_store, session_id, data_store
        )  # Run in thread


async def generate_analytics(session_id: str):
    """Generates analytics and updates Redis."""
    data_store = load_data_store(session_id)

    # Example analytics code
    data_store.page_num = 1
    data_store.unique_vids = (
        data_store.complete_data[["title", "channelTitle"]]
        .drop_duplicates()
        .to_records(index=False)
        .tolist()
    )
    data_store.num_of_pages = (
        len(data_store.unique_vids) + data_store.max_rows - 1
    ) // data_store.max_rows

    data_store.update_state(DataStoreState.COMPLETE)  # Update progress in Redis

    # Save updated DataStore with analytics to Redis
    await asyncio.to_thread(save_data_store, session_id, data_store)  # Run in thread


async def generate_analytics_context(session_id: str) -> dict:
    """Generates the context for the analytics template."""
    data_store = load_data_store(session_id)

    # Prepare analytics data
    context = {
        "start_index": 0,
        "num_of_pages": data_store.num_of_pages,
        "unique_vids": data_store.unique_vids[: data_store.max_rows],
        "total_vids": data_store.complete_data.shape[0],
        "total_unique_channels": analytics.unique_channels(data_store.complete_data),
    }

    updated_context = visualization.prepare_visualizations(
        data_store.complete_data, context
    )
    final_context = analytics.calculate_total_watch_time(
        data_store.complete_data["duration"].tolist(), updated_context
    )

    return final_context


@app.post("/status", response_class=HTMLResponse)
async def status(request: Request):
    session_id = request.cookies.get("session_id")
    data_store = load_data_store(session_id)

    current_state = data_store.current_state()

    if data_store.error_message == "":
        if current_state == DataStoreState.COMPLETE:
            data_store.process_next_state()
            await asyncio.to_thread(save_data_store, session_id, data_store)  # Run in thread
            context = await generate_analytics_context(session_id)
            context["request"] = request
            return templates.TemplateResponse("partials/analytics.html", context)
        elif current_state == DataStoreState.GENERATING_ANALYTICS:
            data_store.process_next_state()
            await asyncio.to_thread(save_data_store, session_id, data_store)  # Run in thread
            return templates.TemplateResponse(
                "partials/steps/request_data.html", context={"request": request}
            )
        else:
            if len(data_store.state_queue) > 1:
                data_store.process_next_state()
                await asyncio.to_thread(save_data_store, session_id, data_store)  # Run in thread
            return templates.TemplateResponse(
                "partials/steps/verify_and_extract.html", context={"request": request}
            )

    return templates.TemplateResponse(
        "partials/steps/request_data.html",
        context={"request": request, "error": data_store.error_message},
    )


@app.get("/instructions", response_class=HTMLResponse)
async def instructions(request: Request):
    return templates.TemplateResponse("instructions.html", {"request": request})


@app.post("/nextTablePage")
async def next_table_page(request: Request):
    context = {"request": request}
    session_id = request.cookies.get("session_id")
    data_store = load_data_store(session_id)

    # Check if data_store is None
    if not data_store:
        return templates.TemplateResponse(
            "partials/error.html", context={"request": request, "error": "No session found. Please reload data."}
        )

    if data_store.page_num < data_store.num_of_pages:
        data_store.page_num += 1

    # Save updated DataStore to Redis
    await asyncio.to_thread(save_data_store, session_id, data_store)  # Run in thread

    max_index = min(
        len(data_store.unique_vids) - 1, data_store.max_rows * data_store.page_num
    )
    end_index = max_index if max_index >= 0 else 0

    # Calculate the start index for the next page
    start_index = end_index - data_store.max_rows if end_index > 0 else 0

    context["start_index"] = start_index
    context["unique_vids"] = data_store.unique_vids[start_index:end_index]

    return templates.TemplateResponse("partials/vids_table.html", context=context)


@app.post("/prevTablePage")
async def prev_table_page(request: Request):
    context = {"request": request}
    session_id = request.cookies.get("session_id")
    data_store = load_data_store(session_id) 

    # Check if data_store is None
    if not data_store:
        return templates.TemplateResponse(
            "partials/error.html", context={"request": request, "error": "No session found. Please reload data."}
        )

    if data_store.page_num > 1:
        data_store.page_num -= 1
        start_index = data_store.max_rows * (data_store.page_num - 1)
    else:
        start_index = 0

    # Save updated DataStore to Redis
    await asyncio.to_thread(save_data_store, session_id, data_store)  # Run in thread

    # Calculate the end index for the previous page
    end_index = start_index + data_store.max_rows

    context["start_index"] = start_index
    context["unique_vids"] = data_store.unique_vids[start_index:end_index]

    return templates.TemplateResponse("partials/vids_table.html", context=context)
