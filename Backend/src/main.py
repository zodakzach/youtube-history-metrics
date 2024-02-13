import json
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from . import models
from . import data_processing
from . import api_handling

app=FastAPI()

# Mount the "static" directory at the path "/static"
app.mount("/static", StaticFiles(directory="../Frontend/static"), name="static")

templates=Jinja2Templates(directory="../Frontend/templates")

class DataStore:
    def __init__(self):
        self.filtered_json_data = []
        self.complete_data = []
        self.removed_video_count = 0

data_store = DataStore()

@app.get("/", response_class=HTMLResponse)
async def index(request:Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context=context)

@app.post("/uploadFile", response_class=HTMLResponse)
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

        data_store.filtered_json_data, data_store.removed_videos_count = data_processing.filter_data(watched_items)
    except Exception as e:
        print(f"Error parsing JSON data: {e}")
        context['error'] = f"Error parsing JSON data: {e}"

    context["request"] = request
    return templates.TemplateResponse("partials/steps/verify_and_extract.html", context=context)


@app.get("/instructions", response_class=HTMLResponse)
async def instructions(request: Request):
    return templates.TemplateResponse("instructions.html", {"request":request})


@app.get("/requestData", response_class=HTMLResponse)
async def requestData(request: Request):
    context = {}

    try:
        vid_info_df = await api_handling.request_data(data_store.filtered_json_data)
    except Exception as e:
        print(f"Error reqesting youtube data: {e}")
        context['error'] = f"Error reqesting youtube data: {e}"
        return templates.TemplateResponse("partials/steps/request_data.html", context=context)

    data_store.complete_data = data_processing.merge_data(vid_info_df=vid_info_df, videos=data_store.filtered_json_data)

    context["request"] = request
    print(len(data_store.complete_data))
    return templates.TemplateResponse("partials/steps/request_data.html", context=context)

@app.get("/loadAnalytics")
async def loadAnalytics(request: Request):
    context = {}
    context["request"] = request
    return templates.TemplateResponse("partials/analytics.html", context=context)



    