import re
from typing import List, Optional
from . import models
import pandas as pd
from datetime import datetime


def extract_video_id(titleUrl: str) -> Optional[str]:
    # Extract video ID from URL
    id_match = re.search(r"v=([^\&]+)", titleUrl)
    if id_match:
        return id_match.group(1)
    return None


def parse_timestamp(timestamp):
    # Define possible formats, including with and without milliseconds and `Z` suffix
    formats_to_try = [
        "%Y-%m-%dT%H:%M:%S.%f",  # e.g., 2023-10-12T04:17:43.284
        "%Y-%m-%dT%H:%M:%S",  # e.g., 2023-10-02T02:03:30
        "%Y-%m-%dT%H:%M:%S.%fZ",  # e.g., 2023-10-12T04:17:43.284Z
        "%Y-%m-%dT%H:%M:%SZ",  # e.g., 2023-10-02T02:03:30Z
    ]

    timestamp_string = str(timestamp)

    # Handle cases where 'Z' is present or not
    if timestamp_string.endswith("Z"):
        timestamp_string = timestamp_string[:-1]  # Remove trailing 'Z'

    for format_str in formats_to_try:
        try:
            return datetime.strptime(str(timestamp_string), format_str)
        except ValueError:
            continue

    # If none of the formats match, return None to indicate failure
    # print(timestamp)
    return None


def filter_data(watched_items):
    # Filter watched items based on conditions
    filtered_data = [
        models.YouTubeVideo(
            watchDate=parse_timestamp(item.time),
            id=str(extract_video_id(item.titleUrl)),
        ).to_json()
        for item in watched_items
        if (
            item.time is not None and item.titleUrl is not None and item.details is None
        )
    ]

    # Count removed videos
    removed_videos_count = sum(
        1
        for item in watched_items
        if item.title == "Watched a video that has been removed"
    )

    return filtered_data, removed_videos_count


def merge_data(
    videos: List[models.YouTubeVideo], vid_info_df: pd.DataFrame
) -> pd.DataFrame:
    video_data = [{"id": video.id, "watch_date": video.watchDate} for video in videos]
    df = pd.DataFrame(video_data)

    merged_df = pd.merge(df, vid_info_df, on="id", how="left")
    merged_df = merged_df.loc[
        merged_df["title"].notna()
        & merged_df["channelTitle"].notna()
        & merged_df["duration"].notna()
    ]
    youtube_df = merged_df.reset_index(drop=True)

    return youtube_df


def json_to_youtube_videos(json_list: List[str]) -> List[models.YouTubeVideo]:
    return [models.YouTubeVideo.from_json(json_str) for json_str in json_list]
