# HANDOFF — WordClip Studio learning modes update

## Project state

This is an update to the existing WordClip Studio codebase. Existing rendering, Pixabay integration, vision checks, TTS fallback, release publishing, settings and manual photo tools are retained. This handoff describes the source in this ZIP; no GitHub push or deployment is included.

## Product behavior

The Home page now supports four separate learning modes:

1. `object` — Object Learning, with object naming question and target-word spelling.
2. `action` — Action Learning, with an action question and a complete present-continuous sentence.
3. `vocabulary` — Useful Vocabulary, with a meaning and example.
4. `phrases` — Everyday Phrases, with a practical conversational prompt and response.

Each mode supports `A1`, `A2`, `B1`, and `mixed` levels. The word bank is bundled in `engine/learning_bank.py`; data records include stable item ID, mode, level, image query/check target, question, spoken answer, slow target pronunciation, display label, spelling, Bengali meaning and example where applicable.

Automatic mode is the default. After Prepare returns candidates, `docs/app.js` selects the first photo from each candidate's ranked list and dispatches Build. The unchecked Manual review option preserves the existing screen for choosing/changing candidate photos. Object-topic filtering only applies to Object Learning.

## Word history

After a successful build only:

- `used_items/object.txt`
- `used_items/action.txt`
- `used_items/vocabulary.txt`
- `used_items/phrases.txt`

Skipped items are recorded separately under `bad_items/<mode>.txt`. Object mode also reads/writes legacy `used_words.txt` and `bad_words.txt` for compatibility with the earlier project. Build failures do not append used IDs.

## Pixabay behavior

- Pixabay remains the only stock-image provider.
- Search metadata responses are stored in `pixabay-cache/` on the `state` branch and reused for the required 24-hour cache window. The cache envelope stores `cached_at` explicitly, so a Git checkout cannot reset the cache age through file modification times.
- Cache stores metadata/URLs, not image bytes or API keys.
- The app does not pre-download the vocabulary bank or retain a permanent image bank.
- Build downloads selected image files into a temporary work directory; the directory is deleted after completion.
- Existing creator attribution and photo-page links remain in `credits.json` and Release notes.
- Candidate ranking keeps the person penalty for object searches but does not penalize people when the requested target itself is a person/action scenario.

Review the current official Pixabay API documentation before changing request rates, caching or image handling: https://pixabay.com/api/docs/ .

## Video / audio pipeline

`engine/render.WordRes` now carries separate question, answer text, slow pronunciation target, answer label, optional subtitle, spelling target, vision target and mode. Existing four-positional-argument WordRes construction remains compatible.

`engine/build.make_clips` renders the item-specific question, full answer and slow pronunciation separately. `engine/draw.build_label` can show a multi-line answer and optional meaning. `engine.render.Scene` uses a learning-mode heading. The countdown, answer reveal animation, spelling and visual sparkles remain. The answer-reveal `chime` and `sparkle` audio events were removed so they no longer overlap the first answer pronunciation; their visual counterparts and other SFX remain.

## AI word generator

The former AI word-generation path is preserved in `engine/words.py` and `engine/prepare.py`. It is disabled by default through `allow_ai_word_generation: false`. If explicitly enabled, it is only an Object Learning fallback. The four mode banks remain independent; the Action/Vocabulary/Phrases banks do not invoke AI word generation.

Vision AI remains a separate optional function for checking photo relevance and deciding arrow placement. If vision credentials/model are unavailable, the current pipeline continues with Pixabay's metadata ranking and emits a warning; an automatic run may therefore choose a less reliable visual match. Manual review should be used when image quality is uncertain.

## GitHub Actions inputs

Both workflow copies (`.github/workflows/prepare.yml` and `github-workflows/prepare.yml`) have `mode` and `level` inputs in addition to category/refill inputs. The Home UI sends the mode and level. Refill reads those values from the session's saved `candidates.json`, so it keeps the existing mode/level.

## Important files changed

- Added `engine/learning_bank.py`.
- Added `tests/test_learning_modes.py`.
- Updated `engine/prepare.py`, `engine/build.py`, `engine/render.py`, `engine/draw.py`, `engine/config.py`, `engine/pixabay.py`, `engine/vision.py`, `engine/timeline.py`, `engine/errors.py`.
- Updated `docs/app.js`, `docs/core.js`, workflows, tests and `config.yaml`.
- Added `README.md`, `.env.example` and this file.

## Local checks run

Run these commands in the repository root:

```bash
python -m py_compile engine/*.py
node --check docs/app.js
node --check docs/core.js
python -m unittest discover -s tests -p 'test_learning_modes.py' -v
python -m unittest discover -s tests -p 'test_v6.py' -v
python -m unittest discover -s tests -p 'test_engine.py' -k TimelineTests -v
python -m unittest discover -s tests -p 'test_engine.py' -k PrepareFlowTests -v
python -m unittest discover -s tests -p 'test_engine.py' -k WordBankTests -v
python -m unittest discover -s tests -p 'test_engine.py' -k PixabayTests -v
node --test tests/test_core.js
```

A real Pixabay search, actual Cloudflare/Groq/edge-tts calls, live GitHub Actions and a published Release were not executed in this environment. The full `test_engine.py` module did not complete within the available execution window; its focused timeline, Pixabay, prepare, word-bank, geometry, selection, audio, voice, state, and provider test groups were run individually. A full three-item MP4 render was not completed in this environment, so successful production video output still needs an Actions run with the project secrets.

## Known limitations / follow-up review

- Current bundled bank size: Object 211 (A1 79 / A2 108 / B1 24), Action 64 (28 / 25 / 11), Useful Vocabulary 49 (18 / 20 / 11), Everyday Phrases 42 (16 / 16 / 10). The old word bank remains archived; only a small explicit allowlist of practical legacy objects is served. Add content in `_OBJECTS`, `_ACTIONS`, `_VOCAB` and `_PHRASES` in `engine/learning_bank.py`, preserving unique IDs within each mode. CEFR assignments are practical learning estimates, not official exam-list certification.
- The existing renderer is still a question/countdown/answer/spelling format. It adapts text and pronunciation per mode; Useful Vocabulary speaks its example sentence as part of the answer, while the video remains one scene per item rather than a multi-scene dialogue.
- Automatic image mode uses the first candidate after ranking/optional vision filtering. Manual review is safer if the vision provider is unavailable or the action is visually ambiguous.
- Do not change `words_per_video` casually; quality/layout tests and default UI are designed around three items.
- The old legacy Prepare path remains for regression compatibility. Normal UI calls the new mode-aware path explicitly.
