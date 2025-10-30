#!/usr/bin/env python3
"""
pipeline.py
-----------
Flexible YouTube → Anki deck pipeline.
Supports starting and ending at any step, automatically fetching/sanitizing titles,
or using a manually provided title.
"""

import subprocess
from pathlib import Path
import argparse
import json
import re
from urllib.parse import urlparse, parse_qs


def run_command(cmd_list):
    """Run a Python script as a subprocess and print status."""
    print(f"[+] Running: {' '.join(cmd_list)}")
    subprocess.run(cmd_list, check=True)
    print("[+] Completed successfully.\n")


def extract_video_id(url_or_id: str) -> str:
    """Extract YouTube video ID from URL or return it directly."""
    if re.fullmatch(r'[a-zA-Z0-9_-]{11}', url_or_id):
        return url_or_id

    parsed = urlparse(url_or_id)
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        qs = parse_qs(parsed.query)
        if 'v' in qs:
            return qs['v'][0]
    elif parsed.hostname in ('youtu.be',):
        return parsed.path.lstrip('/')

    raise ValueError(f"Cannot extract YouTube video ID from '{url_or_id}'")


def ensure_title(video_id: str, title_json: Path, scripts_dir: Path,
                 manual_title: str | None = None, cookies: str | None = None) -> str:
    """
    Ensure we have a sanitized title.
    - Use manual_title if provided
    - Otherwise, fetch via youtubeTitle.py (optionally using cookies)
    """
    if manual_title:
        print(f"[i] Using manual title: {manual_title}")
        cmd = ["python3", str(scripts_dir / "youtubeTitle.py"), video_id, "--title", manual_title]
        run_command(cmd)
    elif not title_json.exists():
        print(f"[!] Title JSON not found, fetching via youtubeTitle.py...")
        cmd = ["python3", str(scripts_dir / "youtubeTitle.py"), video_id]
        if cookies:
            cmd.extend(["--cookies", cookies])
            print(f"[i] Using cookies file: {cookies}")
        run_command(cmd)

    if not title_json.exists():
        raise FileNotFoundError(f"{title_json} was not created.")

    with open(title_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        title = data.get("title")
    if not title:
        raise ValueError(f"No 'title' field found in {title_json}")

    return title


def create_dirs(*dirs):
    """Ensure that directories exist."""
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="YouTube → Anki deck pipeline. Steps can be started or ended mid-pipeline.",
        epilog=(
            "Step mapping:\n"
            "1 = Fetch transcript\n"
            "2 = Reduce transcript\n"
            "3 = Summarize chunks\n"
            "4 = Generate flashcards\n"
            "5 = Package Anki deck"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("video", help="YouTube video URL or ID to process")
    parser.add_argument("--title_json", default="currentTitle.json",
                        help="JSON file with sanitized title")
    parser.add_argument("--title", default=None,
                        help="Manually specify a title to save in JSON (skips fetching from YouTube)")
    parser.add_argument("--cookies", "--cookies-file", dest="cookies", default=None,
                        help="Path to cookies.txt file for authenticated yt-dlp requests (optional)")
    parser.add_argument("--start_step", type=int, default=1, choices=range(1, 6),
                        help="Step number to start at (1–5)")
    parser.add_argument("--end_step", type=int, default=5, choices=range(1, 6),
                        help="Step number to end at (1–5)")

    args = parser.parse_args()

    video_id = extract_video_id(args.video)
    title_json = Path(args.title_json)
    start_step = args.start_step
    end_step = args.end_step
    cookies = args.cookies
    manual_title = args.title

    if start_step > end_step:
        raise ValueError(f"start_step ({start_step}) cannot be greater than end_step ({end_step})")

    # Remove stale title JSON
    if title_json.exists():
        print(f"[!] Removing old title JSON: {title_json}")
        title_json.unlink()

    scripts_dir = Path("scripts")
    transcripts_dir = Path("transcripts")
    reduced_dir = Path("reduced")
    summaries_dir = Path("summaries")
    flashcards_dir = Path("flashcardTxt")
    apkg_dir = Path("apkg")

    # Ensure directories exist
    create_dirs(transcripts_dir, reduced_dir, summaries_dir, flashcards_dir, apkg_dir)

    # Determine title
    title = ensure_title(video_id, title_json, scripts_dir,
                         manual_title=manual_title, cookies=cookies)

    transcript_file = transcripts_dir / f"{title}_transcript.json"
    reduced_file = reduced_dir / f"{title}_transcript_reduced.txt"
    summary_subdir = summaries_dir / title
    full_summary_file = summary_subdir / "full_summary.txt"
    flashcard_file = flashcards_dir / f"{title}.txt"

    # Ensure summary subdir exists
    create_dirs(summary_subdir)

    # Step 1: Fetch transcript
    if start_step <= 1 <= end_step:
        cmd = [
            "python3", str(scripts_dir / "fetch_transcript.py"),
            video_id,
            "--output_dir", str(transcripts_dir),
            "--title_json", str(title_json)
        ]
        run_command(cmd)

    # Step 2: Reduce transcript
    if start_step <= 2 <= end_step:
        run_command([
            "python3", str(scripts_dir / "reduce_transcript.py"),
            str(transcript_file),
            "--outdir", str(reduced_dir)
        ])

    # Step 3: Summarize chunks
    if start_step <= 3 <= end_step:
        run_command([
            "python3", str(scripts_dir / "llm.py"),
            str(reduced_file),
            "--outdir", str(summaries_dir)
        ])

    # Step 4: Generate flashcards
    if start_step <= 4 <= end_step:
        if not full_summary_file.exists():
            raise FileNotFoundError(f"Full summary not found: {full_summary_file}")
        run_command([
            "python3", str(scripts_dir / "summarize_flashcards_anki.py"),
            str(full_summary_file)
        ])

    # Step 5: Package Anki deck
    if start_step <= 5 <= end_step:
        if not flashcard_file.exists():
            raise FileNotFoundError(f"Flashcard file not found: {flashcard_file}")
        run_command([
            "python3", str(scripts_dir / "anki_packager_tabbed.py"),
            str(flashcard_file),
            "--title_json", str(title_json),
            "--outdir", str(apkg_dir)
        ])

    print("[+] Pipeline complete! Your Anki deck is in the 'apkg/' directory.")


if __name__ == "__main__":
    main()
