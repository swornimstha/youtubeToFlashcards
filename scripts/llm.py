#!/usr/bin/env python3
"""
llm.py
-----------------------------
Summarize each chunk of a reduced transcript individually.
Tries Google (Gemini) first, falls back to Mistral via direct REST API if Google fails.
Uses a high-density academic scribe prompt for better Anki card preparation.
"""

import os
import time
import argparse
import json
import urllib.request
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# SDKs
from google import genai

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Model Names
GOOGLE_MODEL = "gemma-4-26b-a4b-it" 
MISTRAL_MODEL = "mistral-small-latest"

MAX_RETRIES = 3
RETRY_DELAY = 5 

def get_google_summary(text: str, prompt_template: str) -> str:
    """Attempt to summarize using Google API."""
    if not GOOGLE_API_KEY:
        raise ConnectionError("Google API Key missing.")
    
    client = genai.Client(api_key=GOOGLE_API_KEY)
    # Format the prompt with the actual text
    full_prompt = prompt_template.format(text=text)
    
    response = client.models.generate_content(
        model=GOOGLE_MODEL,
        contents=full_prompt
    )
    return response.text.strip()

def get_mistral_summary(text: str, prompt_template: str) -> str:
    """Attempt to summarize using Mistral REST API directly."""
    if not MISTRAL_API_KEY:
        raise ConnectionError("Mistral API Key missing.")
    
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    full_prompt = prompt_template.format(text=text)
    
    data = {
        "model": MISTRAL_MODEL,
        "messages": [{"role": "user", "content": full_prompt}]
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        return result['choices'][0]['message']['content'].strip()

def read_chunks(file_path: Path) -> List[str]:
    """Read reduced transcript and split into chunks based on --- CHUNK header."""
    chunks: List[str] = []
    current_chunk: List[str] = []

    if not file_path.exists():
        return []

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
    """Summarize a chunk with automatic fallback and high-density academic prompt."""
    
    prompt_template = (
        "You are an expert academic scribe. Your task is to extract high-density knowledge "
        "from the following lecture transcript chunk for use in a study system.\n\n"
        "### INSTRUCTIONS:\n"
        "1. FILTER NOISE: Completely ignore all administrative talk, greetings, microphone checks, "
        "syllabus mentions, or classroom banter.\n"
        "2. TONE: Use clear, high-school level language that is direct and easy to understand.\n"
        "3. STRUCTURE: Organize the output into the following sections:\n"
        "    - **Core Concept**: The single most important idea in this chunk.\n"
        "    - **Key Terms & Definitions**: List any specific jargon, names, or dates mentioned and define them clearly.\n"
        "    - **Detailed Breakdown**: A bulleted list of the logical arguments or historical events presented. "
        "Do not omit supporting details.\n"
        "    - **Illustrative Examples**: Briefly mention any stories or analogies the professor used to explain a point.\n"
        "4. FORMAT: Do not include introductory phrases like \"This chunk discusses...\" or \"The professor starts by...\". "
        "Go straight to the content.\n\n"
        "### ACCURACY GUARDRAIL:\n"
        "Do not hallucinate. If a concept is mentioned but not explained, simply list it. Maintain the original logical flow of the lecture.\n\n"
        "TEXT TO PROCESS:\n"
        "{text}"
    )

    # Try Google First
    try:
        print("    [~] Trying Google...")
        return get_google_summary(text, prompt_template)
    except Exception as e:
        print(f"    [!] Google failed: {e}")
        print("    [~] Falling back to Mistral...")
        
        # Fallback to Mistral
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return get_mistral_summary(text, prompt_template)
            except Exception as e_mistral:
                print(f"    [!] Mistral attempt {attempt} failed: {e_mistral}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                else:
                    return "ERROR: All providers failed for this chunk."

def save_chunk_summaries(chunk_summaries: List[str], output_dir: Path) -> Path:
    """Save individual chunk summaries and a combined file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, summary in enumerate(chunk_summaries, 1):
        chunk_file = output_dir / f"chunk_{i}.txt"
        with chunk_file.open('w', encoding='utf-8') as f:
            f.write(summary)

    full_summary_file = output_dir / "full_summary.txt"
    with full_summary_file.open('w', encoding='utf-8') as f:
        f.write("\n\n---\n\n".join(chunk_summaries))

    return full_summary_file

def main():
    parser = argparse.ArgumentParser(description="Summarize chunks with Google/Mistral fallback")
    parser.add_argument("reduced_file", help="Path to reduced transcript file")
    parser.add_argument("--outdir", default="summaries", help="Base output directory")
    parser.add_argument("--sleep", type=float, default=1.0, help="Sleep between calls")
    args = parser.parse_args()

    reduced_path = Path(args.reduced_file)
    
    # Automatically extract the title from the input filename 
    title = reduced_path.stem.replace("_transcript_reduced", "")
    
    output_dir = Path(args.outdir) / title
    
    chunks = read_chunks(reduced_path)
    if not chunks:
        print("[!] No chunks found. Check your input file format.")
        return

    print(f"[+] Found {len(chunks)} chunks for {title}. Starting high-density summarization...")
    
    chunk_summaries = []
    for i, chunk in enumerate(chunks, 1):
        print(f"Processing chunk {i}/{len(chunks)}...")
        summary = summarize_text(chunk)
        chunk_summaries.append(summary)
        time.sleep(args.sleep)

    full_file = save_chunk_summaries(chunk_summaries, output_dir)
    print(f"\n[DONE] Summaries saved in: {output_dir}")
    print(f"[DONE] Combined summary: {full_file}")

if __name__ == "__main__":
    main()
