#!/usr/bin/env python3
"""
pipeline.py
-----------
Master pipeline to fetch a YouTube transcript, reduce it,
summarize it, generate flashcards, and package into Anki deck.

Usage:
    python pipeline.py <VIDEO_ID>
"""

import subprocess
from pathlib import Path
import sys

if len(sys.argv) != 2:
    print("Usage: python pipeline.py <YOUTUBE_VIDEO_ID>")
    sys.exit(1)

video_id = sys.argv[1]

# Directories
root = Path(__file__).parent.resolve()
scripts_dir = root / "scripts"
transcripts_dir = root / "transcripts"
reduced_dir = root / "reduced"
summaries_dir = root / "summaries"
flashcards_dir = root / "flashcards"

# Filenames
json_file = transcripts_dir / f"{video_id}_transcript.json"
reduced_file = reduced_dir / f"{video_id}_transcript_reduced.txt"
summary_dir = summaries_dir / f"{video_id}_transcript_reduced"
full_summary_file = summary_dir / "full_summary.txt"
flashcards_txt = flashcards_dir / f"{video_id}_flashcards.txt"
anki_deck_file = root / f"{video_id}_flashcards.apkg"


def run_script(script_name, *args):
    script_path = scripts_dir / script_name
    cmd = ["python3", str(script_path), *args]
    print(f"[+] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main():
    # Step 1: Fetch transcript
    run_script(
        "fetch_transcript.py",
        video_id,
        "--output_dir",
        str(transcripts_dir),
        "--lang",
        "en"
    )

    # Step 2: Reduce transcript
    run_script(
        "reduce_transcript.py",
        str(json_file),
        "--outdir",
        str(reduced_dir)
    )

    # Step 3: Summarize chunks
    run_script(
        "llm.py",
        str(reduced_file),
        "--outdir",
        str(summaries_dir)
    )

    # Step 4: Generate flashcards
    run_script(
        "summarize_flashcards_anki.py",
        str(full_summary_file),
        "--output",
        str(flashcards_txt)
    )

    # Step 5: Package into Anki deck
    run_script(
        "anki_packager_tabbed.py",
        str(flashcards_txt)
    )

    print(f"[+] Pipeline completed successfully!")
    print(f"    Transcript JSON: {json_file}")
    print(f"    Reduced transcript: {reduced_file}")
    print(f"    Full summary: {full_summary_file}")
    print(f"    Flashcards: {flashcards_txt}")
    print(f"    Anki deck: {anki_deck_file}")


if __name__ == "__main__":
    main()
