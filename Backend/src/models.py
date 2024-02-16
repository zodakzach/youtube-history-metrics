from pydantic import BaseModel, ValidationError
from typing import List, Optional

class Detail(BaseModel):
    name: str

class WatchedItem(BaseModel):
    header: str
    title: str
    titleUrl: Optional[str] = None
    description: Optional[str] = None
    time: str
    products:Optional[List[str]] = None
    details: Optional[List[Detail]] = None
    activityControls: Optional[List[str]] = None

    @classmethod
    def validate(cls, value):
        try:
            # Validate the input value against the model
            return cls(**value)
        except ValidationError as e:
            raise

    class Config:
        schema_extra = {
            "example": {
                "header": "YouTube",
                "title": "Watched https://www.youtube.com/watch?v=t8hcJtyNRAk",
                "titleUrl": "https://www.youtube.com/watch?v=t8hcJtyNRAk",
                "description": "Watched at 9:52 PM",
                "time": "2024-01-30T02:52:57.611Z",
                "products": ["YouTube"],
                "details": [{"name": "From Google Ads"}],
                "activityControls": ["Web & App Activity", "YouTube watch history", "YouTube search history"]
            }
        }

class YouTubeVideo(BaseModel):
    watchDate: str 
    id: str
    pk: int

    @classmethod
    def model_validate(cls, v):
        v['watchDate'] = v['watchDate'].isoformat()
        return super().model_validate(v)
    
    def to_dict(self):
        return {
            "watchDate": self.watchDate,
            "id": self.id,
            "pk": self.pk
        }