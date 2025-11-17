#!/usr/bin/env python3
"""
anki_packager_tabbed.py
-----------------------
Reads delimiter-separated flashcards (Question||DELIM||Answer) and creates
formatted Anki decks. Supports hierarchical decks for playlists:
each video can become a subdeck under the playlist deck.
"""

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
    """Parse flashcards using the unique delimiter."""
    flashcards = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or DELIMITER not in line:
                continue
            q, a = [part.strip().replace("\n", " ") for part in line.split(DELIMITER, 1)]
            if q and a:
                flashcards.append((markdown_to_html(q), markdown_to_html(a)))
    print(f"[+] Parsed {len(flashcards)} valid flashcards from {file_path}")
    return flashcards

def load_title(title_json: Path) -> str:
    """Load sanitized YouTube title from JSON for deck name."""
    if not title_json.exists():
        raise FileNotFoundError(f"Title JSON not found: {title_json}")
    with open(title_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    title = data.get("title")
    if not title:
        raise ValueError(f"No 'title' in {title_json}")
    title_readable = title.replace("_", " ").strip()
    title_readable = " ".join(w.capitalize() if not w.isupper() else w for w in title_readable.split())
    return title_readable

def create_model(deck_id: int) -> genanki.Model:
    """Create a Q&A model with HTML formatting."""
    return genanki.Model(
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
            font-family: 'Gontserrat', Arial, sans-serif;
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

def create_deck(flashcards_file: Path, title: str, deck_name: str = None) -> genanki.Deck:
    """Create a single Anki deck or subdeck."""
    deck_id = abs(hash(deck_name or title)) % (10**10)
    deck = genanki.Deck(deck_id, deck_name or title)
    model = create_model(deck_id)
    flashcards = parse_flashcards(flashcards_file)
    for q, a in flashcards:
        deck.add_note(genanki.Note(model=model, fields=[q, a]))
    return deck

def write_package(decks: list[genanki.Deck], outdir: Path, filename: str):
    """Write multiple decks into one .apkg (supports hierarchical decks)."""
    outdir.mkdir(parents=True, exist_ok=True)
    # Use a single package and assign decks via decks attribute
    pkg = genanki.Package()
    pkg.decks = decks
    pkg.write_to_file(outdir / filename)
    print(f"[+] Created .apkg: {outdir / filename}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create Anki deck(s) from flashcards")
    parser.add_argument("--input_file", action="append", help="Flashcard file(s) (Question||DELIM||Answer)")
    parser.add_argument("--title_json", default="currentTitle.json", help="JSON with sanitized title")
    parser.add_argument("--subdeck_title", action="append", help="Subdeck title (for playlist hierarchical decks)")
    parser.add_argument("--playlist_name", help="Playlist deck name for hierarchical decks")
    parser.add_argument("--outdir", default="apkg")
    args = parser.parse_args()

    decks = []
    if args.playlist_name and args.input_file and args.subdeck_title:
        # Create hierarchical decks
        for fc_file, sub_title in zip(args.input_file, args.subdeck_title):
            decks.append(create_deck(Path(fc_file), sub_title, deck_name=f"{args.playlist_name}::{sub_title}"))
        write_package(decks, Path(args.outdir), f"{args.playlist_name}.apkg")
    elif args.input_file:
        # Single deck
        decks.append(create_deck(Path(args.input_file[0]), load_title(Path(args.title_json))))
        write_package(decks, Path(args.outdir), f"{load_title(Path(args.title_json))}.apkg")
    else:
        raise ValueError("No input files provided")
