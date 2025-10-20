#!/usr/bin/env python3
"""
youtubeTitle.py
----------------
Fetches the YouTube video title, sanitizes it for filenames, and saves it in currentTitle.json.

Usage:
    python youtubeTitle.py <YOUTUBE_VIDEO_ID>
"""

import sys
import re
import json
from pathlib import Path
import yt_dlp


def sanitize_filename(name: str) -> str:
    r"""
    Sanitize a string to be safe for filenames:
    - Remove invalid filename characters: \ / : * ? " < > |
    - Replace spaces with underscores
    """
    name = re.sub(r'[\\/:"*?<>|]+', '', name)
    name = re.sub(r'\s+', '_', name)
    return name


def fetch_video_title(video_id: str) -> str:
    """Fetch and sanitize YouTube video title using yt-dlp."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            title = info_dict.get('title')
    except yt_dlp.utils.DownloadError as e:
        print(f"[!] Download error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Unexpected error: {e}")
        sys.exit(1)

    if not title:
        print("[!] Could not retrieve video title.")
        sys.exit(1)

    return sanitize_filename(title)


def save_to_json(video_id: str, title: str, file_path: Path = Path("currentTitle.json")):
    """Save video ID and sanitized title to JSON."""
    data = {
        "videoID": video_id,
        "title": title
    }
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"[+] Saved video ID and title to {file_path}")
    except Exception as e:
        print(f"[!] Failed to save JSON: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: python youtubeTitle.py <YOUTUBE_VIDEO_ID>")
        sys.exit(1)

    video_id = sys.argv[1]
    title = fetch_video_title(video_id)
    print(f"[+] Fetched and sanitized title: {title}")
    save_to_json(video_id, title)


if __name__ == "__main__":
    main()
