#!/usr/bin/env python3
"""
pipeline.py
-----------
Flexible YouTube -> Anki deck pipeline.
Supports starting and ending at any step and automatically fetching/sanitizing titles.
Can process a single video or all videos in a playlist, with optional slicing.
Outputs for playlist videos are grouped under a folder named after the playlist.
"""

import subprocess
from pathlib import Path
import argparse
import sys
import json
import re
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen
import xml.etree.ElementTree as ET

PYTHON = sys.executable

def run_command(cmd_list):
    print(f"[+] Running: {' '.join(cmd_list)}")
    subprocess.run(cmd_list, check=True)
    print("[+] Completed successfully.\n")

def extract_video_id(url_or_id: str) -> str:
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

def extract_playlist_video_ids(playlist_url: str) -> tuple[str, list[str]]:
    parsed = urlparse(playlist_url)
    qs = parse_qs(parsed.query)
    playlist_id = qs.get("list")
    if not playlist_id:
        raise ValueError(f"Cannot extract playlist ID from '{playlist_url}'")
    playlist_id = playlist_id[0]

    feed_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
    with urlopen(feed_url) as response:
        xml_data = response.read()
    root = ET.fromstring(xml_data)
    video_ids = [entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
                 for entry in root.findall("{http://www.w3.org/2005/Atom}entry")]

    playlist_title = root.find("{http://www.w3.org/2005/Atom}title").text
    sanitized_title = re.sub(r'[\\/:"*?<>|]+', '', playlist_title)
    sanitized_title = re.sub(r'\s+', '_', sanitized_title)
    return sanitized_title, video_ids

def ensure_title(video_id: str, title_json: Path, scripts_dir: Path,
                 cookies: str | None = None, manual_title: str | None = None) -> str:
    if manual_title:
        sanitized_title = re.sub(r'[\\/:"*?<>|]+', '', manual_title)
        sanitized_title = re.sub(r'\s+', '_', sanitized_title)
        data = {"videoID": video_id, "title": sanitized_title}
        with open(title_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return sanitized_title

    if title_json.exists():
        with open(title_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        title = data.get("title")
        if not title:
            raise ValueError(f"No 'title' field in {title_json}")
        return title

    cmd = [PYTHON, str(scripts_dir / "youtubeTitle.py"), video_id]
    if cookies:
        cmd.extend(["--cookies", cookies])
    run_command(cmd)

    if not title_json.exists():
        raise FileNotFoundError(f"youtubeTitle.py did not produce {title_json}")

    with open(title_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("title")

def create_dirs(*dirs):
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def main():
    parser = argparse.ArgumentParser(
        description="YouTube -> Anki deck pipeline. Supports playlist slicing.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video", help="YouTube video URL or ID to process")
    group.add_argument("--playlist", help="YouTube playlist URL to process all videos")

    parser.add_argument("--playlist_start", type=int, default=1,
                        help="Start index in playlist (1-based, inclusive)")
    parser.add_argument("--playlist_end", type=int, default=None,
                        help="End index in playlist (1-based, inclusive)")
    parser.add_argument("--title_json", default="currentTitle.json")
    parser.add_argument("--title", help="Manually specify a title")
    parser.add_argument("--cookies", "--cookies-file", dest="cookies", default=None)
    parser.add_argument("--start_step", type=int, default=1, choices=range(1, 6))
    parser.add_argument("--end_step", type=int, default=5, choices=range(1, 6))

    args = parser.parse_args()

    start_step, end_step = args.start_step, args.end_step
    if start_step > end_step:
        raise ValueError("start_step cannot be greater than end_step")

    scripts_dir = Path("scripts")
    base_dirs = {
        "transcripts": Path("transcripts"),
        "reduced": Path("reduced"),
        "summaries": Path("summaries"),
        "flashcards": Path("flashcardTxt"),
        "apkg": Path("apkg")
    }
    create_dirs(*base_dirs.values())

    title_json = Path(args.title_json)
    cookies = args.cookies
    manual_title = args.title

    if args.video:
        video_ids = [extract_video_id(args.video)]
        playlist_folder = None
    else:
        playlist_folder, video_ids = extract_playlist_video_ids(args.playlist)
        total = len(video_ids)
        start_idx = max(args.playlist_start - 1, 0)
        end_idx = args.playlist_end if args.playlist_end else total
        video_ids = video_ids[start_idx:end_idx]
        print(f"[+] Processing videos {start_idx+1} to {end_idx} out of {total}")

    for video_id in video_ids:
        print(f"\n[+] Processing video: {video_id}")
        try:
            if not manual_title and title_json.exists():
                title_json.unlink()

            title = ensure_title(video_id, title_json, scripts_dir,
                                 cookies=cookies, manual_title=manual_title)

            # Use playlist folder if exists
            dirs = {}
            for key, base in base_dirs.items():
                dirs[key] = base / playlist_folder if playlist_folder else base
                create_dirs(dirs[key])

            transcript_file = dirs["transcripts"] / f"{title}_transcript.json"
            reduced_file = dirs["reduced"] / f"{title}_transcript_reduced.txt"
            summary_subdir = dirs["summaries"] / title
            full_summary_file = summary_subdir / "full_summary.txt"
            flashcard_file = dirs["flashcards"] / f"{title}.txt"
            create_dirs(summary_subdir)

            # Step 1: Fetch transcript
            if start_step <= 1 <= end_step:
                cmd = [PYTHON, str(scripts_dir / "fetch_transcript.py"), video_id,
                       "--output_dir", str(dirs["transcripts"]),
                       "--title_json", str(title_json)]
                if cookies: cmd.extend(["--cookies", cookies])
                run_command(cmd)

            # Step 2: Reduce transcript
            if start_step <= 2 <= end_step:
                run_command([PYTHON, str(scripts_dir / "reduce_transcript.py"),
                             str(transcript_file), "--outdir", str(dirs["reduced"])])

            # Step 3: Summarize chunks
            if start_step <= 3 <= end_step:
                run_command([PYTHON, str(scripts_dir / "llm.py"),
                             str(reduced_file), "--outdir", str(dirs["summaries"])])

            # Step 4: Generate flashcards
            if start_step <= 4 <= end_step:
                if not full_summary_file.exists():
                    raise FileNotFoundError(f"Full summary not found: {full_summary_file}")
                cmd = [PYTHON, str(scripts_dir / "summarize_flashcards_anki.py"),
                       str(full_summary_file),
                       "--title_json", str(title_json),
                       "--outdir", str(dirs["flashcards"])]
                run_command(cmd)

            # Step 5: Package Anki deck
            if start_step <= 5 <= end_step:
                if not flashcard_file.exists():
                    raise FileNotFoundError(f"Flashcard file not found: {flashcard_file}")
                run_command([PYTHON, str(scripts_dir / "anki_packager_tabbed.py"),
                             str(flashcard_file), "--title_json", str(title_json),
                             "--outdir", str(dirs["apkg"])])

        except Exception as e:
            print(f"[!] Error processing {video_id}: {e}")

    print("\n[+] Pipeline complete! Your Anki decks are in the playlist folder(s).")

if __name__ == "__main__":
    main()
