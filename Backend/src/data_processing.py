import re
from typing import Optional
from . import models
import pandas as pd
from datetime import datetime


def extract_video_id(titleUrl: str) -> Optional[str]:
    # Extract video ID from URL
    id_match = re.search(r"v=([^\&]+)", titleUrl)
    if id_match:
        return id_match.group(1)
    return None


def parse_timestamp(timestamp_string):
    formats_to_try = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ]

    for format_str in formats_to_try:
        try:
            return datetime.strptime(timestamp_string, format_str)
        except ValueError:
            pass

    # If none of the formats match, raise an exception or handle it accordingly
    raise ValueError("Timestamp does not match any expected format")


def filter_data(watched_items):
    # Filter watched items based on conditions
    filtered_data = [
        models.YouTubeVideo(
            watchDate=str(parse_timestamp(str(item.time))),
            id=str(extract_video_id(item.titleUrl)),
        )
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


def merge_data(videos, vid_info_df):
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
