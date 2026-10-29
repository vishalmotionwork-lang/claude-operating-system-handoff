#!/usr/bin/env python3
"""Fetch YouTube transcript with timestamps. Outputs JSON to stdout.

Usage:
    python3 youtube_transcript.py "https://youtube.com/watch?v=XXXXX"
    python3 youtube_transcript.py "XXXXX"  # just the video ID
"""

import json
import re
import sys

import requests
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from a YouTube URL or return as-is if already an ID."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    print(json.dumps({"error": f"Could not extract video ID from: {url_or_id}"}))
    sys.exit(1)


def fetch_title(video_id: str) -> str:
    """Fetch video title from YouTube oembed endpoint."""
    try:
        oembed_url = (
            f"https://www.youtube.com/oembed"
            f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
        )
        resp = requests.get(oembed_url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("title", "Unknown Title")
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        return "Unknown Title"


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or H:MM:SS format."""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: youtube_transcript.py <URL or video_id>"}))
        sys.exit(1)

    video_id = extract_video_id(sys.argv[1])
    title = fetch_title(video_id)

    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        transcript_entries = fetched.to_raw_data()
    except Exception as exc:
        print(json.dumps({
            "error": f"Failed to fetch transcript: {exc}",
            "video_id": video_id,
            "title": title,
        }))
        sys.exit(1)

    segments = [
        {
            "text": entry["text"],
            "start": entry["start"],
            "duration": entry["duration"],
            "timestamp": format_timestamp(entry["start"]),
        }
        for entry in transcript_entries
    ]

    full_text = " ".join(entry["text"] for entry in transcript_entries)

    result = {
        "video_id": video_id,
        "title": title,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "segment_count": len(segments),
        "segments": segments,
        "full_text": full_text,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
