#!/usr/bin/env python3

"""
YouTube-to-Anki Pipeline
------------------------

A streamlined orchestration script that converts YouTube videos—or entire
playlists—into structured Anki decks. The pipeline runs five sequential stages:

    1. Fetch transcript
    2. Reduce transcript
    3. Generate hierarchical summaries
    4. Produce flashcards
    5. Package an .apkg deck

Playlists are enumerated through yt-dlp to ensure complete, reliable retrieval
of all video IDs. When processing playlists, outputs are automatically grouped
into a dedicated folder named after the playlist.

Each stage may be executed independently or as part of the full sequence, and
the system accommodates manual titles and optional cookie-based requests.
Designed for clarity, reproducibility, and efficient large-scale processing.
"""

import subprocess
from pathlib import Path
import argparse
import sys
import json
import re
from urllib.parse import urlparse, parse_qs
import yt_dlp

PYTHON = sys.executable

def run_command(cmd_list):
    print(f"[+] Running: {' '.join(cmd_list)}")
    subprocess.run(cmd_list, check=True)
    print("[+] Completed.\n")

def extract_video_id(url_or_id: str) -> str:
    if re.fullmatch(r'[a-zA-Z0-9_-]{11}', url_or_id):
        return url_or_id
    parsed = urlparse(url_or_id)
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")
    raise ValueError(f"Could not extract video ID from '{url_or_id}'")

def extract_playlist_video_ids(playlist_url: str) -> tuple[str, list[str]]:
    opts = {"extract_flat": True, "quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    entries = info.get("entries", [])
    video_ids = [e["id"] for e in entries]

    title = info.get("title", "playlist")
    title = re.sub(r'[\\/:"*?<>|]+', "", title)
    title = re.sub(r"\s+", "_", title)

    return title, video_ids

def ensure_title(video_id: str, title_json: Path, scripts_dir: Path,
                 cookies: str | None = None, manual: str | None = None) -> str:

    if manual:
        safe = re.sub(r'[\\/:"*?<>|]+', "", manual)
        safe = re.sub(r"\s+", "_", safe)
        with title_json.open("w", encoding="utf-8") as f:
            json.dump({"videoID": video_id, "title": safe}, f, indent=4)
        return safe

    if title_json.exists():
        with open(title_json, "r", encoding="utf-8") as f:
            return json.load(f)["title"]

    cmd = [PYTHON, str(scripts_dir / "youtubeTitle.py"), video_id]
    if cookies: cmd += ["--cookies", cookies]
    run_command(cmd)

    with open(title_json, "r", encoding="utf-8") as f:
        return json.load(f)["title"]

def mkdirs(*dirs):
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def main():
    parser = argparse.ArgumentParser(description="YouTube → Anki pipeline")

    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--video")
    g.add_argument("--playlist")

    parser.add_argument("--title_json", default="currentTitle.json")
    parser.add_argument("--title")
    parser.add_argument("--cookies")
    parser.add_argument("--start_step", type=int, default=1)
    parser.add_argument("--end_step", type=int, default=5)
    parser.add_argument("--playlist_start", type=int, default=1)
    parser.add_argument("--playlist_end", type=int)

    args = parser.parse_args()

    scripts = Path("scripts")

    base = {
        "transcripts": Path("transcripts"),
        "reduced": Path("reduced"),
        "summaries": Path("summaries"),
        "flashcards": Path("flashcardTxt"),
        "apkg": Path("apkg"),
    }
    mkdirs(*base.values())

    title_json = Path(args.title_json)
    cookies = args.cookies
    manual_title = args.title

    if args.video:
        video_ids = [extract_video_id(args.video)]
        playlist_folder = None
    else:
        playlist_folder, vids = extract_playlist_video_ids(args.playlist)
        total = len(vids)
        start = max(args.playlist_start - 1, 0)
        end = args.playlist_end or total
        video_ids = vids[start:end]
        print(f"[+] Processing {start+1} to {end} of {total}")

    for vid in video_ids:
        print(f"\n[+] Video: {vid}")

        try:
            if not manual_title and title_json.exists():
                title_json.unlink()

            title = ensure_title(vid, title_json, scripts, cookies, manual_title)

            dirs = {k: (v / playlist_folder if playlist_folder else v)
                    for k, v in base.items()}
            mkdirs(*dirs.values())

            transcript = dirs["transcripts"] / f"{title}_transcript.json"
            reduced = dirs["reduced"] / f"{title}_transcript_reduced.txt"
            summary_dir = dirs["summaries"] / title
            full_summary = summary_dir / "full_summary.txt"
            flashcards = dirs["flashcards"] / f"{title}.txt"
            mkdirs(summary_dir)

            if args.start_step <= 1 <= args.end_step:
                cmd = [
                    PYTHON, str(scripts / "fetch_transcript.py"), vid,
                    "--output_dir", str(dirs["transcripts"]),
                    "--title_json", str(title_json),
                ]
                if cookies: cmd += ["--cookies", cookies]
                run_command(cmd)

            if args.start_step <= 2 <= args.end_step:
                run_command([
                    PYTHON, str(scripts / "reduce_transcript.py"),
                    str(transcript), "--outdir", str(dirs["reduced"])
                ])

            if args.start_step <= 3 <= args.end_step:
                run_command([
                    PYTHON, str(scripts / "llm.py"),
                    str(reduced), "--outdir", str(dirs["summaries"])
                ])

            if args.start_step <= 4 <= args.end_step:
                run_command([
                    PYTHON, str(scripts / "summarize_flashcards_anki.py"),
                    str(full_summary),
                    "--title_json", str(title_json),
                    "--outdir", str(dirs["flashcards"])
                ])

            if args.start_step <= 5 <= args.end_step:
                run_command([
                    PYTHON, str(scripts / "anki_packager_tabbed.py"),
                    str(flashcards),
                    "--title_json", str(title_json),
                    "--outdir", str(dirs["apkg"])
                ])

        except Exception as e:
            print(f"[!] Error: {e}")

    print("\n[+] Done.")

if __name__ == "__main__":
    main()
