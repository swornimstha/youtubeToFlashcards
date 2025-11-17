#!/usr/bin/env python3
"""
summarize_flashcards_anki.py (Google Gemini + Mistral selectable)
------------------------------------------------------------------
Generates atomic Anki flashcards from lecture text.
Default provider: Google.
Supports playlist subfolders.
"""

import os
import time
import json
import random
from pathlib import Path
from dotenv import load_dotenv
from typing import Literal

# Providers
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    genai = None
    HarmCategory = None
    HarmBlockThreshold = None

try:
    from mistralai.client import MistralClient as Mistral
    from mistralai.models.chat_completion import ChatMessage
    from mistralai.models.sdkerror import SDKError
except ImportError:
    Mistral = None
    ChatMessage = None
    SDKError = Exception

load_dotenv()

DEFAULT_PROVIDER: Literal["google", "mistral"] = "google"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not GOOGLE_API_KEY and not MISTRAL_API_KEY:
    raise ValueError("No GOOGLE_API_KEY or MISTRAL_API_KEY found.")

# ---------------------------------------------------------------
# Provider initialization
# ---------------------------------------------------------------

def init_google():
    if not genai:
        raise ImportError("google-generativeai not installed. Install with: pip install google-generativeai")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(
        "gemini-2.5-pro",
        safety_settings={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    )
    return model

def init_mistral():
    if not Mistral:
        raise ImportError("mistralai not installed.")
    return Mistral(api_key=MISTRAL_API_KEY), "mistral-large-latest"

# ---------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------

def call_llm_with_retry(prompt, provider, max_retries=5, base_delay=5):
    for attempt in range(1, max_retries + 1):
        try:
            if provider == "google":
                model = init_google()
                response = model.generate_content(prompt)
                if not response.candidates:
                    raise RuntimeError("Google API returned no candidates")
                return response.text.strip()
            elif provider == "mistral":
                client, model_name = init_mistral()
                messages = [ChatMessage(role="user", content=prompt)]
                response = client.chat(model=model_name, messages=messages)
                return response.choices[0].message.content.strip()
            else:
                raise ValueError(f"Unknown provider: {provider}")
        except Exception as e:
            wait_time = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            print(f"[!] Attempt {attempt} failed: {e}. Retrying in {wait_time:.1f}s")
            time.sleep(wait_time)
            if attempt == max_retries:
                raise RuntimeError(f"Maximum retries exceeded: {e}")

# ---------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------

def load_sanitized_title(title_json: Path) -> str:
    if not title_json.exists():
        raise FileNotFoundError(f"Title JSON file not found: {title_json}")
    with open(title_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    title = data.get("title")
    if not title:
        raise ValueError(f"No 'title' field in {title_json}")
    return title

def determine_output_path(output_dir: Path, title: str, playlist_folder: str | None = None) -> Path:
    if playlist_folder:
        output_dir = output_dir / playlist_folder
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{title}.txt"

def deduplicate_flashcards(raw: str) -> str:
    seen = set()
    out_lines = []
    for line in raw.splitlines():
        norm = line.strip()
        if norm and norm not in seen:
            out_lines.append(line)
            seen.add(norm)
    return "\n".join(out_lines)

# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate atomic Anki flashcards using Google or Mistral.")
    parser.add_argument("input_file")
    parser.add_argument("--title_json", default="currentTitle.json")
    parser.add_argument("--outdir", default="flashcardTxt")
    parser.add_argument("--provider", choices=["google", "mistral"], default=DEFAULT_PROVIDER)
    parser.add_argument("--playlist_folder", default=None, help="Optional playlist folder name")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    title = load_sanitized_title(Path(args.title_json))
    output_path = determine_output_path(Path(args.outdir), title, args.playlist_folder)

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        raise ValueError(f"{input_path} is empty")

    delimiter = "||DELIM||"
    prompt = f"""
You are an expert at creating high-quality Anki flashcards from lecture notes.

- Generate flashcards strictly in this format:
  Question{delimiter}Answer
- Use exactly '{delimiter}' between question and answer.
- Each flashcard must test only one fact, concept, or relationship (atomic fact).
- Include all essential information from the text, without omissions.
- Always include the full name of any Greek person mentioned.
- Avoid redundancy, trivial details, commentary, or explanations.
- No prefixes like 'Q:' or 'A:'.
- Each flashcard must be a single line.
- Use <b>bold</b> for key terms and <i>italics</i> for definitions.
- Avoid duplicates; split overly long answers.
- Clarify pronouns.
- Output ONLY flashcards.
- Skip any unnecessary information about the course like the instructor and course materials
- Skip sponsored segments and self-promotion of the channel and creator
Text to process:
{text}
"""

    print(f"[+] Generating flashcards using {args.provider}...")
    raw_cards = call_llm_with_retry(prompt, provider=args.provider)
    deduped = deduplicate_flashcards(raw_cards)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(deduped)

    print(f"[+] Saved to {output_path}")

if __name__ == "__main__":
    main()
