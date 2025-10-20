#!/usr/bin/env python3
"""
fetch_transcript.py
------------------
Fetches a YouTube transcript and saves it as JSON.
Output filename is based on the sanitized YouTube title.
"""

import argparse
from pathlib import Path
import json
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter

def fetch_transcript(video_id: str, output_dir: Path, title_json: Path, languages=None):
    """Fetch transcript from YouTube and save as JSON using sanitized title."""
    if languages is None:
        languages = ["en"]

    # Load sanitized title from JSON
    with open(title_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        title = data.get("title")
    if not title:
        raise ValueError(f"No title found in {title_json}")

    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id, languages=languages, preserve_formatting=True)

    formatter = JSONFormatter()
    json_formatted = formatter.format_transcript(transcript, indent=2)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{title}_transcript.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json_formatted)

    print(f"[+] Transcript saved to {output_file}")
    print(f"[+] Total segments: {len(transcript)}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Fetch a YouTube transcript and save as JSON")
    parser.add_argument("video_id", help="YouTube video ID")
    parser.add_argument("--output_dir", "-o", default="transcripts",
                        help="Directory to save JSON transcript (default: transcripts/)")
    parser.add_argument("--lang", "-l", nargs="+", default=["en"],
                        help="Preferred language(s), e.g., en fr es (default: en)")
    parser.add_argument("--title_json", default="currentTitle.json",
                        help="Path to JSON containing sanitized title")
    args = parser.parse_args()

    fetch_transcript(args.video_id, Path(args.output_dir), Path(args.title_json), args.lang)

if __name__ == "__main__":
    main()
