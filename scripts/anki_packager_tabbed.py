#!/usr/bin/env python3
"""
anki_packager_tabbed.py
-----------------------
Reads a delimiter-separated flashcard file (Question||DELIM||Answer format)
and creates a formatted .apkg Anki deck with HTML rendering.
Outputs decks to the `apkg/` directory using the sanitized YouTube title.
"""

import os
import re
import json
from pathlib import Path
import genanki

# Fonts (update paths if needed)
FONT_BOLD = "/usr/share/fonts/gontserrat/Gontserrat-Bold.ttf"
FONT_LIGHT = "/usr/share/fonts/gontserrat/Gontserrat-Light.ttf"

DELIMITER = "||DELIM||"

def markdown_to_html(text: str) -> str:
    """Convert **bold** and *italic* Markdown to HTML."""
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    return text.strip()

def parse_flashcards(file_path: Path):
    """Parse flashcards using a unique delimiter and normalize whitespace."""
    flashcards = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if DELIMITER not in line:
                continue  # skip malformed lines
            q, a = [part.strip().replace("\n", " ") for part in line.split(DELIMITER, 1)]
            if q and a:
                flashcards.append((markdown_to_html(q), markdown_to_html(a)))
    print(f"[+] Parsed {len(flashcards)} valid flashcards from {file_path}")
    return flashcards

def load_sanitized_title(title_json: Path) -> str:
    """Load sanitized YouTube title from JSON file and convert to readable deck name."""
    if not title_json.exists():
        raise FileNotFoundError(f"Title JSON file not found: {title_json}")
    with open(title_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    title = data.get("title")
    if not title:
        raise ValueError(f"No 'title' field found in {title_json}")
    # Replace underscores with spaces and title-case
    title_readable = title.replace("_", " ").strip()
    title_readable = " ".join(word.capitalize() if not word.isupper() else word for word in title_readable.split())
    return title_readable

def determine_output_path(outdir: Path, title: str) -> Path:
    """Determine output path for the .apkg file using sanitized title (underscores only)."""
    safe_filename = re.sub(r'[^\w\- ]', '', title).replace(" ", "_")
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir / f"{safe_filename}.apkg"

def create_anki_deck(input_file: Path, title_json: Path, outdir: Path = Path("apkg")):
    """Build and export an Anki deck using sanitized title."""
    title = load_sanitized_title(title_json)
    flashcards = parse_flashcards(input_file)
    if not flashcards:
        raise ValueError("No valid flashcards found — check your input file formatting.")

    deck_id = abs(hash(title)) % (10**10)
    deck = genanki.Deck(deck_id, title)  # Deck name is readable

    model = genanki.Model(
        deck_id + 1,
        'Q&A Model',
        fields=[{'name': 'Question'}, {'name': 'Answer'}],
        templates=[{
            'name': 'Card 1',
            'qfmt': '<div class="question">{{Question}}</div>',
            'afmt': '{{FrontSide}}<hr id="answer"><div class="answer">{{Answer}}</div>'
        }],
        css=f"""
        @font-face {{
            font-family: 'Gontserrat';
            src: url('{FONT_BOLD}') format('truetype');
            font-weight: 700;
        }}
        @font-face {{
            font-family: 'Gontserrat';
            src: url('{FONT_LIGHT}') format('truetype');
            font-weight: 300;
        }}
        .card {{
            font-family: 'Gontserrat', 'Arial', sans-serif;
            background-color: #F4F1FA;
            text-align: center;
            line-height: 1.6;
            padding: 25px;
            border-radius: 20px;
            box-shadow: 0 0 15px rgba(90, 24, 154, 0.2);
        }}
        .question {{ font-weight:700; font-size:22px; color:#8C5DA7; margin-bottom:15px; }}
        .answer {{ font-weight:300; font-size:18px; color:#B89FE6; }}
        b {{ color:#B89FE6; font-weight:700; }}
        i {{ color:#C9ACF0; font-style:italic; }}
        hr {{ margin:20px auto; width:50%; border:0; height:2px; background-color:#D6C1FF; opacity:0.7; }}
        """
    )

    for q, a in flashcards:
        note = genanki.Note(model=model, fields=[q, a])
        deck.add_note(note)

    output_path = determine_output_path(outdir, title)
    genanki.Package(deck).write_to_file(output_path)
    print(f"[+] Created Anki deck: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=f"Create an Anki .apkg deck from a flashcard file using '{DELIMITER}' as delimiter.")
    parser.add_argument("input_file", help="Path to flashcard text file (Question||DELIM||Answer format)")
    parser.add_argument("--title_json", default="currentTitle.json", help="Path to JSON containing sanitized title")
    parser.add_argument("--outdir", default="apkg", help="Directory to save .apkg deck")
    args = parser.parse_args()

    create_anki_deck(Path(args.input_file), Path(args.title_json), Path(args.outdir))
