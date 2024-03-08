import unittest
from src import analytics
import pandas as pd


class AnalyticsModuleTest(unittest.TestCase):
    def test_get_top_channels(self):
        # Test case for get_top_channels function
        data = {
            "channelTitle": [
                "Channel A",
                "Channel A",
                "Channel B",
                "Channel B",
                "Channel B",
                "Channel C",
            ]
        }
        youtube_history_df = pd.DataFrame(data)
        top_channels = analytics.get_top_channels(youtube_history_df, "channelTitle", 2)
        self.assertEqual(top_channels, [("Channel B", 3), ("Channel A", 2)])

    def test_get_top_videos(self):
        # Test case for get_top_videos function
        data = {
            "title": ["Video A", "Video A", "Video B", "Video B", "Video B", "Video C"]
        }
        youtube_history_df = pd.DataFrame(data)
        top_videos = analytics.get_top_videos(youtube_history_df, "title", 2)
        self.assertEqual(top_videos, [("Video B", 3), ("Video A", 2)])

    def test_calculate_total_watch_time(self):
        # Test case for calculate_total_watch_time function
        vid_duration_list = ["PT1H30M15S", "PT45M20S", "PT15M"]
        context = {}
        analytics.calculate_total_watch_time(vid_duration_list, context)
        self.assertEqual(context["total_days"], 0)
        self.assertEqual(context["total_hours"], 2)
        self.assertEqual(context["total_mins"], 30)

    def test_unique_channels(self):
        # Test case for unique_channels function
        data = {"channelTitle": ["Channel A", "Channel B", "Channel A", "Channel C"]}
        youtube_df = pd.DataFrame(data)
        num_unique_channels = analytics.unique_channels(youtube_df)
        self.assertEqual(num_unique_channels, 3)


if __name__ == "__main__":
    unittest.main()
