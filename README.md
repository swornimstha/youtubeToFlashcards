---

# YouTube → Anki Flashcards Pipeline (V2)

A high-performance, modular system that transforms YouTube lectures and playlists into professional Anki decks. This version features advanced **Cognitive Science-driven prompting** and utilizes the latest **Gemma 4** models for superior flashcard quality.

The system uses a **Google-First, Mistral-Fallback** architecture, ensuring 99.9% reliability even when hitting API rate limits.

---

## 🚀 Key Improvements in V2

### 🧠 Cognitive Science SRS Engine

Unlike standard summaries, the new flashcard stage (`summarize_flashcards_anki.py`) enforces:

* **The Atomicity Rule**: One memory trace per card.
* **The Contrast Principle**: Automatic generation of cards that differentiate similar concepts.
* **The "Why" Over "What"**: Causal encoding that prioritizes logic over rote memorization.
* **The No-Pronoun Rule**: Every card is a standalone unit of knowledge.

### 🤖 Gemma 4 & Mistral Large Integration

* **Primary Model**: `gemma-4-31b-it` (Google GenAI) — Optimized for educational reasoning.
* **Fallback Model**: `mistral-large-latest` — Professional-grade fallback for high-volume playlist processing.
* **Safety Bypass**: Custom safety settings (`BLOCK_NONE`) to prevent educational/medical content from being flagged.

### 🐧 Linux & Cross-Platform Optimization

* **Divergent Branch Handling**: Full support for syncing between Windows and Linux environments.
* **zsh/bash Compatible**: Handles IDs starting with hyphens (`-`) using the `--` delimiter.
* **Headless Ready**: Optimized for terminal-only environments.

---

## 🟣 Workflow Stages

1. **Stage 1 (Fetch)**: Retrieves transcript JSON and sanitized titles via `yt-dlp`.
2. **Stage 2 (Reduce)**: Cleans filler text and merges fragments into coherent 600-word paragraphs.
3. **Stage 3 (Summarize)**: Generates high-school level explanations for every chunk of the lecture.
4. **Stage 4 (Flashcards)**: Applies SRS principles to the summaries to create `Question||DELIM||Answer` pairs.
5. **Stage 5 (Package)**: Injects CSS (Gontserrat fonts, purple accents) and creates `.apkg` files.

---

## 🛠 Installation

### 1. Clone & Setup

```bash
git clone <repo_url>
cd youtubeToFlashcards
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

```

### 2. Dependencies

```bash
pip install -r requirements.txt

```

### 3. Environment Configuration

Create a `.env` file in the root directory:

```bash
GOOGLE_API_KEY=your_google_genai_key
MISTRAL_API_KEY=your_mistral_key

```

---

## 📖 Usage

### Single Video

```bash
python pipeline.py --video "https://www.youtube.com/watch?v=VIDEO_ID"

```

### Entire Playlists (Hierarchical Decks)

The pipeline will create one master deck with each video as a sub-deck.

```bash
python pipeline.py --playlist "https://youtube.com/playlist?list=PLAYLIST_ID"

```

### Partial Playlist Sync

```bash
python pipeline.py --playlist <url> --playlist_start 5 --playlist_end 10

```

### Resume from Failure

If an API fails during the flashcard stage, you don't need to re-fetch the transcript:

```bash
python pipeline.py --video <id> --start_step 4

```

---

## 📁 Output Structure

```text
transcripts/   → Raw JSON data
reduced/       → Processed text chunks
summaries/     → Multi-chunk AI summaries
flashcardTxt/  → Raw Question||DELIM||Answer files
apkg/          → Final importable Anki Decks

```

---

## 🎨 UI & Styling

The generated cards feature a custom design:

* **Fonts**: Gontserrat Bold (Questions) & Light (Answers).
* **Color Palette**: Deep purple (`#8C5DA7`) headers with lavender (`#B89FE6`) accents.
* **Layout**: Centered, shadow-boxed cards with HTML formatting (`<b>`, `<i>`).

---

## 📜 License

MIT License — Free to use for personal education and open-source projects.

