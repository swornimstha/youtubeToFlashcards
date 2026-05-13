#!/usr/bin/env python3
"""
summarize_flashcards_anki.py
----------------------------
Generates high-quality atomic Anki flashcards using Gemini
with Mistral Large as a robust fallback via REST API.
"""

import os
import time
import json
import urllib.request
import argparse
from pathlib import Path
from dotenv import load_dotenv

# SDKs
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Model Configuration
GOOGLE_MODEL = "gemma-4-31b-it" 
MISTRAL_MODEL = "mistral-large-latest"
DELIMITER = "||DELIM||"

def get_anki_prompt(text: str) -> str:
    """Combines SRS principles with strict formatting rules."""
    return f"""
You are a specialist in Cognitive Science and Spaced Repetition (SRS). Transform this transcript into Anki cards.

### RULES
1. ATOMICITY: Each card must test a SINGLE memory trace. No 'and' or bullet points in answers.
2. CONTRAST: If two concepts are similar, create a 'Contrast Card' highlighting the difference.
3. CAUSALITY: Prioritize 'Why' and 'How' over simple 'What' definitions.
4. NO PRONOUNS: Every question must be a standalone unit. Replace 'it/this/that' with the Subject Name.
5. NOISE FILTER: Ignore logistics and sponsorships. Keep only permanent knowledge.

### FORMATTING
- Format: Question{DELIMITER}Answer
- Styling: <b>Bold</b> for key subjects; <i>Italics</i> for core answers.
- Formatting: No 'Q:' or 'A:' prefixes. One card per line.

Text to process:
{text}
"""

def call_google_api(prompt: str) -> str:
    """Primary: Use Google GenAI SDK."""
    if not GOOGLE_API_KEY:
        raise ConnectionError("Google API Key missing.")
    
    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    # Safety settings to ensure educational content isn't blocked
    safety = [
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    ]

    response = client.models.generate_content(
        model=GOOGLE_MODEL, 
        contents=prompt,
        config=types.GenerateContentConfig(safety_settings=safety, temperature=0.3)
    )
    return response.text.strip()

def call_mistral_api(prompt: str, max_retries=3) -> str:
    """Fallback: Use Mistral REST API directly to bypass SDK cache issues."""
    if not MISTRAL_API_KEY:
        raise ConnectionError("Mistral API Key missing.")
    
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    data = {
        "model": MISTRAL_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            if "429" in str(e) and attempt < max_retries:
                wait = 5 * attempt
                print(f"    [!] Mistral Rate Limit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise e
    return ""

def deduplicate_flashcards(raw_flashcards: str) -> str:
    """Remove duplicates and ensure delimiter integrity."""
    seen = set()
    deduped_lines = []
    for line in raw_flashcards.splitlines():
        normalized = line.strip()
        if normalized and normalized not in seen and DELIMITER in normalized:
            deduped_lines.append(normalized)
            seen.add(normalized)
    return "\n".join(deduped_lines)

def main():
    parser = argparse.ArgumentParser(description="Generate Anki cards with Google/Mistral fallback.")
    parser.add_argument("input_file", help="Path to input text file")
    parser.add_argument("--title_json", default="currentTitle.json", help="Ignored, kept for pipeline compatibility")
    parser.add_argument("--outdir", default="flashcardTxt")
    parser.add_argument("--playlist_folder", default=None, help="Optional subfolder for playlists")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    
    # Extract the title directly from the folder name containing full_summary.txt
    title = input_path.parent.name
    
    # Determine output path
    output_dir = Path(args.outdir)
    if args.playlist_folder:
        output_dir = output_dir / args.playlist_folder
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{title}.txt"

    if not input_path.exists():
        print(f"[!] Input file {input_path} does not exist.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    
    if not text:
        print("[!] Input file is empty.")
        return

    print(f"[+] Generating cards for: {title}")
    prompt = get_anki_prompt(text)
    
    raw_content = ""
    try:
        print("    [~] Attempting Google (Gemini)...")
        raw_content = call_google_api(prompt)
    except Exception as e:
        print(f"    [!] Google failed: {e}")
        print("    [~] Falling back to Mistral...")
        try:
            raw_content = call_mistral_api(prompt)
        except Exception as e2:
            print(f"    [CRITICAL] All APIs failed: {e2}")
            return

    if raw_content:
        final_cards = deduplicate_flashcards(raw_content)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_cards)
        print(f"[SUCCESS] {len(final_cards.splitlines())} cards saved to {output_path}")

if __name__ == "__main__":
    main()
