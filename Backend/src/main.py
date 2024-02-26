import json
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from httpx import HTTPError
from pydantic import ValidationError
import pandas as pd
from . import models
from . import data_processing
from . import api_handling
from . import analytics
from . import visualization

app = FastAPI()

# Mount the "static" directory at the path "/static"
app.mount("/static", StaticFiles(directory="../Frontend/static"), name="static")

templates = Jinja2Templates(directory="../Frontend/templates")


class DataStore:
    def __init__(self):
        self.filtered_json_data = []
        self.complete_data = pd.DataFrame()
        self.removed_video_count = 0
        self.page_num = 1
        self.unique_vids = []
        self.num_of_pages = 0
        self.max_rows = 500


data_store = DataStore()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context=context)


@app.post("/uploadFile", response_class=HTMLResponse)
async def upload_file(file_input: UploadFile, request: Request):
    try:
        data = await file_input.read()
        decoded_data = data.decode("utf-8")
        json_data = json.loads(decoded_data)
        watched_items = [models.WatchedItem.model_validate(item) for item in json_data]
        (
            data_store.filtered_json_data,
            data_store.removed_videos_count,
        ) = data_processing.filter_data(watched_items)
        return templates.TemplateResponse(
            "partials/steps/verify_and_extract.html", context={"request": request}
        )
    except (OSError, json.JSONDecodeError, ValidationError) as e:
        error_message = str(e)
        print("Error:", error_message)
        return templates.TemplateResponse(
            "partials/steps/verify_and_extract.html",
            context={"request": request, "error": error_message},
        )


@app.get("/instructions", response_class=HTMLResponse)
async def instructions(request: Request):
    return templates.TemplateResponse("instructions.html", {"request": request})


@app.get("/requestData", response_class=HTMLResponse)
async def request_data(request: Request):
    try:
        vid_info_df = await api_handling.request_data(data_store.filtered_json_data)
        data_store.complete_data = data_processing.merge_data(
            vid_info_df=vid_info_df, videos=data_store.filtered_json_data
        )
        context = {"request": request}
    except HTTPError as e:
        error_message = f"Error requesting YouTube data: {e}"
        print(error_message)
        context = {"request": request, "error": error_message}
    except Exception as e:
        error_message = f"Unexpected error: {e}"
        print(error_message)
        context = {"request": request, "error": error_message}

    return templates.TemplateResponse(
        "partials/steps/request_data.html", context=context
    )


@app.get("/loadAnalytics")
async def load_analytics(request: Request):
    context = {}
    context["request"] = request

    data_store.page_num = 1

    # Get all unique videos
    data_store.unique_vids = (
        data_store.complete_data[["title", "channelTitle"]]
        .drop_duplicates()
        .to_records(index=False)
        .tolist()
    )

    # Max rows in table and total pages needed to display all unique videos in table
    data_store.num_of_pages = (
        len(data_store.unique_vids) + data_store.max_rows - 1
    ) // data_store.max_rows
    context["start_index"] = 0
    context["num_of_pages"] = data_store.num_of_pages
    context["unique_vids"] = data_store.unique_vids[: data_store.max_rows]

    # Analytics for stat values
    context["total_vids"] = data_store.complete_data.shape[0]
    context["total_unique_channels"] = analytics.unique_channels(
        data_store.complete_data
    )

    # Add charts to context
    updated_context = visualization.prepare_visualizations(
        data_store.complete_data, context
    )

    # Calculates the total number of days, hours, and minutes watched
    final_context = analytics.calculate_total_watch_time(
        data_store.complete_data["duration"].tolist(), updated_context
    )

    return templates.TemplateResponse("partials/analytics.html", context=final_context)


@app.get("/nextTablePage")
async def next_table_page(request: Request):
    context = {"request": request}
    if data_store.page_num < data_store.num_of_pages:
        data_store.page_num += 1

    max_index = min(
        len(data_store.unique_vids) - 1, data_store.max_rows * data_store.page_num
    )
    end_index = max_index if max_index >= 0 else 0

    # Calculate the start index for the next page
    start_index = end_index - data_store.max_rows if end_index > 0 else 0

    context["start_index"] = start_index
    context["unique_vids"] = data_store.unique_vids[start_index:end_index]

    return templates.TemplateResponse("partials/vids_table.html", context=context)


@app.get("/prevTablePage")
async def prev_table_page(request: Request):
    context = {"request": request}
    if data_store.page_num > 1:
        data_store.page_num -= 1
        start_index = data_store.max_rows * (data_store.page_num - 1)
    else:
        start_index = 0

    # Calculate the end index for the previous page
    end_index = start_index + data_store.max_rows

    context["start_index"] = start_index
    context["unique_vids"] = data_store.unique_vids[start_index:end_index]

    return templates.TemplateResponse("partials/vids_table.html", context=context)
