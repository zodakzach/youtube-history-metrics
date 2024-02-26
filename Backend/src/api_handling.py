"""
API Handling Module

This module provides functions for handling YouTube API requests.

Author: Zachary Cervenka
"""

import asyncio
import httpx
import pandas as pd
import os
from dotenv import load_dotenv


async def fetch_video_data(youtube_api_key, video_id_string):
    """
    Fetch video data from YouTube API.

    :param youtube_api_key: YouTube API key.
    :param video_id_string: Comma-separated string of video IDs.
    :return: List of dictionaries containing video information.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id={video_id_string}&key={youtube_api_key}"
        )
        response.raise_for_status()
        data = response.json()["items"]

        extracted_data = [
            {
                "id": item.get("id", ""),
                "title": item.get("snippet", {}).get("title", ""),
                "channelTitle": item.get("snippet", {}).get("channelTitle", ""),
                "duration": item.get("contentDetails", {}).get("duration", ""),
            }
            for item in data
        ]

        return extracted_data


async def process_vid_info_df_chunk(youtube_api, chunk):
    """
    Process a chunk of video information.

    :param youtube_api: YouTube API key.
    :param chunk: List of video IDs.
    :return: List of dictionaries containing video information.
    """
    video_id_string = ",".join(chunk)
    return await fetch_video_data(youtube_api, video_id_string)


async def process_vid_info_df(vid_id_chunks, youtube_api):
    """
    Process video information DataFrame.

    :param vid_id_chunks: List of lists, each containing video IDs.
    :param youtube_api: YouTube API key.
    :return: DataFrame containing video information.
    """
    tasks = [process_vid_info_df_chunk(youtube_api, chunk) for chunk in vid_id_chunks]
    video_data_chunks = await asyncio.gather(*tasks)

    # Flatten the list of lists
    video_data = [item for sublist in video_data_chunks for item in sublist]

    vid_info_df = pd.DataFrame(video_data)

    return vid_info_df


def get_vid_id_chunks(chunk_size, vid_ids):
    """Function to split a list of unique video IDs into chunks of size chunk"""
    unique_vid_ids = list(set(vid_ids))
    unique_vid_ids = list(map(str, unique_vid_ids))
    return [
        unique_vid_ids[i : i + chunk_size]
        for i in range(0, len(unique_vid_ids), chunk_size)
    ]


async def request_data(videos):
    # Load environment variables from .env file
    load_dotenv()

    # Now you can access your environment variables using os.getenv()
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")

    vid_ids = [video.id for video in videos]

    vid_info_df = await process_vid_info_df(
        get_vid_id_chunks(50, vid_ids),
        youtube_api_key,
    )

    return vid_info_df
