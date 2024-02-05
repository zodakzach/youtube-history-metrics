from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app=FastAPI()

# Mount the "static" directory at the path "/static"
app.mount("/static", StaticFiles(directory="../Frontend/static"), name="static")

templates=Jinja2Templates(directory="../Frontend/templates")

@app.get("/")
async def index(request:Request):
    return templates.TemplateResponse("base.html",{"request":request})