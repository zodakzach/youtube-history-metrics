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
    formats_to_try = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]
    
    for format_str in formats_to_try:
        try:
            return datetime.strptime(timestamp_string, format_str)
        except ValueError:
            pass
    
    # If none of the formats match, raise an exception or handle it accordingly
    raise ValueError("Timestamp does not match any expected format")

def filter_data(watched_items):
    filtered_data = []
    removed_videos_count = 0
    vid_num = 0

    for item in watched_items:
        # Check if the video is removed
        if item.title == "Watched a video that has been removed":
            removed_videos_count += 1

        if item.time is not None and item.titleUrl is not None and item.details is None:
            # Process the data only if both 'time' and 'titleUrl' are not None
            watch_date = parse_timestamp(str(item.time))
            video_id = extract_video_id(item.titleUrl)

            try:
                # Attempt to convert video_id to string
                video_id_str = str(video_id)
            except Exception as e:
                # Skip processing this item if conversion fails
                print(f"Error converting video_id to string: {e}")
                continue

            youtube_video = models.YouTubeVideo(
                watchDate=str(watch_date),
                id=video_id_str,
                pk=vid_num
            )
            filtered_data.append(youtube_video)
            vid_num += 1

    return filtered_data, removed_videos_count

def merge_data(videos, vid_info_df):
    video_data = [{"id": video.id, "watch_date": video.watchDate} for video in videos]
    df = pd.DataFrame(video_data)

    merged_df = pd.merge(df, vid_info_df, on="id", how="left")
    merged_df = merged_df.loc[merged_df["title"].notna() & merged_df["channelTitle"].notna() & merged_df["duration"].notna()]
    youtube_df = merged_df.reset_index(drop=True)

    return youtube_df


