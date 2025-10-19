#!/usr/bin/env python3
"""
anki_packager_tabbed.py
-----------------------
Reads a tab-separated flashcard file (Question<TAB>Answer format)
and creates a formatted .apkg Anki deck with HTML rendering.
"""

import os
import re
from pathlib import Path
import genanki

# Paths to your Gontserrat fonts (update if needed)
FONT_BOLD = "/usr/share/fonts/gontserrat/Gontserrat-Bold.ttf"
FONT_LIGHT = "/usr/share/fonts/gontserrat/Gontserrat-Light.ttf"

def markdown_to_html(text: str) -> str:
    """Convert **bold** and *italic* Markdown to HTML."""
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    return text.strip()

def parse_tab_flashcards(file_path: Path):
    """Parse tab-separated question-answer pairs, skip invalid lines."""
    flashcards = []
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                print(f"[!] Skipping invalid line {i}: {line}")
                continue
            q, a = parts[0].strip(), parts[1].strip()
            if q and a:
                flashcards.append((markdown_to_html(q), markdown_to_html(a)))
    print(f"[+] Parsed {len(flashcards)} valid flashcards from {file_path}")
    return flashcards

def create_anki_deck(input_file: Path, deck_name: str):
    """Build and export an Anki deck."""
    flashcards = parse_tab_flashcards(input_file)
    if not flashcards:
        raise ValueError("No valid flashcards found — check your input file formatting.")

    deck_id = abs(hash(deck_name)) % (10**10)
    deck = genanki.Deck(deck_id, deck_name)

    model = genanki.Model(
        deck_id + 1,
        'Tabbed Q&A Model',
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
            font-family: 'Gontserrat', sans-serif;
            background-color: #F4F1FA;
            text-align: center;
            line-height: 1.6;
            padding: 25px;
            border-radius: 20px;
            box-shadow: 0 0 15px rgba(90, 24, 154, 0.2);
        }}

        .question {{
            font-weight: 700;
            font-size: 22px;
            color: #8C5DA7;
            margin-bottom: 15px;
        }}

        .answer {{
            font-weight: 300;
            font-size: 18px;
            color: #B89FE6;
        }}

        b {{ color: #B89FE6; font-weight: 700; }}
        i {{ color: #C9ACF0; font-style: italic; }}

        hr {{
            margin: 20px auto;
            width: 50%;
            border: 0;
            height: 2px;
            background-color: #D6C1FF;
            opacity: 0.7;
        }}
        """
    )

    for q, a in flashcards:
        note = genanki.Note(model=model, fields=[q, a])
        deck.add_note(note)

    output_path = input_file.with_suffix(".apkg")
    genanki.Package(deck).write_to_file(output_path)
    print(f"[+] Created Anki deck: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create an Anki .apkg deck from a tab-separated flashcard file.")
    parser.add_argument("input_file", help="Path to your flashcard text file (Question<TAB>Answer format)")
    parser.add_argument("--name", help="Deck name (defaults to filename stem)", default=None)
    args = parser.parse_args()

    input_path = Path(args.input_file)
    deck_name = args.name or input_path.stem
    create_anki_deck(input_path, deck_name)
