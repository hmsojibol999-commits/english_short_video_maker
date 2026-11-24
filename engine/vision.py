"""Photo-vs-word check with a Groq vision model.

Why: the word comes from a text model and the photos from a keyword search, so
nothing guaranteed that the picture really shows the word (a parrot cage under
"batting cage", a whole animal under "tail"). This asks a vision model one
narrow question per photo and returns "yes" / "no" / "unsure".

Design rules:
* Never block the pipeline because the vision model is unavailable. Any
  problem (no key, model missing, rate limit, bad JSON) gives "unsure" and the
  caller decides; prepare.py keeps the photo, build.py only fails on a clear "no".
* Only the verdict is stored, never the image, and the key never leaves the
  Authorization header.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time

import requests

from . import errors as E
from . import llm

GROQ_CHAT = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3.6-27b"

PROMPT = (
    'A short English-learning video teaches this target: "{word}".\n'
    "Inspect the photo and decide whether it clearly illustrates that target.\n"
    "For a physical object, the main subject must be the correct whole object, not merely a part.\n"
    "For a person-action or real-life scenario, the photo must visibly show the described action or situation; a person merely standing near the object is not enough.\n"
    "Answer \"yes\" only when the main subject/action is a clear and natural match and no different subject would be an equally good answer.\n"
    "Answer \"no\" if it mainly shows something unrelated, a drawing/logo, only text, or a product box.\n"
    'Answer "unsure" if you cannot tell.\n'
    'Reply ONLY with JSON: {{"verdict":"yes|no|unsure","main_subject":"<2-4 words>"}}'
)


def has_dark_borders(im) -> bool:
    """True when a wide strip along an edge is almost pure black (letterbox bars)."""
    g = im.convert("L").resize((64, 64))
    px = list(g.getdata())
    def strip(rows=None, cols=None):
        vals = [px[y * 64 + x] for y in range(64) for x in range(64)
                if (rows and y in rows) or (cols and x in cols)]
        return sum(vals) / max(1, len(vals)), max(vals) if vals else 255
    k = 8                                           # 12.5 % of each side
    for rows, cols in ((range(0, k), None), (range(64 - k, 64), None),
                       (None, range(0, k)), (None, range(64 - k, 64))):
        mean, peak = strip(rows, cols)
        if mean < 18 and peak < 60:
            return True
    return False


def data_url_from_url(url: str, max_side: int = 768, timeout: int = 30) -> tuple:
    """Download a photo and return (data_url, dark_borders). Cloudflare cannot fetch
    remote image links itself, so Prepare must send the picture as a data URL (Build already does)."""
    from PIL import Image
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    borders = has_dark_borders(im)
    return data_url_from_file(io.BytesIO(r.content), max_side), borders


def data_url_from_file(path, max_side: int = 768) -> str:
    """Small JPEG data URL of a local image (no expiring links, ~100 KB)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    k = max_side / max(im.size)
    if k < 1:
        im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def parse_verdict(text: str) -> dict:
    """Parse the model reply. Anything unreadable is 'unsure'."""
    t = (text or "").strip()
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()      # reasoning models
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    data = None
    try:
        data = json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, flags=re.S)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                data = None
    if not isinstance(data, dict):
        return {"verdict": "unsure", "subject": ""}
    v = str(data.get("verdict", "")).strip().lower()
    if v not in ("yes", "no", "unsure"):
        v = "unsure"
    return {"verdict": v, "subject": str(data.get("main_subject", ""))[:60]}


def _check_once(word: str, image_url: str, url: str, key: str, model: str, prov: str,
                timeout: int, dbg: dict) -> dict:
    """One model, with retries. dbg["detail"] keeps the last HTTP status + body start."""
    if not key or not image_url:
        return {"verdict": "unsure", "subject": "", "error": E.GROQ_NO_KEY}
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT.format(word=word)},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]}],
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last = E.GROQ_BAD
    for attempt in range(2):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
        except requests.RequestException:
            last = E.GROQ_BAD
            time.sleep(1 + attempt)
            continue
        dbg["detail"] = f"{model}: HTTP {r.status_code}: {(r.text or '')[:220]}"
        if prov == "cloudflare" and llm.needs_license(r.text) and llm.accept_model_license(url, key, model):
            continue                                   # one-time Llama vision agreement, then retry
        if r.status_code == 400 and ("response_format" in (r.text or "").lower()
                                     or "json" in (r.text or "").lower()):
            body.pop("response_format", None)
            continue
        low = (r.text or "").lower()
        if "decommissioned" in low or "model_not_found" in low or "does not exist" in low:
            return {"verdict": "unsure", "subject": "", "error": E.GROQ_MODEL}
        if r.status_code == 429:
            last = E.GROQ_RATE
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code in (401, 403, 404):
            return {"verdict": "unsure", "subject": "",
                    "error": E.GROQ_NO_KEY if r.status_code == 401 else E.GROQ_MODEL}
        if r.status_code != 200:
            last = E.GROQ_BAD
            time.sleep(1 + attempt)
            continue
        try:
            text = r.json()["choices"][0]["message"]["content"]
        except Exception:  # noqa: BLE001
            last = E.GROQ_BAD
            continue
        out = parse_verdict(text)
        out["error"] = None
        return out
    return {"verdict": "unsure", "subject": "", "error": last}


def check_photo(word: str, image_url: str, model: str | None = None,
                key: str | None = None, timeout: int = 60) -> dict:
    """Return {"verdict": yes|no|unsure, "subject": str, "error": code|None, "detail": str}.
    On Cloudflare several vision models are tried until one is accepted; the working one is remembered."""
    url, token, first, prov = llm.resolve("vision", model or DEFAULT_MODEL, key)
    if prov == "cloudflare" and (image_url or "").startswith(("http://", "https://")):
        try:
            image_url, borders = data_url_from_url(image_url)
        except Exception as ex:                            # noqa: BLE001
            return {"verdict": "unsure", "subject": "", "error": E.GROQ_BAD,
                    "detail": f"photo download failed: {str(ex)[:120]}"}
        if borders:
            return {"verdict": "no", "subject": "black borders", "error": None, "detail": ""}
    models = [first]
    if prov == "cloudflare":
        models = llm.vision_models()
        if _WORKING.get("model") in models:
            models = [_WORKING["model"]] + [m for m in models if m != _WORKING["model"]]
    res, dbg = {"verdict": "unsure", "subject": "", "error": E.GROQ_MODEL}, {}
    for m in models:
        res = _check_once(word, image_url, url, token, m, prov, timeout, dbg)
        if res.get("error") not in (E.GROQ_MODEL,):
            if prov == "cloudflare" and not res.get("error"):
                _WORKING["model"] = m
            break
    res.setdefault("detail", dbg.get("detail", ""))
    res["detail"] = res.get("detail") or dbg.get("detail", "")
    return res


_WORKING: dict = {}


def filter_photos(word: str, photos: list, keep: int, model: str | None = None,
                  key: str | None = None, check=check_photo, pause: float = 0.0,
                  workers: int = 1) -> tuple:
    """Check photos in order until `keep` have said "yes".

    `workers` > 1 checks that many photos at the same time (much faster; used on
    Cloudflare). Order of the kept photos is always the original order.
    Returns (kept_photos, report) where report is a dict:
      checked, yes, no, unsure, unavailable (True when the model could not be used).
    Photos are annotated with "vision": verdict. If the model is unavailable the
    photos are returned unchanged (verdict "unsure") so the pipeline keeps working.
    """
    from concurrent.futures import ThreadPoolExecutor

    workers = max(1, int(workers or 1))
    kept, rep = [], {"checked": 0, "yes": 0, "no": 0, "unsure": 0, "unavailable": False}
    fails = 0
    i = 0
    while i < len(photos) and len(kept) < keep:
        batch = photos[i:i + workers]
        i += len(batch)
        if rep["checked"] and pause:
            time.sleep(pause)

        def one(p):
            try:
                return check(word, p.get("large") or p.get("thumb") or "", model, key)
            except Exception as ex:                      # noqa: BLE001
                return {"verdict": "unsure", "subject": "", "error": E.GROQ_BAD, "detail": str(ex)[:100]}

        if len(batch) == 1:
            results = [one(batch[0])]
        else:
            with ThreadPoolExecutor(max_workers=len(batch)) as ex:
                results = list(ex.map(one, batch))
        for p, res in zip(batch, results):
            rep["checked"] += 1
            if res.get("error") in (E.GROQ_NO_KEY, E.GROQ_MODEL):
                rep["unavailable"] = True
                break
            if res.get("error"):
                fails += 1
            v = res["verdict"]
            rep[v] += 1
            if v == "yes":
                kept.append({**p, "vision": "yes"})
        if rep["unavailable"]:
            break
        if rep["checked"] >= 6 and rep["yes"] == 0 and rep["no"] >= 6:
            break                                  # six clear "no" and no "yes": drop this word early
        if fails >= 3 and rep["yes"] == 0:        # model keeps failing: stop wasting calls
            rep["unavailable"] = True
            break
    if rep["unavailable"]:
        return [{**p, "vision": "unsure"} for p in photos[:keep]], rep
    return kept[:keep], rep


LOCATE_PROMPT = (
    'An English-learning video teaches this target: "{word}".\n'
    "Decide whether a viewer needs an arrow to identify the important visual target.\n"
    "For an object, point to the whole object. For an action, point to the person clearly "
    "performing that action; when relevant, include the object they are acting on. "
    "For a real-life phrase or situation, point to the people or item that best explains the scene.\n"
    '- "arrow": false when the important target is already the one obvious main subject and '
    "fills much of the photo.\n"
    '- "arrow": true when the photo shows many things, or the important target is small, '
    "off-centre, or difficult to identify without help.\n"
    '"x" and "y" = the centre of the important target as a fraction of photo width and height '
    "(0,0 is top-left, 1,1 bottom-right).\n"
    'Reply ONLY with JSON: {{"arrow": true|false, "x": 0.0-1.0, "y": 0.0-1.0}}'
)


def parse_locate(text: str):
    """-> (arrow_bool, (x, y)) or None when the reply is unusable."""
    t = re.sub(r"<think>.*?</think>", "", (text or ""), flags=re.S).strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    m = re.search(r"\{.*\}", t, flags=re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        arrow = d.get("arrow")
        if isinstance(arrow, str):
            arrow = arrow.strip().lower() == "true"
        x, y = float(d.get("x")), float(d.get("y"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        return None
    clamp = lambda v: min(0.92, max(0.08, v))      # keep the arrow tip away from the very edge
    return bool(arrow), (round(clamp(x), 3), round(clamp(y), 3))


def locate_photo(word: str, image_url: str, key: str | None = None, timeout: int = 60):
    """Ask the vision model whether the photo needs an arrow and where it goes.
    Returns (arrow, (x, y)) or None. Never raises."""
    try:
        url, token, first, prov = llm.resolve("vision", DEFAULT_MODEL, key)
        if not token or not image_url:
            return None
        models = [first]
        if prov == "cloudflare":
            models = llm.vision_models()
            if _WORKING.get("model") in models:
                models = [_WORKING["model"]] + [m for m in models if m != _WORKING["model"]]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        for m in models:
            body = {"model": m, "temperature": 0, "max_tokens": 300,
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": LOCATE_PROMPT.format(word=word)},
                        {"type": "image_url", "image_url": {"url": image_url}}]}]}
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
            if r.status_code != 200:
                continue
            out = parse_locate(r.json()["choices"][0]["message"]["content"])
            if out is not None:
                return out
    except Exception:                                 # noqa: BLE001 - arrows are a bonus, never block
        return None
    return None
