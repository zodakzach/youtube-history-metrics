import json
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from src import data_processing, models


class DataProcessingModuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        watch_history_path = Path(__file__).resolve().parent.parent / "watch-history.json"
        cls.watch_history = json.loads(watch_history_path.read_text())
        cls.watched_items = [models.WatchedItem(**item) for item in cls.watch_history]
        cls.filtered_json, cls.removed_videos_count = data_processing.filter_data(
            cls.watched_items
        )
        cls.filtered_videos = data_processing.json_to_youtube_videos(cls.filtered_json)

    def test_extract_video_id(self):
        # Test case for valid URL
        url = "https://www.youtube.com/watch?v=abc123"
        self.assertEqual(data_processing.extract_video_id(url), "abc123")

        # Test case for invalid URL
        invalid_url = "https://www.youtube.com/watch"
        self.assertIsNone(data_processing.extract_video_id(invalid_url))

    def test_parse_timestamp_handles_watch_history_format(self):
        timestamp_string = self.watch_history[0]["time"]
        expected_datetime = datetime.fromisoformat(timestamp_string.rstrip("Z"))
        self.assertEqual(
            data_processing.parse_timestamp(timestamp_string), expected_datetime
        )

    def test_parse_timestamp_returns_none_for_invalid_strings(self):
        self.assertIsNone(data_processing.parse_timestamp("not-a-real-timestamp"))

    def test_filter_data_includes_entries_without_ad_metadata(self):
        plain_entry = next(
            item
            for item in self.watched_items
            if item.details is None and item.titleUrl is not None
        )
        filtered_ids = {video.id for video in self.filtered_videos}
        expected_id = data_processing.extract_video_id(plain_entry.titleUrl)
        self.assertIn(expected_id, filtered_ids)

    def test_filter_data_excludes_entries_with_ad_metadata(self):
        entry_with_details = next(
            item
            for item in self.watched_items
            if item.details is not None and item.titleUrl is not None
        )
        filtered_ids = {video.id for video in self.filtered_videos}
        excluded_id = data_processing.extract_video_id(entry_with_details.titleUrl)
        self.assertNotIn(excluded_id, filtered_ids)

    def test_filter_data_counts_removed_videos(self):
        removed_expected = sum(
            1 for item in self.watched_items if item.title == "Watched a video that has been removed"
        )
        self.assertEqual(self.removed_videos_count, removed_expected)

    def test_json_round_trip_from_watch_history(self):
        sample_json = [video.to_json() for video in self.filtered_videos[:5]]
        reconstructed = data_processing.json_to_youtube_videos(sample_json)
        self.assertEqual(reconstructed, self.filtered_videos[:5])

    def test_merge_data_filters_missing_metadata(self):
        videos = self.filtered_videos[:3]
        vid_info_df = pd.DataFrame(
            [
                {
                    "id": videos[0].id,
                    "title": "Video 1",
                    "channelTitle": "Channel 1",
                    "duration": "PT5M",
                },
                {
                    "id": videos[1].id,
                    "title": "Video 2",
                    "channelTitle": "Channel 2",
                    "duration": "PT3M",
                },
            ]
        )

        merged_df = data_processing.merge_data(videos, vid_info_df)
        self.assertEqual(len(merged_df), 2)
        self.assertListEqual(merged_df["id"].tolist(), [videos[0].id, videos[1].id])


if __name__ == "__main__":
    unittest.main()
