import re
from typing import Optional 

def extract_video_id(titleUrl: str) -> Optional[str]:
    # Extract video ID from URL
    id_match = re.search(r"v=([^\&]+)", titleUrl)
    if id_match:
        return id_match.group(1)
    return None

from datetime import datetime

def parse_timestamp(timestamp_string):
    formats_to_try = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]
    
    for format_str in formats_to_try:
        try:
            return datetime.strptime(timestamp_string, format_str)
        except ValueError:
            pass
    
    # If none of the formats match, raise an exception or handle it accordingly
    raise ValueError("Timestamp does not match any expected format")