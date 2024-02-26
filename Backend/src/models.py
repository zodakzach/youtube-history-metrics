from pydantic import BaseModel, validator
from typing import List, Optional


class Detail(BaseModel):
    name: str


class WatchedItem(BaseModel):
    header: str
    title: str
    titleUrl: Optional[str] = None
    description: Optional[str] = None
    time: str
    products: List[str]
    details: Optional[List[Detail]] = None
    activityControls: Optional[List[str]] = None

    @validator("products")
    def validate_products(cls, v):
        if "YouTube" not in v:
            raise ValueError('products must contain "YouTube"')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "header": "YouTube",
                "title": "Watched https://www.youtube.com/watch?v=t8hcJtyNRAk",
                "titleUrl": "https://www.youtube.com/watch?v=t8hcJtyNRAk",
                "description": "Watched at 9:52 PM",
                "time": "2024-01-30T02:52:57.611Z",
                "products": ["YouTube"],
                "details": [{"name": "From Google Ads"}],
                "activityControls": [
                    "Web & App Activity",
                    "YouTube watch history",
                    "YouTube search history",
                ],
            }
        }


class YouTubeVideo(BaseModel):
    watchDate: str
    id: str

    @classmethod
    def model_validate(cls, v):
        v["watchDate"] = v["watchDate"].isoformat()
        return super().model_validate(v)
