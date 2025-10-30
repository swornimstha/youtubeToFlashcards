#!/usr/bin/env python3
"""
llm.py
-----------------------------
Summarize each chunk of a reduced transcript individually,
save chunk summaries and a full concatenated summary using
sanitized YouTube title for filenames.
"""

import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from mistralai import Mistral
from typing import List

# Load environment variables
load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    raise ValueError("MISTRAL_API_KEY not found in environment variables")

client = Mistral(api_key=API_KEY)
MODEL_NAME = "mistral-small-latest"

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

def read_chunks(file_path: Path) -> List[str]:
    """Read reduced transcript and split into chunks"""
    chunks: List[str] = []
    current_chunk: List[str] = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('--- CHUNK'):
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
            elif line:
                current_chunk.append(line)
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

def summarize_text(text: str) -> str:
    """Summarize a chunk in clear, complete language without extra headers."""
    prompt = (
        f"Please summarize the following lecture text in clear, high school-level language, "
        f"covering all points and topics. Do not add extra introductory lines like 'Here’s a summary'. "
        f"Keep it accurate and do not omit details.\n\n{text}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.complete(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[!] Error summarizing chunk (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                print(f"    Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                print("    Max retries reached, returning placeholder summary.")
                return "ERROR: Summary failed."

def save_chunk_summaries(chunk_summaries: List[str], output_dir: Path) -> Path:
    """Save individual chunk summaries and the combined full summary"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save individual chunks
    for i, summary in enumerate(chunk_summaries, 1):
        chunk_file = output_dir / f"chunk_{i}.txt"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(summary)

    # Save full concatenated summary
    full_summary_file = output_dir / "full_summary.txt"
    with open(full_summary_file, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(chunk_summaries))

    return full_summary_file

def load_sanitized_title(title_json: Path) -> str:
    """Load sanitized YouTube title from JSON file"""
    if not title_json.exists():
        raise FileNotFoundError(f"Title JSON file not found: {title_json}")
    with open(title_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    title = data.get("title")
    if not title:
        raise ValueError(f"No 'title' field found in {title_json}")
    return title

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Summarize chunks and save summaries using sanitized title")
    parser.add_argument("reduced_file", help="Path to reduced transcript file")
    parser.add_argument("--title_json", default="currentTitle.json",
                        help="Path to JSON containing sanitized title")
    parser.add_argument("--outdir", default="summaries",
                        help="Directory to save chunk summaries")
    parser.add_argument("--sleep", type=float, default=1.0,
                        help="Seconds to wait between API calls")
    args = parser.parse_args()

    title = load_sanitized_title(Path(args.title_json))
    reduced_path = Path(args.reduced_file)
    output_dir = Path(args.outdir) / title
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = read_chunks(reduced_path)
    if not chunks:
        print("[!] No chunks found in the reduced transcript.")
        return

    print(f"[+] Found {len(chunks)} chunks. Summarizing each chunk...")
    chunk_summaries: List[str] = []

    for i, chunk in enumerate(chunks, 1):
        print(f"  Summarizing chunk {i}/{len(chunks)}...")
        summary = summarize_text(chunk)
        chunk_summaries.append(summary)
        time.sleep(args.sleep)

    full_summary_file = save_chunk_summaries(chunk_summaries, output_dir)
    print(f"[+] Summaries saved in {output_dir}")
    print(f"[+] Full concatenated summary saved as {full_summary_file}")

if __name__ == "__main__":
    main()

