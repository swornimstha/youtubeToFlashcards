# YouTube to Anki Flashcards Pipeline

This repository provides a complete pipeline to convert YouTube videos into structured Anki flashcards. It fetches transcripts, preprocesses them, summarizes content using Mistral AI, and generates HTML-formatted flashcards packaged into an Anki `.apkg` deck.

---

## Features

- **YouTube Transcript Fetching**: Retrieves transcripts in multiple languages.
- **Transcript Reduction**: Merges short segments into coherent, LLM-ready chunks.
- **Chunk Summarization**: Summarizes each chunk individually using Mistral AI, ensuring clarity and completeness.
- **Anki Flashcard Generation**: Converts summaries into tab-separated question-answer flashcards.
- **HTML Formatting**: Questions are bold and large; answers are lighter, centered, and styled with Gontserrat font and purple accents.
- **Automatic Packaging**: Outputs a ready-to-import `.apkg` Anki deck.

---

## Requirements

- Python 3.13+
- Virtual environment recommended (`python -m venv .venv`)
- Dependencies:

```bash
pip install -r requirements.txt
````

* Environment variables:

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

2. Activate virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set your API key in `.env`:

```
MISTRAL_API_KEY=your_key_here
```

---

## Usage

Run the master pipeline script:

```bash
python pipeline.py <YOUTUBE_VIDEO_ID>
```

**Example**:

```bash
python pipeline.py bqsXWmZHcFQ
```

This performs the following steps:

1. Fetch the transcript.
2. Reduce and chunk the transcript for summarization.
3. Summarize each chunk.
4. Generate Anki-ready flashcards.
5. Package the flashcards into an `.apkg` deck.

**Outputs**:

* `transcripts/<video_id>_transcript.json`
* `reduced/<video_id>_reduced.txt`
* `summaries/<video_id>_reduced/full_summary.txt`
* `flashcards/<video_id>_flashcards.txt`
* `flashcards/<video_id>_flashcards.apkg`

---

## Notes

* The summarization step includes retry logic for reliability. Failed chunks are retried up to three times.
* Flashcards are formatted in HTML for better readability in Anki.
* Adjust Gontserrat font paths in `anki_packager_tabbed.py` based on your system.

---

## Customization

* **Chunk size**: Modify `--words` argument in `reduce_transcript.py`.
* **Summarization model**: Change `MODEL_NAME` in `llm.py`.
* **Deck appearance**: Adjust CSS in `anki_packager_tabbed.py`.

---

## To-Do

- Add logging per video and pipeline stage.  
- Capture YouTube titles for deck/file naming.  
- Support full playlists, including large ones.  
- Improve chunk retry and error handling.  

---

## License

MIT License — free to use, modify, and distribute.

```
