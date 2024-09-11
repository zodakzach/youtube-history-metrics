from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
import json


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

    @field_validator("products")
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
    watchDate: datetime
    id: str

    def model_dump(self, **kwargs):
        # Convert watchDate to ISO format during serialization
        data = super().model_dump(**kwargs)
        data["watchDate"] = data["watchDate"].isoformat()
        return data

    def to_json(self):
        # Convert to JSON string
        return json.dumps(self.model_dump())

    @classmethod
    def from_json(cls, json_str: str):
        # Convert JSON string back to YouTubeVideo object
        data = json.loads(json_str)
        data["watchDate"] = datetime.fromisoformat(data["watchDate"])
        return cls(**data)
