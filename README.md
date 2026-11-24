# WordClip Studio

WordClip Studio creates vertical English-learning videos (9:16) through GitHub Pages and GitHub Actions. The browser UI runs on a phone; GitHub Actions performs image search, voice generation, rendering, quality checks and Release publishing.

## Learning modes

Choose one mode and a CEFR level (A1, A2, B1, or Mixed) before creating a video:

- **Object Learning** — identify a photographed object.
- **Action Learning** — describe an action shown by a person.
- **Useful Vocabulary** — learn a word, short meaning and example.
- **Everyday Phrases** — learn a practical expression for a real situation.

Modes are kept separate. A successful build records stable item IDs in a history file for that mode, so an item is not offered again in that mode. An unsuccessful build does not consume the items.

Automatic selection is the default: Prepare gathers suitable candidates, chooses the highest-ranked available photo for each item, then starts Build. Enable **Manual review** to inspect and choose photos yourself.

## Setup

Follow `SETUP_BN.md` for the full phone-friendly GitHub setup. Add secrets in **Repository Settings → Secrets and variables → Actions**; do not commit secret values:

- `PIXABAY_API_KEY`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Cloudflare Workers AI is used for photo relevance checking and optional arrow placement when configured. Without a working vision provider, the app can still rank candidates from Pixabay metadata, but those images are not AI-verified. GitHub Actions also needs repository workflow permissions set to **Read and write**.

## Word source and images

The curated mode-specific learning bank is the default word source. The old 1,300-item photo-focused list remains archived in `engine/wordbank.py`; only an explicit allowlist of practical legacy objects is added to Object Learning. The old AI word generator remains in the code but is disabled by default (`allow_ai_word_generation: false` in `config.yaml`). It is retained as a legacy opt-in for Object Learning only. CEFR levels are approximate learning targets, not official exam-list classifications.

Images are searched from Pixabay during Prepare. The project does not maintain a permanent image bank or bulk-download the whole vocabulary. Pixabay search-response metadata is cached in the `state` branch for the required 24-hour window; rendered source images are downloaded only for a build and temporary work files are removed afterward. Photo credits are included in Release notes and `credits.json`.

## Developer checks

```bash
python -m py_compile engine/*.py
python -m unittest discover -s tests -p 'test_learning_modes.py' -v
python -m unittest discover -s tests -p 'test_v6.py' -v
node --test tests/test_core.js
```

Run the full suite with `python -m unittest discover -s tests -v`. A real build also depends on valid GitHub, Pixabay, voice and (optionally) vision credentials; mock tests do not verify live provider access.

## Main folders

- `docs/` — static mobile web app.
- `engine/` — Python prepare, image, voice, audio and video pipeline.
- `.github/workflows/` — GitHub Actions entry points.
- `engine/learning_bank.py` — mode-specific content and CEFR levels.
- `engine/state.py` — persistent history, sessions and API metadata cache.
- `tests/` — Python and browser-core tests.
