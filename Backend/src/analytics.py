"""
Analytics Module

This module provides functions for analyzing YouTube video data.

Author: Zachary Cervenka
"""

from collections import Counter
from datetime import timedelta
import re


def get_top_channels(youtube_history_df, column_name="channelTitle", top_n=5):
    """Function to get the top channels from a DataFrame with a 'channelTitle' column."""
    if column_name not in youtube_history_df.columns:
        raise ValueError(f"Column '{column_name}' not found in the DataFrame.")
    channels_counter = Counter(
        channel for channel in youtube_history_df[column_name] if channel != ""
    )
    top_channels = channels_counter.most_common(top_n)
    return top_channels


def get_top_videos(youtube_history_df, column_name="title", top_n=5):
    """Function to get the top videos from a DataFrame with a specified column."""
    if column_name not in youtube_history_df.columns:
        raise ValueError(f"Column '{column_name}' not found in the DataFrame.")
    videos_counter = Counter(
        title for title in youtube_history_df[column_name] if title != ""
    )
    top_videos = videos_counter.most_common(top_n)
    return top_videos


def calculate_total_watch_time(vid_duration_list, context):
    """Function to calculate the total watch time from a list of video durations"""
    hours_pattern = re.compile(r"(\d+)H")
    minutes_pattern = re.compile(r"(\d+)M")
    seconds_pattern = re.compile(r"(\d+)S")
    total_hours = 0
    total_mins = 0
    total_secs = 0
    for vid in vid_duration_list:
        hours = hours_pattern.search(vid)
        mins = minutes_pattern.search(vid)
        secs = seconds_pattern.search(vid)
        total_hours += int(hours.group(1)) if hours else 0
        total_mins += int(mins.group(1)) if mins else 0
        total_secs += int(secs.group(1)) if secs else 0

    total_time = timedelta(hours=total_hours, minutes=total_mins, seconds=total_secs)
    context["total_days"] = total_time.days
    context["total_hours"] = total_time.seconds // 3600
    context["total_mins"] = (total_time.seconds % 3600) // 60

    return context


def unique_channels(youtube_df):
    # Getting all unique channelTitles from the filtered DataFrame
    unique_channel_titles = youtube_df["channelTitle"].unique()

    # Getting the length of the unique channelTitles array
    num_unique_channel_titles = len(unique_channel_titles)

    return num_unique_channel_titles