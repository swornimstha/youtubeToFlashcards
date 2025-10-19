#!/usr/bin/env python3
"""
fetch_transcript.py
------------------
Fetches a YouTube transcript and saves it as JSON.
Output filename is based on the video ID for clarity.
"""

import argparse
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter

def fetch_transcript(video_id: str, output_dir: Path, languages=None):
    """Fetch transcript from YouTube and save as JSON."""
    if languages is None:
        languages = ["en"]

    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id, languages=languages, preserve_formatting=True)

    formatter = JSONFormatter()
    json_formatted = formatter.format_transcript(transcript, indent=2)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{video_id}_transcript.json"
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

    args = parser.parse_args()
    fetch_transcript(args.video_id, Path(args.output_dir), args.lang)

if __name__ == "__main__":
    main()

