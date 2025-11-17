#!/usr/bin/env python3
"""
YouTube Title Fetcher
youtubeTitle.py
---------------------

Retrieves a video's title via yt-dlp, sanitizes it for filesystem safety,
and stores both the video ID and cleaned title in `currentTitle.json`.

Features:
    • Robust title extraction using yt-dlp
    • Optional cookies for authenticated or region-locked videos
    • Optional manual title override
    • Filename-safe title normalization

Usage:
    python youtubeTitle.py <VIDEO_ID>
    python youtubeTitle.py <VIDEO_ID> --cookies cookies.txt
    python youtubeTitle.py <VIDEO_ID> --title "Custom Name"
"""

import sys
import re
import json
from pathlib import Path
import argparse
import yt_dlp


def sanitize_filename(name: str) -> str:
    """Remove illegal filename characters and collapse spaces into underscores."""
    name = re.sub(r'[\\/:*?"<>|]+', "", name)
    name = re.sub(r"\s+", "_", name)
    return name


def fetch_video_title(video_id: str, cookies: str | None = None) -> str:
    """Fetch a YouTube video title using yt-dlp and return a sanitized version."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {"quiet": True}

    if cookies:
        ydl_opts["cookiefile"] = cookies
        print(f"[i] Using cookies: {cookies}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get("title")
    except yt_dlp.utils.DownloadError as e:
        print(f"[!] yt-dlp error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Unexpected error: {e}")
        sys.exit(1)

    if not title:
        print("[!] Could not retrieve YouTube title.")
        sys.exit(1)

    return sanitize_filename(title)


def save_to_json(video_id: str, title: str, file_path: Path = Path("currentTitle.json")):
    """Write the video ID and sanitized title into currentTitle.json."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"videoID": video_id, "title": title}, f, indent=4, ensure_ascii=False)
        print(f"[+] Saved: {file_path}")
    except Exception as e:
        print(f"[!] Failed to write JSON: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Fetch and sanitize a YouTube video title.")
    parser.add_argument("video_id", help="YouTube video ID")
    parser.add_argument("--cookies", dest="cookies", default=None,
                        help="Optional path to cookies.txt for yt-dlp")
    parser.add_argument("--title", dest="manual_title", default=None,
                        help="Manually specify a title (skips YouTube lookup)")
    args = parser.parse_args()

    video_id = args.video_id

    if args.manual_title:
        title = sanitize_filename(args.manual_title)
        print(f"[i] Using manual title: {title}")
    else:
        title = fetch_video_title(video_id, cookies=args.cookies)
        print(f"[+] Retrieved title: {title}")

    save_to_json(video_id, title)


if __name__ == "__main__":
    main()
