import json
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from . import models
from . import data_processing
from datetime import datetime


app=FastAPI()

# Mount the "static" directory at the path "/static"
app.mount("/static", StaticFiles(directory="../Frontend/static"), name="static")

templates=Jinja2Templates(directory="../Frontend/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request:Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context=context)

@app.post("/uploadFile")
async def upload_file(file_input: UploadFile, request: Request):
    context = {}
    data = await file_input.read()
    try:
        # Decode bytes to string assuming UTF-8 encoding
        decoded_data = data.decode("utf-8")
        # Parse JSON data
        json_data = json.loads(decoded_data)
        # Load JSON data into Python objects
        watched_items = []
        for item in json_data:
            try:
                # Attempt to validate and create a WatchedItem object
                watched_item = models.WatchedItem.validate(item)
                if watched_item:
                    watched_items.append(watched_item)
                else:
                    print("Watched item dropped due to missing fields:", item)
            except ValidationError as e:
                context['error'] = f"Error parsing JSON data: {e}"
                # Handle validation errors
                print("Validation error:", e)

        filtered_data = []
        removed_videos_count = 0

        for item in watched_items:
            if item.time is not None and item.titleUrl is not None:
                # Process the data only if both 'time' and 'titleUrl' are not None
                watch_date = data_processing.parse_timestamp(item.time)
                video_id = data_processing.extract_video_id(item.titleUrl)

                try:
                    # Attempt to convert video_id to string
                    video_id_str = str(video_id)
                except Exception as e:
                    # Skip processing this item if conversion fails
                    print(f"Error converting video_id to string: {e}")
                    continue

                # Check if the video is removed
                if item.title == "Watched a video that has been removed":
                    removed_videos_count += 1

                youtube_video = models.YouTubeVideo(
                    titleUrl=item.titleUrl,
                    watchDate=watch_date,
                    id=video_id_str
                )
                filtered_data.append(youtube_video)

        context['youtube_videos'] = filtered_data
        context['removed_videos_count'] = removed_videos_count
    except Exception as e:
        print(f"Error parsing JSON data: {e}")
        context['error'] = f"Error parsing JSON data: {e}"

    context["request"] = request
    return templates.TemplateResponse("partials/steps/verify_and_extract.html", context=context)


@app.get("/instructions", response_class=HTMLResponse)
async def instructions(request: Request):
    return templates.TemplateResponse("instructions.html", {"request":request})
