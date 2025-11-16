#!/usr/bin/env python3
"""
llm.py (Google Gemini + Mistral selectable, with robust rate-limit handling, updated for latest SDK)
-------------------------------------------------
Summarize each chunk of a reduced transcript individually,
save chunk summaries and a full concatenated summary using
sanitized YouTube title for filenames.

Default provider: Google
Loads GOOGLE_API_KEY automatically.
"""

import os
import time
import json
import random
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Literal

# Providers (Google + Mistral)
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from mistralai.client import MistralClient as Mistral
    from mistralai.models.chat_completion import ChatMessage
except ImportError:
    Mistral = None
    ChatMessage = None

load_dotenv()

DEFAULT_PROVIDER: Literal["google", "mistral"] = "google"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not GOOGLE_API_KEY and not MISTRAL_API_KEY:
    raise ValueError("No GOOGLE_API_KEY or MISTRAL_API_KEY found.")

# ---------------------------------------------------------------
# Initialize clients
# ---------------------------------------------------------------

def init_google():
    if not genai:
        raise ImportError("google-generativeai package not installed. Install with: pip install google-generativeai")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY missing.")
    genai.configure(api_key=GOOGLE_API_KEY)
    # The genai.GenerativeModel is now the primary way to interact with models.
    # No need for genai.Client() anymore.
    model = genai.GenerativeModel('gemini-2.5-flash-lite') # Using gemini-1.5-flash as a more recent, faster model
    return model


def init_mistral():
    if not Mistral:
        raise ImportError("mistralai package not installed.")
    if not MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY missing.")
    return Mistral(api_key=MISTRAL_API_KEY), "mistral-small-latest"

# ---------------------------------------------------------------
# Chunk reader
# ---------------------------------------------------------------

def read_chunks(file_path: Path) -> List[str]:
    chunks, current_chunk = [], []
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

# ---------------------------------------------------------------
# Summarization wrapper with exponential backoff for rate limits
# ---------------------------------------------------------------
MAX_RETRIES = 5
BASE_DELAY = 5

def summarize_text(text: str, provider: str):
    prompt = (
        f"Please summarize the following lecture text in clear, high school-level language, "
        f"covering all points and topics. Do not add extra introductory lines like 'Here’s a summary'. "
        f"Keep it accurate and do not omit details.\n\n{text}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if provider == "google":
                model = init_google()
                # For genai.GenerativeModel, we use generate_content
                response = model.generate_content(prompt)
                return response.text.strip() # Access text directly from the response object

            elif provider == "mistral":
                if ChatMessage is None:
                    raise ImportError("mistralai.models.chat_completion.ChatMessage not found. Ensure mistralai package is up to date.")
                client, model_name = init_mistral()
                messages = [ChatMessage(role="user", content=prompt)]
                response = client.chat(model=model_name, messages=messages)
                return response.choices[0].message.content.strip()

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            # Check for specific Google GenAI rate limit errors
            is_rate_limit = False
            if provider == "google" and "ResourceExhausted" in str(e):
                is_rate_limit = True
            elif "429" in str(e): # General HTTP 429 for Mistral or other providers
                is_rate_limit = True

            if is_rate_limit:
                wait = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                print(f"[!] Rate limited, waiting {wait:.1f}s before retry (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
            elif attempt < MAX_RETRIES:
                wait = BASE_DELAY * attempt
                print(f"[!] Error encountered, retrying in {wait}s (attempt {attempt}/{MAX_RETRIES}): {e}")
                time.sleep(wait)
            else:
                print("[!] Max retries reached, returning placeholder summary.")
                return "ERROR: Summary failed."

# ---------------------------------------------------------------
# Save summaries
# ---------------------------------------------------------------

def save_chunk_summaries(chunk_summaries: List[str], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, summary in enumerate(chunk_summaries, 1):
        with open(output_dir / f"chunk_{i}.txt", 'w', encoding='utf-8') as f:
            f.write(summary)
    full_summary_file = output_dir / "full_summary.txt"
    with open(full_summary_file, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(chunk_summaries))
    return full_summary_file

# ---------------------------------------------------------------
# Load sanitized title
# ---------------------------------------------------------------

def load_sanitized_title(title_json: Path) -> str:
    if not title_json.exists():
        raise FileNotFoundError(f"Title JSON file not found: {title_json}")
    with open(title_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    title = data.get("title")
    if not title:
        raise ValueError(f"No 'title' field found in {title_json}")
    return title

# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Summarize chunks with Google or Mistral")
    parser.add_argument("reduced_file")
    parser.add_argument("--title_json", default="currentTitle.json")
    parser.add_argument("--outdir", default="summaries")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--provider", choices=["google","mistral"], default=DEFAULT_PROVIDER)
    args = parser.parse_args()

    title = load_sanitized_title(Path(args.title_json))
    reduced_path = Path(args.reduced_file)
    output_dir = Path(args.outdir) / title
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = read_chunks(reduced_path)
    if not chunks:
        print("[!] No chunks found in the reduced transcript.")
        return

    print(f"[+] Found {len(chunks)} chunks. Summarizing each chunk using {args.provider}...")
    summaries = []

    for i, chunk in enumerate(chunks, 1):
        print(f"  Summarizing chunk {i}/{len(chunks)}...")
        summary = summarize_text(chunk, args.provider)
        summaries.append(summary)
        time.sleep(args.sleep)

    full_summary = save_chunk_summaries(summaries, output_dir)
    print(f"[+] Summaries saved in {output_dir}")
    print(f"[+] Full concatenated summary saved as {full_summary}")

if __name__ == "__main__":
    main()
