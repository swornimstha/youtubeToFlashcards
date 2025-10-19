
#!/usr/bin/env python3
"""
summarize_flashcards_anki.py
----------------------------
Converts lecture text into Anki-ready tab-separated flashcards.
Questions are bold, answers are lighter in color.
Handles Mistral API rate limits automatically.
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.models.sdkerror import SDKError
import html

# Load environment variables
load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    raise ValueError("MISTRAL_API_KEY not found in environment variables")

MODEL = "mistral-small-latest"
client = Mistral(api_key=API_KEY)

def call_mistral_with_retry(prompt, max_retries=5, base_delay=5):
    """Call Mistral API with exponential backoff for rate limits."""
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

def format_flashcards(raw_flashcards: str) -> str:
    """Convert tab-separated flashcards to HTML-enhanced version for Anki."""
    lines = raw_flashcards.strip().splitlines()
    formatted = []
    for line in lines:
        if "\t" not in line:
            continue
        q, a = line.split("\t", 1)
        q_html = f"<b>{html.escape(q)}</b>"
        a_html = f"<span style='font-weight:300;color:#B89FE6'>{html.escape(a)}</span>"
        formatted.append(f"{q_html}\t{a_html}")
    return "\n".join(formatted)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate Anki-ready flashcards from text using Mistral.")
    parser.add_argument("input_file", help="Path to input text file")
    parser.add_argument("--output", default="anki_flashcards.txt", help="Output file to save flashcards")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output)

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        raise ValueError(f"{input_path} is empty")

    # Prompt tuned for Anki Basic format
    prompt = f"""
You are an expert at creating high-quality Anki flashcards from lecture notes.

Your task:
- Create clear, high-school-level flashcards in this format:
  Question<TAB>Answer
- Each flashcard should test one idea only.
- Include every important concept and relationship from the text.
- Avoid redundancy or trivia.
- Do NOT include 'Q:' or 'A:' prefixes.
- Separate each flashcard with a newline.

Text to process:
{text}
"""

    print(f"[+] Generating Anki-style flashcards from {input_path.name}...")
    raw_flashcards = call_mistral_with_retry(prompt)

    formatted_flashcards = format_flashcards(raw_flashcards)

    # Save in tab-separated Anki format with HTML
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(formatted_flashcards)

    print(f"[+] Flashcards saved to {output_path}")
    print("[!] You can now import this file into Anki (Basic note type, tab-separated, HTML enabled).")

if __name__ == "__main__":
    main()
