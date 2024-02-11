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
    formats_to_try = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]
    
    for format_str in formats_to_try:
        try:
            return datetime.strptime(timestamp_string, format_str)
        except ValueError:
            pass
    
    # If none of the formats match, raise an exception or handle it accordingly
    raise ValueError("Timestamp does not match any expected format")


def parse_data(data):
    videos = data.split('YouTubeVideo')

    # Define potential date formats to try
    date_formats = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]
    _videos = []
    for video in videos:
        # Split the string by comma to separate the data parts
        parts = video.split(',')
        
        # Initialize variables to store watchDate and id
        watch_date = None
        video_id = None
        
        # Iterate over data parts
        for part in parts:
            # Check if the part contains 'watchDate' or 'id' and extract the value
            if 'watchDate' in part:
                watch_date_str = part.split('=')[1].strip().strip("'")
            # Attempt to convert watch_date_str to datetime object using different formats
                for date_format in date_formats:
                    try:
                        watch_date = datetime.strptime(watch_date_str, date_format)
                        break  # Exit the loop if conversion succeeds
                    except ValueError:
                        pass  # If conversion fails, try the next format
                if watch_date is None:
                    raise ValueError("Unable to parse watchDate:", watch_date_str)
            
            elif 'id' in part:
                video_id = part.split('=')[1].strip().strip("'")
        
        # Append a tuple of (id, watchDate) to the result list
        _videos.append((video_id, watch_date))
    return _videos

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
    # Create a pandas DataFrame
    df = pd.DataFrame(videos, columns=["id", "watch_date"])
    df.loc[:, 'watch_date'] = df['watch_date'].dt.strftime('%Y-%m-%dT%H:%M:%S')  # Convert datetime object to ISO format string
    merged_df = pd.merge(df, vid_info_df, on="id", how="left")
    merged_df = merged_df.loc[merged_df["title"].notna() & merged_df["channelTitle"].notna() & merged_df["duration"].notna()]
    youtube_df = merged_df.reset_index(drop=True)
    result = youtube_df.values.tolist()

    return result
