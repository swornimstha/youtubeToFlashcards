#!/usr/bin/env python3

"""
YouTube-to-Anki Pipeline
------------------------

Converts YouTube videos or playlists into structured Anki decks.
Supports hierarchical decks for playlists: each video becomes a subdeck
under the playlist deck. The pipeline runs five stages:

    1. Fetch transcript
    2. Reduce transcript
    3. Generate summaries
    4. Produce flashcards
    5. Package an .apkg deck

Stages can be executed independently. Optional cookies and manual titles
are supported. Outputs are organized per playlist or video title.

For playlists, individual video decks are always generated immediately.
A combined playlist deck is created at the end for hierarchical structure.
"""

import subprocess
from pathlib import Path
import argparse
import sys
import json
import re
import yt_dlp

PYTHON = sys.executable

def run_command(cmd_list):
    print(f"[+] Running: {' '.join(cmd_list)}")
    subprocess.run(cmd_list, check=True)
    print("[+] Completed.\n")

def extract_video_id(url_or_id: str) -> str:
    if re.fullmatch(r'[a-zA-Z0-9_-]{11}', url_or_id):
        return url_or_id
    parsed = yt_dlp.utils.urlparse(url_or_id)
    if parsed.hostname in ("www.youtube.com", "youtube.com") and "v" in parsed.query:
        return re.search(r"v=([a-zA-Z0-9_-]{11})", parsed.query).group(1)
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

    # Add '--' before video_id so IDs starting with '-' aren't treated as options
    cmd = [PYTHON, str(scripts_dir / "youtubeTitle.py"), "--", video_id]
    if cookies:
        cmd += ["--cookies", cookies]
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

    # --- Determine videos to process ---
    if args.video:
        video_ids = [extract_video_id(args.video)]
        playlist_folder = None
        single_video_mode = True
    else:
        playlist_folder, vids = extract_playlist_video_ids(args.playlist)
        total = len(vids)
        start = max(args.playlist_start - 1, 0)
        end = args.playlist_end or total
        video_ids = vids[start:end]
        print(f"[+] Processing {start+1} to {end} of {total}")
        single_video_mode = False

    # --- Process each video ---
    decks_for_playlist = []
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

            # Step 1: Fetch transcript
            if args.start_step <= 1 <= args.end_step:
                cmd = [
                    PYTHON, str(scripts / "fetch_transcript.py"),
                    "--output_dir", str(dirs["transcripts"]),
                    "--title_json", str(title_json),
                    "--", vid
                ]
                if cookies:
                    cmd += ["--cookies", cookies]
                run_command(cmd)

            # Step 2: Reduce transcript
            if args.start_step <= 2 <= args.end_step:
                run_command([
                    PYTHON, str(scripts / "reduce_transcript.py"),
                    str(transcript), "--outdir", str(dirs["reduced"])
                ])

            # Step 3: Summarize chunks
            if args.start_step <= 3 <= args.end_step:
                run_command([
                    PYTHON, str(scripts / "llm.py"),
                    str(reduced), "--outdir", str(dirs["summaries"])
                ])

            # Step 4: Generate flashcards
            if args.start_step <= 4 <= args.end_step:
                run_command([
                    PYTHON, str(scripts / "summarize_flashcards_anki.py"),
                    str(full_summary),
                    "--title_json", str(title_json),
                    "--outdir", str(dirs["flashcards"])
                ])

            # Step 5: Package single video deck immediately
            if args.start_step <= 5 <= args.end_step:
                run_command([
                    PYTHON, str(scripts / "anki_packager_tabbed.py"),
                    "--input_file", str(flashcards),
                    "--title_json", str(title_json),
                    "--outdir", str(dirs["apkg"])
                ])

                if not single_video_mode:
                    decks_for_playlist.append((flashcards, title))

        except Exception as e:
            print(f"[!] Error: {e}")

    # --- Write combined hierarchical deck for playlist ---
    if decks_for_playlist:
        combined_pkg = dirs["apkg"] / f"{playlist_folder}.apkg"
        cmd = [PYTHON, str(scripts / "anki_packager_tabbed.py")]
        for fc_file, title in decks_for_playlist:
            cmd += ["--input_file", str(fc_file), "--subdeck_title", title]
        cmd += ["--outdir", str(dirs["apkg"]), "--playlist_name", playlist_folder]
        run_command(cmd)

    print("\n[+] Done.")

if __name__ == "__main__":
    main()
