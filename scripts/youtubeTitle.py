#!/usr/bin/env python3
"""
youtubeTitle.py
----------------
Fetches the YouTube video title, sanitizes it for filenames, and saves it in currentTitle.json.
Supports optional cookies and manual title entry.

Usage:
    python youtubeTitle.py <YOUTUBE_VIDEO_ID> [--cookies <COOKIES_FILE>] [--title <MANUAL_TITLE>]
"""

import sys
import re
import json
from pathlib import Path
import argparse
import yt_dlp


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be safe for filenames:
    - Remove invalid filename characters: \ / : * ? " < > |
    - Replace spaces with underscores
    """
    name = re.sub(r'[\\/:"*?<>|]+', '', name)
    name = re.sub(r'\s+', '_', name)
    return name


def fetch_video_title(video_id: str, cookies: str | None = None) -> str:
    """Fetch and sanitize YouTube video title using yt-dlp."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {'quiet': True}
    if cookies:
        ydl_opts['cookiefile'] = cookies
        print(f"[i] Using cookies from: {cookies}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
    parser = argparse.ArgumentParser(
        description="Fetch and sanitize YouTube video title, optionally using cookies or manual title."
    )
    parser.add_argument("video_id", help="YouTube video ID")
    parser.add_argument("--cookies", "--cookies-file", dest="cookies", default=None,
                        help="Path to cookies.txt file for yt-dlp (optional)")
    parser.add_argument("--title", dest="manual_title", default=None,
                        help="Manually specify a title to save in JSON (skips fetching from YouTube)")
    args = parser.parse_args()

    video_id = args.video_id
    cookies = args.cookies
    manual_title = args.manual_title

    if manual_title:
        title = sanitize_filename(manual_title)
        print(f"[i] Using manual title: {title}")
    else:
        title = fetch_video_title(video_id, cookies=cookies)
        print(f"[+] Fetched and sanitized title: {title}")

    save_to_json(video_id, title)


if __name__ == "__main__":
    main()
