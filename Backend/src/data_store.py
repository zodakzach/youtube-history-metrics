from io import StringIO
from typing import List
import pandas as pd
from enum import Enum
from collections import deque


class DataStoreState(Enum):
    NOT_STARTED = "not_started"
    REQUESTING_DATA = "requesting_data"
    GENERATING_ANALYTICS = "generating_analytics"
    COMPLETE = "complete"
    ERROR = "error"


class DataStore:
    def __init__(self):
        self.filtered_json_data: List[str] = []  # List of JSON strings
        self.complete_data = pd.DataFrame()
        self.removed_video_count = 0
        self.page_num = 1
        self.unique_vids = []
        self.num_of_pages = 0
        self.max_rows = 500
        self.state_queue = deque()  # Initialize as empty
        self.error_message = ""

    def to_dict(self):
        """Serialize the DataStore object to a dictionary."""
        if "watch_date" in self.complete_data.columns:
            self.complete_data["watch_date"] = self.complete_data[
                "watch_date"
            ].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {
            "filtered_json_data": self.filtered_json_data,
            "complete_data": self.complete_data.to_json(
                orient="split"
            ),  # Convert DataFrame to JSON string
            "removed_video_count": self.removed_video_count,
            "page_num": self.page_num,
            "unique_vids": self.unique_vids,
            "num_of_pages": self.num_of_pages,
            "max_rows": self.max_rows,
            "state_queue": [
                state.value for state in self.state_queue
            ],  # Serialize state queue
            "error_message": self.error_message,  # Include error_message in the dictionary
        }

    def update_state(self, new_state: DataStoreState):
        """Update the state and add it to the state queue."""
        self.state_queue.append(new_state)

    def current_state(self) -> DataStoreState:
        """Get the current state without removing it from the queue."""
        return self.state_queue[0] if self.state_queue else DataStoreState.NOT_STARTED

    def process_next_state(self) -> DataStoreState:
        """Remove the processed state from the queue and return it."""
        if self.state_queue:
            return self.state_queue.popleft()

    @classmethod
    def from_dict(cls, data):
        """Deserialize a dictionary to a DataStore object."""
        complete_data_json = data.get("complete_data", "{}")

        # Fix FutureWarning: Use StringIO to wrap literal JSON string
        complete_data = pd.read_json(StringIO(complete_data_json), orient="split")

        # Convert `watch_date` column from ISO format strings back to datetime and enforce dtype
        if "watch_date" in complete_data.columns:
            complete_data["watch_date"] = pd.to_datetime(
                complete_data["watch_date"], format="%Y-%m-%dT%H:%M:%S.%fZ"
            )
            complete_data["watch_date"] = complete_data["watch_date"].astype(
                "datetime64[ns]"
            )  # Enforce datetime64[ns] dtype

        instance = cls()
        instance.filtered_json_data = data.get("filtered_json_data", [])
        instance.complete_data = complete_data
        instance.removed_video_count = data.get("removed_video_count", 0)
        instance.page_num = data["page_num"]
        instance.unique_vids = data["unique_vids"]
        instance.num_of_pages = data["num_of_pages"]
        instance.max_rows = data["max_rows"]
        # Deserialize state queue
        state_queue = data.get("state_queue", [])
        instance.state_queue = deque(DataStoreState(state) for state in state_queue)

        instance.error_message = data.get(
            "error_message", ""
        )  # Set default error_message if not present
        return instance
