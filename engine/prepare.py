"""prepare.yml / more_images.yml entry point.

  python -m engine.prepare --session SID [--category kitchen]
  python -m engine.prepare --session SID --more "wood chisel"
  python -m engine.prepare --session SID --refill --exclude "word one,word two"

--refill adds fresh words to an existing session (used when the user skipped
every spare word), so "skip" never runs out.

Writes sessions/<SID>/candidates.json and status.json on the state branch.
On failure status.json carries a stable error code the UI translates.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import random
import re
import sys
import traceback

from . import config as C
from . import errors as E
from . import llm
from .pixabay import Pixabay, photo_keys, unique_photos
from .selection import SID_RE
from . import vision as V
from .state import State
from .words import (builtin_words, fallback_words, filter_candidates, groq_words, too_similar,
                    normalize, verify_words)
from . import learning_bank

PHOTOS_PER_WORD = 4
MIN_PHOTOS = 3            # a word with 3 good photos is still accepted (4 is the goal)
MIN_POOL = 6              # with vision on: fewer Pixabay photos than this -> drop the word at once
WORD_BUFFER = 14          # words asked from the AI (many get dropped when photos do not match)
MAX_TRIED = 40            # safety cap on how many words one Prepare run may try
VISION_WORKERS = 3        # photos checked at the same time (Cloudflare only)
VISION_POOL = 10          # photos fetched per word so that 4 can survive the vision check
VISION_PAUSE = 2.1        # seconds between vision calls (Groq free tier ~30 requests/minute)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def vision_on(settings, mock: bool) -> bool:
    return bool(getattr(settings, "vision_check", True)) and not mock \
        and llm.available()


def vision_filter(settings, word: str, photos: list, keep: int, warnings: list) -> list:
    """Keep only photos that clearly match the selected object/action/scenario."""
    kept, rep = V.filter_photos(word, photos, keep, settings.vision_model,
                                  pause=(0.0 if llm.cloudflare_ready() else VISION_PAUSE),
                                  workers=(VISION_WORKERS if llm.cloudflare_ready() else 1))
    print(f"[prepare] vision '{word}': {rep}", flush=True)
    if rep["unavailable"] and not any(w.get("code") == "vision_unavailable" for w in warnings):
        warnings.append({"code": "vision_unavailable", "stage": "vision",
                         "detail": "vision model could not be used; photos were NOT checked"})
    return kept


BANK_LOW = 40             # warn when fewer unused curated words than this are left


def pick_words(settings, used, bad, category, rng, mock, total) -> tuple:
    """Return (candidate list ordered by preference, source, warnings).
    Order: the curated word bank first (medium difficulty, always photographs well);
    the AI only adds words when the bank has too few unused words left."""
    warnings = []
    bank = filter_candidates(builtin_words(rng, category), used, bad)
    print(f"[prepare] word bank: {len(bank)} unused words left"
          + (f" in category '{category}'" if category else ""), flush=True)
    if mock or len(bank) >= total:
        if not mock and len(bank) < BANK_LOW:
            warnings.append({"code": "bank_low", "stage": "bank",
                             "detail": f"only {len(bank)} unused words left in the word bank"})
        return bank, "builtin", warnings
    items = list(bank)
    source = "groq"
    try:
        raw = groq_words(total, used + [b["word"] for b in bank], bad, category, settings.text_model, rng=rng)
        ai = filter_candidates(raw, used + [b["word"] for b in bank], bad)
        checked = verify_words(ai, settings.text_model)
        if len(checked) < len(ai):
            print(f"[prepare] verify dropped: {sorted({i['word'] for i in ai} - {c['word'] for c in checked})}", flush=True)
        items += filter_candidates(checked, used + [b["word"] for b in bank], bad)
    except E.WCError as ex:
        print(f"[prepare] WARNING AI text failed ({ex.code}): {ex.detail[:200]}", flush=True)
        warnings.append({"code": ex.code, "detail": ex.detail[:200], "stage": "groq"})
        source = "builtin"
    warnings.append({"code": "bank_low", "stage": "bank",
                     "detail": f"only {len(bank)} unused words left in the word bank"})
    return items, source, warnings


def build_candidates(settings, state: State, sid: str, category: str | None,
                     mock: bool, extra_used=(), total: int | None = None,
                     seed: str = "", mode: str | None = None, level: str = "mixed") -> dict:
    """Pick learning items + photos when mode is set; otherwise use legacy object flow.

    Legacy AI word generation remains available through the old code path. New learning
    modes use stable item IDs and the curated offline bank by default.
    """
    if mode:
        return build_learning_candidates(settings, state, sid, category, mock,
                                         extra_used=extra_used, total=total, seed=seed,
                                         mode=mode, level=level)
    used = state.read_lines("used_words.txt") + [w for w in extra_used if w]
    bad = state.read_lines("bad_words.txt")
    rng = random.Random(sid + seed)
    total = total or settings.words_per_video * 2
    ask = max(total + 8, WORD_BUFFER)
    items, source, warnings = pick_words(settings, used, bad, category, rng, mock, ask)
    px = Pixabay(mock=mock, cache_dir=state.p("pixabay-cache"))
    use_vision = vision_on(settings, mock)
    pool = VISION_POOL if use_vision else PHOTOS_PER_WORD
    min_photos = MIN_PHOTOS if use_vision else PHOTOS_PER_WORD
    out, seen, tried = [], set(), set()
    dropped = []
    topups = 0
    queue = list(items)
    while len(out) < total and len(tried) < MAX_TRIED:
        if not queue:
            if topups >= 2:
                break
            topups += 1
            extra, _src = fallback_words(rng, category)
            skip = used + [o["word"] for o in out] + list(tried)
            more = filter_candidates(extra, skip, bad)
            if not more:
                break
            queue.extend(more[:20])
            warnings.append({"code": "topped_up", "detail": "extra words added from curated list",
                             "stage": "words"})
        it = queue.pop(0)
        n = normalize(it["word"])
        if n in seen or n in tried:
            continue
        tried.add(n)
        if too_similar(it["word"], [o["word"] for o in out]):
            print(f"[prepare] skip '{it['word']}': looks like a word already in the list", flush=True)
            continue
        try:
            photos = px.candidates(it["word"], it["search_query"], page=1, want=pool)
            if use_vision and len(photos) < MIN_POOL:
                print(f"[prepare] drop '{it['word']}': Pixabay has only {len(photos)} photos", flush=True)
                dropped.append(it["word"])
                continue
            if use_vision and len(photos) >= min_photos:
                photos = vision_filter(settings, it["word"], photos, PHOTOS_PER_WORD, warnings)
        except E.WCError as ex:
            if ex.code in (E.PIXABAY_NO_KEY, E.PIXABAY_RATE):
                raise
            print(f"[prepare] Pixabay failed for {it['word']}: {ex.detail}", flush=True)
            dropped.append(it["word"])
            continue
        if len(photos) < min_photos:
            print(f"[prepare] drop '{it['word']}': only {len(photos)} usable photos", flush=True)
            dropped.append(it["word"])
            continue
        seen.add(n)
        out.append({**it, "photos": photos, "page": 1})
    need = min(settings.words_per_video, total)
    if len(out) < need:
        raise E.WCError(E.PIXABAY_EMPTY,
                        f"only {len(out)} usable words found (need {need}); "
                        f"{len(dropped)} words dropped because their photos did not match: "
                        f"{', '.join(dropped[:12])}",
                        "prepare")
    return {
        "session": sid,
        "created": _now(),
        "category": category or "",
        "source": source,
        "words_per_video": settings.words_per_video,
        "warnings": warnings,
        "words": out,
    }


def build_learning_candidates(settings, state: State, sid: str, category: str | None,
                              mock: bool, extra_used=(), total: int | None = None,
                              seed: str = "", mode: str = "object",
                              level: str = "mixed") -> dict:
    """Use only the built-in mode-specific bank unless the legacy AI toggle is enabled.

    An item's ID, not its visible word, is the durable identity. History is stored
    separately per mode, so one mode never consumes another mode's vocabulary.
    """
    known_modes = learning_bank.modes()
    if mode not in known_modes:
        raise E.WCError(E.SELECTION_BAD, f"unknown learning mode: {mode}", "prepare")
    used_ids = set(state.read_lines(f"used_items/{mode}.txt"))
    used_words = state.read_lines("used_words.txt") if mode == "object" else []
    blocked = {normalize(w) for w in used_words + list(extra_used) if w}
    bad_lines = state.read_lines(f"bad_items/{mode}.txt")
    if mode == "object":
        bad_lines += state.read_lines("bad_words.txt")
    bad = {normalize(w) for w in bad_lines}
    rng = random.Random(sid + seed + mode + level)
    pool_items = learning_bank.items_for(mode, level, category)
    rng.shuffle(pool_items)
    queue = [it for it in pool_items if it["id"] not in used_ids
             and normalize(it["word"]) not in blocked and normalize(it["word"]) not in bad]
    total = total or settings.words_per_video * 2
    # The old AI word path remains available, but only by an explicit config opt-in.
    if mode == "object" and getattr(settings, "allow_ai_word_generation", False) and len(queue) < total:
        try:
            raw = groq_words(total - len(queue), used_words + list(extra_used),
                             state.read_lines("bad_words.txt"), category, settings.text_model, rng=rng)
            for it in filter_candidates(raw, used_words + list(extra_used), state.read_lines("bad_words.txt")):
                key = re.sub(r"[^a-z0-9]+", "_", it["word"].lower()).strip("_")
                it.update({"id": f"object_ai_{key}", "type": "object", "mode": mode,
                           "level": "B1", "question": "What is this called?",
                           "answer": learning_bank.object_answer(it["word"]), "slow_text": it["word"],
                           "label": it["word"].title(), "spelling": it["word"],
                           "image_check": it["word"], "bengali_meaning": "",
                           "example": f"This is a {it['word']}."})
                if it["id"] not in used_ids:
                    queue.append(it)
        except E.WCError as ex:
            print(f"[prepare] optional AI word fallback not available: {ex.code}", flush=True)
    print(f"[prepare] {mode} bank: {len(queue)} unused items (level={level})", flush=True)
    px = Pixabay(mock=mock, cache_dir=state.p("pixabay-cache"))
    use_vision = vision_on(settings, mock)
    want_pool = VISION_POOL if use_vision else PHOTOS_PER_WORD
    min_photos = MIN_PHOTOS if use_vision else PHOTOS_PER_WORD
    out, tried, dropped = [], set(), []
    warnings = []
    vision_requested = bool(getattr(settings, "vision_check", True)) and not mock
    if vision_requested and not use_vision:
        warnings.append({
            "code": "vision_unavailable",
            "stage": "vision",
            "detail": "no vision provider credentials are configured; Pixabay results were not AI-verified",
        })
    while queue and len(out) < total and len(tried) < MAX_TRIED:
        it = queue.pop(0)
        if it["id"] in tried:
            continue
        tried.add(it["id"])
        try:
            target = it.get("image_check") or it["word"]
            photos = px.candidates(target, it["search_query"], page=1, want=want_pool)
            if use_vision and len(photos) < MIN_POOL:
                dropped.append(it["word"]); continue
            if use_vision and len(photos) >= min_photos:
                photos = vision_filter(settings, target, photos, PHOTOS_PER_WORD, warnings)
        except E.WCError as ex:
            if ex.code in (E.PIXABAY_NO_KEY, E.PIXABAY_RATE):
                raise
            print(f"[prepare] skip {it['id']}: Pixabay {ex.detail[:150]}", flush=True)
            dropped.append(it["word"]); continue
        if len(photos) < min_photos:
            dropped.append(it["word"]); continue
        out.append({**it, "photos": photos, "page": 1})
    if len(out) < min(settings.words_per_video, total):
        raise E.WCError(E.BANK_EMPTY,
                        f"not enough unused {mode} items at level {level}; "
                        f"found {len(out)}, need {min(settings.words_per_video, total)}. "
                        f"{len(dropped)} skipped because suitable Pixabay photos were unavailable.",
                        "prepare")
    if len(queue) < 10:
        warnings.append({"code": "bank_low", "stage": "bank",
                         "detail": f"{len(queue)} more unused {mode} items remain in this level"})
    return {"session": sid, "created": _now(), "category": category or "",
            "source": "builtin", "mode": mode, "level": level.upper(),
            "words_per_video": settings.words_per_video, "warnings": warnings, "words": out}


def more_images(state: State, sid: str, word: str, mock: bool, settings=None) -> dict:
    path = f"sessions/{sid}/candidates.json"
    data = state.read_json(path)
    if not data:
        raise E.WCError(E.IMAGE_MISSING, "no candidates.json for this session", "more_images")
    target = None
    for w in data["words"]:
        if w["word"] == word or normalize(w["word"]) == normalize(word):
            target = w
            break
    if target is None:
        raise E.WCError(E.SELECTION_BAD, f"unknown word '{word}'", "more_images")
    px = Pixabay(mock=mock, cache_dir=state.p("pixabay-cache"))
    use_vision = settings is not None and vision_on(settings, mock)
    have = {p["id"] for p in target["photos"]}
    have_keys = set()
    for p in target["photos"]:
        have_keys |= photo_keys(p)
    added = []
    page = target.get("page", 1)
    for _ in range(3):
        page += 1
        found = px.candidates(target.get("image_check") or target["word"], target["search_query"], page=page,
                              want=VISION_POOL if use_vision else PHOTOS_PER_WORD, exclude_ids=have,
                              exclude_keys=have_keys)
        if use_vision and found:
            found = vision_filter(settings, target.get("image_check") or target["word"], found, PHOTOS_PER_WORD, [])
        for p in unique_photos(found, have_keys):
            have.add(p["id"])
            have_keys |= photo_keys(p)
            added.append(p)
        target["page"] = page
        if len(added) >= PHOTOS_PER_WORD:
            break
    if not added:
        raise E.WCError(E.PIXABAY_EMPTY, f"no more photos for '{word}'", "more_images")
    target["photos"].extend(added[:PHOTOS_PER_WORD])
    data["updated"] = _now()
    state.write_json(path, data)
    return {"word": target["word"], "added": len(added[:PHOTOS_PER_WORD])}


def refill_words(settings, state: State, sid: str, exclude: list, mock: bool) -> dict:
    """Append new words (with photos) to an existing session. Never repeats a word
    that is already in the session, was skipped, or is in the word history."""
    path = f"sessions/{sid}/candidates.json"
    data = state.read_json(path)
    if not data:
        raise E.WCError(E.IMAGE_MISSING, "no candidates.json for this session", "refill")
    have = [w["word"] for w in data["words"]]
    mode = data.get("mode")
    more = build_candidates(settings, state, sid, data.get("category") or None, mock,
                            extra_used=have + list(exclude), total=settings.words_per_video,
                            seed=f"-refill{len(have)}", mode=mode,
                            level=data.get("level", "mixed"))
    data["words"].extend(more["words"])
    data["warnings"] = (data.get("warnings") or []) + more["warnings"]
    data["updated"] = _now()
    state.write_json(path, data)
    return {"added": [w["word"] for w in more["words"]]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--category", default="")
    ap.add_argument("--mode", default="object", choices=tuple(learning_bank.modes()))
    ap.add_argument("--level", default="mixed", choices=("mixed", "A1", "A2", "B1"))
    ap.add_argument("--more", default="")
    ap.add_argument("--refill", action="store_true")
    ap.add_argument("--exclude", default="")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--state-dir", default=os.environ.get("STATE_DIR", "state"))
    ap.add_argument("--remote", default=os.environ.get("STATE_REMOTE", ""))
    a = ap.parse_args(argv)
    if not SID_RE.match(a.session):
        print("bad session id", file=sys.stderr)
        return 2
    settings = C.load_settings()
    state = State(a.state_dir, a.remote or None).init()
    base = f"sessions/{a.session}"
    try:
        if a.refill:
            excl = [w.strip().lower() for w in a.exclude.split(",") if w.strip()]
            res = refill_words(settings, state, a.session, excl, a.mock)
            state.write_json(f"{base}/more_status.json",
                             {"state": "ok", "refill": res["added"], "at": _now()})
            msg = f"refill {a.session}"
        elif a.more:
            res = more_images(state, a.session, a.more, a.mock, settings)
            state.write_json(f"{base}/more_status.json",
                             {"state": "ok", "word": res["word"], "added": res["added"],
                              "at": _now()})
            msg = f"more images {a.session} {res['word']}"
        else:
            cand = build_candidates(settings, state, a.session, a.category or None, a.mock,
                                    mode=a.mode, level=a.level)
            state.write_json(f"{base}/candidates.json", cand)
            state.write_json(f"{base}/status.json",
                             {"state": "ok", "source": cand["source"],
                              "warnings": cand["warnings"], "at": _now()})
            removed = state.prune_sessions()
            if removed:
                print(f"[prepare] pruned old sessions: {removed}")
            msg = f"prepare {a.session}"
        state.commit_push(msg)
        print("[prepare] done")
        return 0
    except E.WCError as ex:
        print(f"[prepare] FAILED {ex}", file=sys.stderr)
        name = "more_status.json" if (a.more or a.refill) else "status.json"
        state.write_json(f"{base}/{name}", {**ex.to_dict(), "at": _now()})
        try:
            state.commit_push(f"{name} error {a.session}")
        except E.WCError:
            pass
        return 1
    except Exception as ex:  # noqa: BLE001
        traceback.print_exc()
        name = "more_status.json" if (a.more or a.refill) else "status.json"
        state.write_json(f"{base}/{name}",
                         {"state": "error", "code": E.UNKNOWN, "detail": str(ex)[:300],
                          "stage": "prepare", "at": _now()})
        try:
            state.commit_push(f"{name} error {a.session}")
        except E.WCError:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
