import unittest
from datetime import datetime
from src import data_processing
import pandas as pd
from src import models


class data_processing_test(unittest.TestCase):
    def test_extract_video_id(self):
        # Test case for valid URL
        url = "https://www.youtube.com/watch?v=abc123"
        self.assertEqual(data_processing.extract_video_id(url), "abc123")

        # Test case for invalid URL
        invalid_url = "https://www.youtube.com/watch"
        self.assertIsNone(data_processing.extract_video_id(invalid_url))

    def test_parse_timestamp(self):
        # Test case for valid timestamp string
        timestamp_string = "2023-01-01T12:00:00Z"
        expected_datetime = datetime(2023, 1, 1, 12, 0, 0)
        self.assertEqual(
            data_processing.parse_timestamp(timestamp_string), expected_datetime
        )

        # Test case for invalid timestamp string
        invalid_timestamp_string = "invalid_timestamp"
        with self.assertRaises(ValueError):
            data_processing.parse_timestamp(invalid_timestamp_string)

    def test_filter_data(self):
        # Mock watched_items
        watched_items = [
            models.WatchedItem(
                header="YouTube",
                title="Watched https://www.youtube.com/watch?v=abc123",
                time="2023-01-01T12:00:00Z",
                products=["YouTube"],
                titleUrl="https://www.youtube.com/watch?v=abc123",
            ),
            models.WatchedItem(
                header="YouTube",
                title="Watched https://www.youtube.com/watch?v=def456",
                time="2023-01-02T12:00:00Z",
                products=["YouTube"],
                titleUrl="https://www.youtube.com/watch?v=def456",
            ),
            models.WatchedItem(
                header="YouTube",
                title="Watched https://www.youtube.com/watch?v=ghi789",
                time="2023-01-02T12:00:00Z",
                products=["YouTube"],
                titleUrl=None,
            ),
            models.WatchedItem(
                header="YouTube",
                title="Watched https://www.youtube.com/watch?v=jkl012",
                time="2023-01-03T12:00:00Z",
                products=["YouTube"],
                titleUrl=None,
            ),
            models.WatchedItem(
                header="YouTube",
                title="Watched a video that has been removed",
                time="2023-01-04T12:00:00Z",
                products=["YouTube"],
                titleUrl=None,
            ),
        ]

        # Mock expected output
        expected_filtered_data = [
            models.YouTubeVideo(
                watchDate=str(data_processing.parse_timestamp("2023-01-01T12:00:00Z")),
                id="abc123",
            ),
            models.YouTubeVideo(
                watchDate=str(data_processing.parse_timestamp("2023-01-02T12:00:00Z")),
                id="def456",
            ),
        ]
        expected_removed_videos_count = 1

        # Test filter_data function
        filtered_data, removed_videos_count = data_processing.filter_data(watched_items)
        self.assertEqual(filtered_data, expected_filtered_data)
        self.assertEqual(removed_videos_count, expected_removed_videos_count)

    def test_merge_data(self):
        # Mock videos and vid_info_df
        videos = [
            models.YouTubeVideo(
                id="abc123", watchDate=datetime(2023, 1, 1, 12, 0, 0).isoformat()
            ),
            models.YouTubeVideo(
                id="def456", watchDate=datetime(2023, 1, 2, 12, 0, 0).isoformat()
            ),
        ]
        vid_info_df = pd.DataFrame()
        # Assign columns to the DataFrame
        vid_info_df["id"] = ["abc123", "def456"]
        vid_info_df["title"] = ["test1", "test2"]
        vid_info_df["channelTitle"] = ["test1", "test2"]
        vid_info_df["duration"] = ["test1", "test2"]

        # Mock expected output
        expected_merged_df = pd.DataFrame(
            {
                "id": ["abc123", "def456"],
                "watch_date": [
                    datetime(2023, 1, 1, 12, 0, 0).isoformat(),
                    datetime(2023, 1, 2, 12, 0, 0).isoformat(),
                ],
                "title": ["test1", "test2"],
                "channelTitle": ["test1", "test2"],
                "duration": ["test1", "test2"],
            }
        )

        merged_df = data_processing.merge_data(videos, vid_info_df)
        self.assertTrue(expected_merged_df.equals(merged_df))


if __name__ == "__main__":
    unittest.main()
