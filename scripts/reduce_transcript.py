#!/usr/bin/env python3
import json
import re
import textwrap
from pathlib import Path
from typing import List, Dict, Any

def load_transcript(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def clean_text(text: str) -> str:
    text = re.sub(r"\[.*?\]", "", text)  # remove [music], etc.
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def merge_segments(transcript: List[Dict[str, Any]], max_gap: float = 3.0) -> List[str]:
    merged, buffer = [], []
    last_end = None

    for entry in transcript:
        segment = clean_text(entry.get("text", ""))
        if not segment:
            continue

        start = float(entry.get("start", 0))
        duration = float(entry.get("duration", 0))
        
        if last_end is not None and (start - last_end) > max_gap:
            merged.append(" ".join(buffer))
            buffer = []

        buffer.append(segment)
        last_end = start + duration

    if buffer:
        merged.append(" ".join(buffer))
    return merged

def chunk_text(paragraphs: List[str], max_words: int = 3000, overlap_paras: int = 2) -> List[str]:
    """
    Groups paragraphs into chunks. 
    When a chunk is full, it starts the next one using the last `overlap_paras` 
    from the previous chunk to maintain context.
    """
    chunks, current, count = [], [], 0

    for para in paragraphs:
        words = para.split()
        if count + len(words) > max_words and current:
            chunks.append(" ".join(current))
            # Start next chunk with the tail of the previous one
            current = current[-overlap_paras:] if len(current) > overlap_paras else current
            count = sum(len(p.split()) for p in current)

        current.append(para)
        count += len(words)

    if current:
        chunks.append(" ".join(current))
    return chunks

def save_chunks(chunks: List[str], title: str, out_dir: Path) -> Path:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    # Bumped default to 3000 to utilize LLM context better
    parser.add_argument("--words", type=int, default=3000)
    parser.add_argument("--outdir", default="reduced")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    title = input_path.stem.replace("_transcript", "")

    transcript = load_transcript(input_path)
    paragraphs = merge_segments(transcript)
    chunks = chunk_text(paragraphs, max_words=args.words)
    save_chunks(chunks, title, Path(args.outdir))

if __name__ == "__main__":
    main()
