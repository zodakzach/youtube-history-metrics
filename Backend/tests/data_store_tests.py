import unittest
from datetime import datetime
import pandas as pd
from src.data_store import DataStore
import src.models as models
from copy import deepcopy


class TestDataStoreSerialization(unittest.TestCase):
    def setUp(self):
        # Create a sample DataFrame for complete_data with the specified columns and example data
        self.sample_data = pd.DataFrame(
            {
                "id": ["sTzF57GE4-k"],
                "watch_date": [pd.to_datetime("2023-10-01 23:28:10.856000")],
                "title": ["HTMX: 3 IRL Use Cases"],
                "channelTitle": ["ThePrimeTime"],
                "duration": ["PT18M33S"],
            }
        )

        # Create an instance of DataStore and set its attributes
        self.data_store = DataStore()
        # Create YouTubeVideo objects and serialize them to JSON strings
        video1 = models.YouTubeVideo(
            watchDate=datetime.fromisoformat("2023-10-01T23:28:10.856000"),
            id="sTzF57GE4-k",
        )
        self.data_store.filtered_json_data = [video1.to_json()]
        self.data_store.complete_data = self.sample_data
        self.data_store.removed_video_count = 0
        self.data_store.page_num = 1
        self.data_store.unique_vids = ["sTzF57GE4-k"]
        self.data_store.num_of_pages = 1
        self.data_store.max_rows = 500

    def test_serialization_deserialization(self):
        # Serialize the DataStore object to a dictionary
        data_dict = deepcopy(self.data_store)

        data_dict = data_dict.to_dict()

        # Deserialize the dictionary back to a DataStore object
        deserialized_data_store = DataStore.from_dict(data_dict)

        # Deserialize filtered_json_data back to YouTubeVideo objects for comparison
        original_videos = [
            models.YouTubeVideo.from_json(json_str)
            for json_str in self.data_store.filtered_json_data
        ]
        deserialized_videos = [
            models.YouTubeVideo.from_json(json_str)
            for json_str in deserialized_data_store.filtered_json_data
        ]

        pd.testing.assert_frame_equal(
            self.data_store.complete_data, deserialized_data_store.complete_data
        )
        self.assertEqual(original_videos, deserialized_videos)
        self.assertEqual(
            self.data_store.removed_video_count,
            deserialized_data_store.removed_video_count,
        )
        self.assertEqual(self.data_store.page_num, deserialized_data_store.page_num)
        self.assertEqual(
            self.data_store.unique_vids, deserialized_data_store.unique_vids
        )
        self.assertEqual(
            self.data_store.num_of_pages, deserialized_data_store.num_of_pages
        )
        self.assertEqual(self.data_store.max_rows, deserialized_data_store.max_rows)


if __name__ == "__main__":
    unittest.main()
