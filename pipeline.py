#!/usr/bin/env python3

"""
YouTube-to-Anki Pipeline
------------------------
Converts YouTube videos or playlists into structured Anki decks.
Includes Smart Caching, File-Existence Auto-Resume, and File Logging.
"""

import subprocess
from pathlib import Path
import argparse
import sys
import json
import re
import yt_dlp
import logging

PYTHON = sys.executable

# --- 1. Setup Logging ---
# This logs to BOTH the terminal and a permanent 'pipeline.log' file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("pipeline.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def log_info(msg):
    logging.info(msg)

def log_error(msg):
    logging.error(msg)

def run_command(cmd_list):
    log_info(f"Running: {' '.join(cmd_list)}")
    subprocess.run(cmd_list, check=True)
    log_info("Completed.\n")

# --- 2. Setup Smart Cache ---
CACHE_FILE = Path("video_cache.json")

def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache_dict: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_dict, f, indent=4)

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

def mkdirs(*dirs):
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def main():
    parser = argparse.ArgumentParser(description="YouTube → Anki pipeline with Auto-Resume")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--video")
    g.add_argument("--playlist")
    parser.add_argument("--title_json", default="currentTitle.json")
    parser.add_argument("--title", help="Manual title override")
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
    video_cache = load_cache()

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
        log_info(f"Processing {start+1} to {end} of {total} in playlist: {playlist_folder}")
        single_video_mode = False

    dirs = {k: (v / playlist_folder if playlist_folder else v) for k, v in base.items()}
    mkdirs(*dirs.values())

    # --- Process each video ---
    decks_for_playlist = []
    for vid in video_ids:
        log_info(f"\n{'='*40}\nProcessing Video ID: {vid}\n{'='*40}")
        try:
            # ---------------------------------------------------------
            # STEP 1: Fetch Transcript (With Caching & Resume)
            # ---------------------------------------------------------
            title = video_cache.get(vid)
            
            if title and (dirs["transcripts"] / f"{title}_transcript.json").exists():
                log_info(f"[SKIP] Step 1: Transcript for '{title}' already exists.")
                # We still need to write the currentTitle.json so later scripts don't crash
                with open(title_json, "w", encoding="utf-8") as f:
                    json.dump({"videoID": vid, "title": title}, f, indent=4)
            else:
                if args.start_step <= 1 <= args.end_step:
                    log_info("[RUN] Step 1: Fetching metadata and transcript...")
                    cmd = [
                        PYTHON, str(scripts / "fetch_transcript.py"),
                        "--output_dir", str(dirs["transcripts"]),
                        "--title_json", str(title_json)
                    ]
                    if cookies: cmd += ["--cookies", cookies]
                    if args.title: cmd += ["--title", args.title]
                    cmd += ["--", vid]
                    
                    run_command(cmd)

                    # Update Cache with the newly fetched title
                    if title_json.exists():
                        with open(title_json, "r", encoding="utf-8") as f:
                            title = json.load(f)["title"]
                            video_cache[vid] = title
                            save_cache(video_cache)
                else:
                    log_info("[!] Step 1 skipped by arguments, but no cached file exists. This may cause errors downstream.")

            # If title is still completely unknown, we must skip this video
            if not title:
                log_error(f"[!] Could not determine title for {vid}. Skipping.")
                continue

            # Define Expected File Paths
            transcript = dirs["transcripts"] / f"{title}_transcript.json"
            reduced = dirs["reduced"] / f"{title}_transcript_reduced.txt"
            summary_dir = dirs["summaries"] / title
            full_summary = summary_dir / "full_summary.txt"
            flashcards = dirs["flashcards"] / f"{title}.txt"
            apkg_file = dirs["apkg"] / f"{title}.apkg"
            
            mkdirs(summary_dir)

            # ---------------------------------------------------------
            # STEP 2: Reduce Transcript
            # ---------------------------------------------------------
            if args.start_step <= 2 <= args.end_step:
                if reduced.exists():
                    log_info(f"[SKIP] Step 2: Reduced text already exists for '{title}'.")
                else:
                    log_info("[RUN] Step 2: Reducing transcript...")
                    run_command([
                        PYTHON, str(scripts / "reduce_transcript.py"),
                        str(transcript), "--outdir", str(dirs["reduced"])
                    ])

            # ---------------------------------------------------------
            # STEP 3: Summarize with LLM
            # ---------------------------------------------------------
            if args.start_step <= 3 <= args.end_step:
                if full_summary.exists():
                    log_info(f"[SKIP] Step 3: LLM Summary already exists for '{title}'.")
                else:
                    log_info("[RUN] Step 3: Generating summaries...")
                    run_command([
                        PYTHON, str(scripts / "llm.py"),
                        str(reduced), "--outdir", str(dirs["summaries"])
                    ])

            # ---------------------------------------------------------
            # STEP 4: Generate Flashcards
            # ---------------------------------------------------------
            if args.start_step <= 4 <= args.end_step:
                if flashcards.exists():
                    log_info(f"[SKIP] Step 4: Flashcards already exist for '{title}'.")
                else:
                    log_info("[RUN] Step 4: Formatting Anki flashcards...")
                    run_command([
                        PYTHON, str(scripts / "summarize_flashcards_anki.py"),
                        str(full_summary),
                        "--title_json", str(title_json),
                        "--outdir", str(dirs["flashcards"])
                    ])

            # ---------------------------------------------------------
            # STEP 5: Package single video deck
            # ---------------------------------------------------------
            if args.start_step <= 5 <= args.end_step:
                if apkg_file.exists():
                    log_info(f"[SKIP] Step 5: .apkg deck already exists for '{title}'.")
                else:
                    log_info("[RUN] Step 5: Packaging Anki deck...")
                    run_command([
                        PYTHON, str(scripts / "anki_packager_tabbed.py"),
                        "--input_file", str(flashcards),
                        "--title_json", str(title_json),
                        "--outdir", str(dirs["apkg"])
                    ])

            if not single_video_mode:
                decks_for_playlist.append((flashcards, title))

        except subprocess.CalledProcessError as e:
            log_error(f"[!] Subprocess failed for {vid}: {e}")
        except Exception as e:
            log_error(f"[!] Unexpected Error processing {vid}: {e}")

    # --- Write combined hierarchical deck for playlist ---
    if decks_for_playlist:
        log_info(f"\n{'='*40}\nCompiling Master Playlist Deck\n{'='*40}")
        combined_pkg = dirs["apkg"] / f"{playlist_folder}.apkg"
        
        if combined_pkg.exists():
            log_info(f"[SKIP] Combined master deck '{playlist_folder}.apkg' already exists.")
        else:
            cmd = [PYTHON, str(scripts / "anki_packager_tabbed.py")]
            for fc_file, t_name in decks_for_playlist:
                if fc_file.exists():
                    cmd += ["--input_file", str(fc_file), "--subdeck_title", t_name]
            cmd += ["--outdir", str(dirs["apkg"]), "--playlist_name", playlist_folder]
            run_command(cmd)

    log_info("\n[+] Pipeline Completed Successfully.")

if __name__ == "__main__":
    main()
