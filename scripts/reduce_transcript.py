#!/usr/bin/env python3
"""
reduce_transcript.py
--------------------
Preprocess and condense a YouTube transcript JSON file into coherent,
LLM-ready text chunks for summarization and flashcard generation.

Output: reduced/<sanitized_title>_transcript_reduced.txt
"""

import json
import re
import textwrap
from pathlib import Path
from typing import List, Dict, Any


def load_transcript(path: Path) -> List[Dict[str, Any]]:
    """Load transcript JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def clean_text(text: str) -> str:
    """Remove filler artifacts and normalize whitespace."""
    text = re.sub(r"\[.*?\]", "", text)  # remove [music], [applause], etc.
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def merge_segments(transcript: List[Dict[str, Any]], max_gap: float = 3.0) -> List[str]:
    """Merge short caption segments into paragraphs."""
    merged, buffer = [], []
    last_start = None

    for entry in transcript:
        segment = clean_text(entry.get("text", ""))
        if not segment:
            continue

        start = float(entry.get("start", 0))
        if last_start is not None and start - last_start > max_gap:
            merged.append(" ".join(buffer))
            buffer = []

        buffer.append(segment)
        last_start = start

    if buffer:
        merged.append(" ".join(buffer))
    return merged


def chunk_text(paragraphs: List[str], max_words: int = 600) -> List[str]:
    """Group paragraphs into chunks of roughly `max_words`."""
    chunks, current, count = [], [], 0

    for para in paragraphs:
        words = para.split()
        if count + len(words) > max_words and current:
            chunks.append(" ".join(current))
            current, count = [], 0

        current.append(para)
        count += len(words)

    if current:
        chunks.append(" ".join(current))
    return chunks


def save_chunks(chunks: List[str], title: str, out_dir: Path) -> Path:
    """Save chunks to reduced/<sanitized_title>_transcript_reduced.txt"""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{title}_transcript_reduced.txt"

    with open(out_path, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks, 1):
            f.write(f"--- CHUNK {i} ---\n")
            f.write(textwrap.fill(chunk, width=100))
            f.write("\n\n")

    print(f"[+] Wrote {len(chunks)} chunks to {out_path}")
    return out_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Reduce YouTube transcript for summarization.")
    parser.add_argument("input_json", help="Path to transcript JSON file")
    parser.add_argument("--words", type=int, default=600, help="Approximate words per chunk")
    parser.add_argument("--outdir", default="reduced", help="Directory to save reduced text files")
    parser.add_argument("--title_json", default="currentTitle.json",
                        help="Path to JSON containing sanitized title")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    out_dir = Path(args.outdir)

    # Read sanitized title from JSON
    with open(args.title_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        title = data.get("title")
    if not title:
        raise ValueError(f"No title found in {args.title_json}")

    transcript = load_transcript(input_path)
    paragraphs = merge_segments(transcript)
    chunks = chunk_text(paragraphs, max_words=args.words)
    save_chunks(chunks, title, out_dir)


if __name__ == "__main__":
    main()
