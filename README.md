---

# YouTube → Anki Flashcards Pipeline

A full end-to-end system that converts YouTube videos—or entire playlists—into structured, styled Anki flashcard decks.
The pipeline retrieves transcripts, preprocesses them into clean chunks, summarizes them using LLMs, converts those summaries into flashcards, and packages everything into ready-to-import `.apkg` decks.

The system supports **Google Generative AI**, **Mistral AI**, or both, with **Google as the default** (ideal for handling rate limits).

---

## Features

### 🟣 Transcript Acquisition

* Fetches YouTube transcripts automatically.
* Supports multiple languages.
* Handles IDs beginning with hyphens (`-`), Windows paths, and playlist extraction.
* Optional cookies for authenticated, region-locked, or age-restricted videos.

### 🟣 Transcript Preprocessing

* Normalizes and merges short segments.
* Produces coherent, LLM-ready text chunks.
* Deterministic and reproducible preprocessing.

### 🟣 Dual-Model Summarization Layer

* Fully supports **Google Generative AI** (default).
* Fully supports **Mistral AI** (fallback or optional).
* Automatic rate-limit handling if both providers are configured.
* Environment-variable–based provider selection.

### 🟣 Flashcard Generation

* Converts summaries into atomic, high-fidelity flashcards.
* HTML-styled output using:

  * bold question headers
  * centered, lighter answer styling
  * custom font support (Gontserrat, purple accents)

### 🟣 Packaging

* Generates `.apkg` decks automatically.
* Supports:

  * single-video decks
  * playlist-wide hierarchical decks (one subdeck per video)
* Compatible with all Anki desktop versions.

### 🟣 Windows-Friendly

* All scripts accept IDs with `-` via the `--` delimiter.
* Backslashes and Windows paths handled cleanly across the pipeline.

---

## Requirements

### Software

* **Python 3.10–3.13**
* A virtual environment is strongly recommended.

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

Set any combination of:

```bash
GOOGLE_API_KEY=<your_google_key>   # Default summarization model
MISTRAL_API_KEY=<your_mistral_key> # Optional fallback or explicit use
```

If both keys are present, the system uses Google by default unless instructed otherwise.

---

## Installation Guide

1. Clone the repository:

```bash
git clone <repo_url>
cd youtubeToFlashcards
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/macOS
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file (optional but recommended):

```
GOOGLE_API_KEY=your_google_key
MISTRAL_API_KEY=your_mistral_key
```

---

## Usage

### Single Video

```bash
python pipeline.py --video "https://www.youtube.com/watch?v=abcdEFGhijk"
```

### Playlist Processing

```bash
python pipeline.py --playlist "https://youtube.com/playlist?list=YOUR_ID"
```

### Process only a subset of a playlist

```bash
python pipeline.py --playlist <url> --playlist_start 10 --playlist_end 15
```

### Using Cookies (optional)

```bash
python pipeline.py --video <id> --cookies cookies.txt
```

### Using Mistral instead of Google

```bash
USE_MISTRAL=1 python pipeline.py --video <id>
```

---

## Output Structure

All generated files are fully organized:

```
transcripts/
    <title>_transcript.json

reduced/
    <title>_transcript_reduced.txt

summaries/
    <title>/
        full_summary.txt

flashcardTxt/
    <title>.txt

apkg/
    <title>.apkg
    <playlist_name>.apkg   # hierarchical deck
```

---

## Notes

* All long-running stages support retry logic for stability.
* Windows users do **not** need to escape video IDs beginning with hyphens; the pipeline safely passes them using `--`.
* The Anki packager embeds HTML formatting and custom styles.
* Model provider selection is transparent and environment-driven.

---

## Customization

### Chunking parameters

`reduce_transcript.py` allows custom word lengths.

### Model selection

`llm.py` includes the logic for:

* provider switching
* rate-limit fallback
* temperature, token limits, etc.

### Deck Formatting

Modify CSS and field templates in `anki_packager_tabbed.py`.

---

## To-Do (Roadmap)

* Improved structured logging across all stages.
* Rich terminal monitoring with timing and profiling.
* Web-based UI for end-users.
* Real-time progress bars for summarization.
* Parallelization for playlists (LLM-friendly throttling).
* Error recovery for partial playlist failures.
* Automatic detection of manual vs. AI titles.

---

## License

MIT License — free to use, modify, and distribute.

---
