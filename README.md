---

# YouTube → Anki Flashcards Pipeline

A complete pipeline to convert YouTube videos into structured Anki flashcards. This system fetches transcripts, preprocesses them, summarizes content using Mistral AI, and generates HTML-styled flashcards packaged into an import-ready Anki `.apkg` deck.

---

## Features

* **YouTube Transcript Fetching**: Retrieve transcripts in multiple languages.
* **Transcript Reduction**: Merge short segments into coherent, LLM-ready chunks.
* **Chunk Summarization**: Summarize each chunk individually with Mistral AI, preserving clarity, accuracy, and completeness.
* **Anki Flashcard Generation**: Convert summaries into atomic question–answer flashcards.
* **HTML Formatting**: Questions are bold and prominent; answers are lighter, centered, and styled with Gontserrat fonts and purple accents.
* **Automatic Packaging**: Outputs a ready-to-import `.apkg` Anki deck.

---

## Requirements

* **Python** 3.13+
* **Virtual Environment** recommended (`python -m venv .venv`)
* **Dependencies**:

```bash
pip install -r requirements.txt
```

* **Environment variables**:

```bash
MISTRAL_API_KEY=<your_mistral_api_key>
```

---

## Installation

1. Clone the repository:

```bash
git clone <repo_url>
cd youtubeToFlashcards
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set your Mistral API key in `.env`:

```
MISTRAL_API_KEY=your_key_here
```

---

## Usage

Run the master pipeline:

```bash
python pipeline.py <YOUTUBE_VIDEO_URL_OR_ID>
```

**Example**:

```bash
python pipeline.py https://www.youtube.com/watch?v=bqsXWmZHcFQ
```

This performs the following steps:

1. Fetch the transcript.
2. Reduce and chunk the transcript for summarization.
3. Summarize each chunk.
4. Generate Anki-ready flashcards.
5. Package the flashcards into an `.apkg` deck.

**Outputs**:

* `transcripts/<sanitized_title>_transcript.json`
* `reduced/<sanitized_title>_transcript_reduced.txt`
* `summaries/<sanitized_title>/full_summary.txt`
* `flashcardTxt/<sanitized_title>.txt`
* `apkg/<sanitized_title>.apkg`

---

## Notes

* The summarization step includes **retry logic** for reliability. Failed chunks are retried up to three times.
* Flashcards are **HTML-formatted** for enhanced readability in Anki.
* Adjust **Gontserrat font paths** in `anki_packager_tabbed.py` based on your system.

---

## Customization

* **Chunk size**: Modify the `--words` argument in `reduce_transcript.py`.
* **Summarization model**: Change `MODEL_NAME` in `llm.py`.
* **Deck appearance**: Adjust CSS in `anki_packager_tabbed.py`.

---

## To-Do

* Add logging for each video and pipeline stage.
* Support batch processing of playlists.
* Enhance chunk retry and error handling.
* Improve deck naming with auto-sanitized titles.

---

## License

MIT License — free to use, modify, and distribute.

---
