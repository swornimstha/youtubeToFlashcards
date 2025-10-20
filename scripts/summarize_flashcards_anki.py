#!/usr/bin/env python3
"""
summarize_flashcards_anki.py
----------------------------
Generates atomic Anki flashcards from lecture text using Mistral,
preserves details and bold/italic formatting, and deduplicates repeated cards.
Saves output under flashcardTxt/<sanitized_title>.txt
"""

import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.models.sdkerror import SDKError

# Load environment variables
load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    raise ValueError("MISTRAL_API_KEY not found in environment variables")

MODEL = "mistral-large-latest"
client = Mistral(api_key=API_KEY)

def call_mistral_with_retry(prompt, max_retries=5, base_delay=5):
    """Call Mistral API with linear backoff for rate limits."""
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.complete(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except SDKError as e:
            if "429" in str(e):
                wait_time = base_delay * attempt
                print(f"[!] Rate limit hit. Waiting {wait_time}s before retry (attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise e
    raise RuntimeError("Exceeded maximum retries due to repeated rate-limit errors.")

def load_sanitized_title(title_json: Path) -> str:
    """Load sanitized YouTube title from JSON file."""
    if not title_json.exists():
        raise FileNotFoundError(f"Title JSON file not found: {title_json}")
    with open(title_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    title = data.get("title")
    if not title:
        raise ValueError(f"No 'title' field found in {title_json}")
    return title

def determine_output_path(output_dir: Path, title: str) -> Path:
    """Determine output path for flashcard text file using sanitized title."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{title}.txt"

def deduplicate_flashcards(raw_flashcards: str) -> str:
    """Remove duplicate flashcards while preserving order."""
    seen = set()
    deduped_lines = []
    for line in raw_flashcards.splitlines():
        normalized = line.strip()
        if normalized and normalized not in seen:
            deduped_lines.append(line)
            seen.add(normalized)
    return "\n".join(deduped_lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate atomic Anki flashcards from text using Mistral.")
    parser.add_argument("input_file", help="Path to input text file")
    parser.add_argument("--title_json", default="currentTitle.json",
                        help="Path to JSON containing sanitized title")
    parser.add_argument("--outdir", default="flashcardTxt",
                        help="Directory to save flashcard text files")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    title = load_sanitized_title(Path(args.title_json))
    output_path = determine_output_path(Path(args.outdir), title)

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
- Each flashcard must test only one fact, concept, or relationship (atomic fact). Do not combine multiple facts in one card.
- Include all essential information from the text, without omissions.
- Always include the full name of any Greek person mentioned when referring to them.
- Avoid redundancy, trivial details, commentary, examples, explanations, or introductions.
- Do NOT use 'Q:' or 'A:' prefixes, extra characters, or punctuation beyond natural usage.
- Each flashcard must be a single line: the question, immediately followed by '{delimiter}', then the answer.
- Do NOT insert bullet points, numbering, or line breaks within the question or answer.
- Answers should be concise, fully self-contained, and understandable without external context.
- For important terms, names, or concepts, wrap them in HTML <b>bold</b> tags; for definitions or emphasized phrases, use <i>italics</i>.
- Prefer short, high-impact sentences; split overly long answers into multiple atomic cards if needed.
- Merge similar facts into a single card where appropriate; avoid generating duplicates.
- Clarify pronouns or vague references; always specify who or what is being referred to.
- Output ONLY flashcards, one per line, no extra text, no headers, separators, or commentary.
- Use high-school-level vocabulary.
- Emphasize on having a question and answer instead of two statements
Text to process:
{text}
"""
    print(f"[+] Generating flashcard content from {input_path.name}...")
    raw_flashcards = call_mistral_with_retry(prompt)

    deduped_flashcards = deduplicate_flashcards(raw_flashcards)

    # Save the deduplicated flashcards
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(deduped_flashcards)

    print(f"[+] Deduplicated flashcard content saved to {output_path}")

if __name__ == "__main__":
    main()
