"""Mode-specific content, stable histories, automatic Pixabay cache and speech."""
import os
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from engine import config as C
from engine import draw as D
from engine import learning_bank as L
from engine import pixabay as P
from engine import prepare
from engine import render as R
from engine import quality as Q
from engine.build import make_clips
from engine.state import State


class LearningBankTests(unittest.TestCase):
    def test_four_modes_have_separate_stable_ids_and_cefr_levels(self):
        expected = {"object", "action", "vocabulary", "phrases"}
        self.assertEqual(set(L.modes()), expected)
        for mode in expected:
            items = L.items_for(mode, "mixed")
            self.assertGreaterEqual(len(items), 8)
            ids = [x["id"] for x in items]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertTrue(all(x["mode"] == mode for x in items))
            self.assertTrue(all(x["level"] in {"A1", "A2", "B1"} for x in items))
            self.assertTrue(all(x["question"] and x["answer"] and x["search_query"] for x in items))

    def test_mode_banks_have_no_duplicate_normalized_targets(self):
        from engine.words import normalize
        for mode in L.modes():
            words = [normalize(x["word"]) for x in L.items_for(mode, "mixed")]
            self.assertEqual(len(words), len(set(words)), mode)

    def test_object_answer_is_a_complete_sentence_with_correct_article(self):
        objects = {x["word"]: x for x in L.items_for("object", "mixed")}
        self.assertEqual(objects["bottle"]["answer"], "This is a bottle.")
        self.assertEqual(objects["umbrella"]["answer"], "This is an umbrella.")
        self.assertEqual(objects["scissors"]["answer"], "These are scissors.")

    def test_action_items_use_action_question_and_complete_sentence(self):
        item = next(x for x in L.items_for("action") if x["word"].startswith("twist"))
        self.assertEqual(item["question"], "What is the person doing?")
        self.assertIn("twisting", item["answer"])
        self.assertTrue(item["answer"].startswith("The person is"))
        self.assertEqual(item["spelling"], "twist")
        self.assertIn("person", item["image_check"])

    def test_vocabulary_and_phrase_answers_are_not_object_labels(self):
        vocab = L.items_for("vocabulary")[0]
        phrase = L.items_for("phrases")[0]
        self.assertIn("means", vocab["answer"])
        self.assertTrue(vocab["example"])
        self.assertNotEqual(phrase["question"], "What is this called?")
        self.assertTrue(phrase["bengali_meaning"])

    def test_level_filter_is_applied_and_each_level_has_enough_items(self):
        for mode in L.modes():
            for level in ("A1", "A2", "B1"):
                items = L.items_for(mode, level)
                self.assertTrue(all(x["level"] == level for x in items))
                self.assertGreaterEqual(len(items), 8, f"{mode}/{level} must have enough spare items")

    def test_legacy_object_words_are_curated_not_served_wholesale(self):
        from engine import words
        manual = {row[2] for row in L._OBJECTS}
        legacy = [x for x in L.items_for("object") if x["word"] not in manual]
        self.assertTrue(legacy)
        self.assertTrue(all(x["word"] in L._LEGACY_OBJECT_ALLOWLIST for x in legacy))
        self.assertFalse(any(words.is_denied(x["word"]) for x in legacy))
        self.assertTrue(all(words.is_valid_shape(x["word"]) for x in legacy))


class PrepareLearningFlowTests(unittest.TestCase):
    def test_learning_mode_reports_when_no_vision_provider_is_configured(self):
        photos = [
            {"id": i, "thumb": "https://example.test/thumb.jpg",
             "large": "https://example.test/large.jpg", "w": 1200, "h": 800,
             "photographer": "Test", "page_url": "https://example.test/photo"}
            for i in range(10)
        ]
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(prepare.llm, "available", return_value=False), \
                mock.patch.object(prepare.Pixabay, "candidates", return_value=photos):
            cand = prepare.build_candidates(C.Settings(), State(d), "sid-action-no-vision-01", None,
                                            False, mode="action", level="A1")
        self.assertIn("vision_unavailable", {w["code"] for w in cand["warnings"]})

    def test_learning_mode_preserves_warnings_created_by_vision_filter(self):
        photos = [
            {"id": i, "thumb": "https://example.test/thumb.jpg",
             "large": "https://example.test/large.jpg", "w": 1200, "h": 800,
             "photographer": "Test", "page_url": "https://example.test/photo"}
            for i in range(10)
        ]

        def unavailable_filter(settings, target, candidates, keep, warnings):
            if not any(w.get("code") == "vision_unavailable" for w in warnings):
                warnings.append({"code": "vision_unavailable", "stage": "vision",
                                 "detail": "vision provider did not answer; photos were not verified"})
            return candidates[:keep]

        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(prepare.llm, "available", return_value=True), \
                mock.patch.object(prepare.Pixabay, "candidates", return_value=photos), \
                mock.patch.object(prepare, "vision_filter", side_effect=unavailable_filter):
            cand = prepare.build_candidates(C.Settings(), State(d), "sid-action-vision-fallback-01", None,
                                            False, mode="action", level="A1")
        self.assertIn("vision_unavailable", {w["code"] for w in cand["warnings"]})

    def test_every_mode_builds_six_candidates_offline_with_pixabay_mock(self):
        with tempfile.TemporaryDirectory() as d:
            state = State(d)
            settings = C.Settings()
            for i, mode in enumerate(("object", "action", "vocabulary", "phrases")):
                cand = prepare.build_candidates(settings, state, f"sid-{mode}-0001", None, True,
                                                mode=mode, level="mixed")
                self.assertEqual(cand["mode"], mode)
                self.assertEqual(cand["source"], "builtin")
                self.assertEqual(len(cand["words"]), 6)
                self.assertTrue(all(len(w["photos"]) == 4 for w in cand["words"]))
                self.assertTrue(all(w["id"].startswith(mode + "_") for w in cand["words"]))

    def test_ai_generator_is_not_called_in_default_bank_mode(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(
                prepare, "groq_words", side_effect=AssertionError("AI word generation called")):
            cand = prepare.build_candidates(C.Settings(), State(d), "sid-object-0001", None, True,
                                            mode="object", level="A1")
            self.assertEqual(len(cand["words"]), 6)

    def test_mode_and_cefr_inputs_work_through_prepare_cli(self):
        with tempfile.TemporaryDirectory() as d:
            remote_path = Path(d) / "state.git"
            subprocess.run(["git", "init", "--bare", str(remote_path)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            sid = "sid-action-cli-01"
            rc = prepare.main(["--session", sid, "--mode", "action", "--level", "A1",
                               "--mock", "--state-dir", str(Path(d) / "write"),
                               "--remote", remote_path.as_uri()])
            self.assertEqual(rc, 0)
            stored = State(Path(d) / "read", remote_path.as_uri()).init()
            cand = stored.read_json(f"sessions/{sid}/candidates.json")
            self.assertEqual((cand["mode"], cand["level"]), ("action", "A1"))
            self.assertTrue(all(x["level"] == "A1" for x in cand["words"]))

    def test_item_ids_remain_blocked_across_cefr_filters(self):
        with tempfile.TemporaryDirectory() as d:
            state = State(d)
            item = next(x for x in L.items_for("action", "A1"))
            state.append_lines("used_items/action.txt", [item["id"]])
            mixed = prepare.build_candidates(C.Settings(), state, "sid-action-level-01", None, True,
                                             mode="action", level="mixed")
            self.assertNotIn(item["id"], {x["id"] for x in mixed["words"]})

    def test_used_ids_are_separate_by_learning_mode(self):
        with tempfile.TemporaryDirectory() as d:
            state = State(d)
            object_item = L.items_for("object", "mixed")[0]
            state.append_lines("used_items/object.txt", [object_item["id"]])
            obj = prepare.build_candidates(C.Settings(), state, "sid-object-0002", None, True,
                                           mode="object", level="mixed")
            self.assertNotIn(object_item["id"], {w["id"] for w in obj["words"]})
            action = prepare.build_candidates(C.Settings(), state, "sid-action-0002", None, True,
                                              mode="action", level="mixed")
            self.assertEqual(len(action["words"]), 6)
            self.assertTrue(all(w["id"] in {x["id"] for x in L.items_for("action")} for w in action["words"]))



    def test_sentence_modes_have_a_relaxed_short_video_duration_gate(self):
        self.assertEqual(Q.duration_range(3, "object"), C.DURATION_RANGE)
        self.assertEqual(Q.duration_range(3, "action"), (20.0, 60.0))
        self.assertEqual(Q.duration_range(3, "vocabulary"), (20.0, 60.0))
        self.assertEqual(Q.duration_range(3, "phrases"), (20.0, 60.0))

class PixabayActionScoringTests(unittest.TestCase):
    def test_person_tags_are_penalized_for_objects_but_not_action_targets(self):
        with_person = {"alt": "woman, opening, bottle, hands", "width": 1800, "height": 1200}
        without_person = {"alt": "opening, bottle, hands", "width": 1800, "height": 1200}
        self.assertLess(P.score_photo(with_person, "bottle"),
                        P.score_photo(without_person, "bottle"))
        action_query = "a person opening a bottle"
        self.assertEqual(P.score_photo(with_person, action_query),
                         P.score_photo(without_person, action_query))
        scene_query = "two colleagues discussing a plan"
        scene_with_people = {"alt": "woman, discussing, office meeting", "width": 1800, "height": 1200}
        scene_without_people = {"alt": "discussing, office meeting", "width": 1800, "height": 1200}
        self.assertEqual(P.score_photo(scene_with_people, scene_query),
                         P.score_photo(scene_without_people, scene_query))
        from engine import vision
        self.assertIn("a person opening", vision.LOCATE_PROMPT.format(word=action_query))

class PixabayCacheTests(unittest.TestCase):
    HIT = {"id": 123, "pageURL": "https://pixabay.com/photos/example-123/", "type": "photo",
           "tags": "water bottle kitchen", "webformatURL": "https://pixabay.com/get/example_640.jpg",
           "largeImageURL": "https://pixabay.com/get/example_1280.jpg", "imageWidth": 2400,
           "imageHeight": 1800, "user": "Creator", "user_id": 1}

    class Response:
        status_code = 200
        headers = {}
        text = ""
        def json(self): return {"hits": [dict(PixabayCacheTests.HIT)]}

    def test_search_response_is_reused_for_24_hours(self):
        with tempfile.TemporaryDirectory() as d:
            calls = []
            def get(*args, **kwargs):
                calls.append(1)
                return self.Response()
            with mock.patch.object(P.requests, "get", get):
                px = P.Pixabay(key="test-key", cache_dir=d)
                self.assertEqual(len(px.search_raw("water bottle")), 1)
                self.assertEqual(len(px.search_raw("water bottle")), 1)
            self.assertEqual(len(calls), 1)
            cache_file = next(Path(d).glob("*.json"))
            self.assertTrue(cache_file.is_file())

    def test_by_id_response_is_cached_for_24_hours(self):
        with tempfile.TemporaryDirectory() as d:
            calls = []
            response = self.Response()
            def get(*args, **kwargs):
                calls.append(1)
                return response
            with mock.patch.object(P.requests, "get", get):
                px = P.Pixabay(key="test-key", cache_dir=d)
                self.assertIsNotNone(px.by_id(123))
                self.assertIsNotNone(px.by_id(123))
            self.assertEqual(len(calls), 1)

    def test_expired_cache_is_refreshed(self):
        with tempfile.TemporaryDirectory() as d:
            calls = []
            def get(*args, **kwargs):
                calls.append(1)
                return self.Response()
            with mock.patch.object(P.requests, "get", get):
                px = P.Pixabay(key="test-key", cache_dir=d)
                px.search_raw("water bottle")
                cache_file = next(Path(d).glob("*.json"))
                import json
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                data["cached_at"] -= 25 * 60 * 60
                cache_file.write_text(json.dumps(data), encoding="utf-8")
                # Keep filesystem mtime fresh: TTL must survive Git checkout timestamps.
                px.search_raw("water bottle")
            self.assertEqual(len(calls), 2)


class ModeSpeechAndLabelTests(unittest.TestCase):
    class FakeVoice:
        def __init__(self): self.calls = []
        def render(self, text, role, slow=False):
            self.calls.append((text, role, slow))
            return np.zeros(max(4800, len(text) * 480), dtype=np.float32)

    def test_make_clips_uses_mode_question_answer_and_target_pronunciation(self):
        voice = self.FakeVoice()
        word = R.WordRes("twist a bottle cap", "unused.png", None, (0.5, 0.5),
                         question="What is he doing?", answer_text="He is twisting the bottle cap.",
                         slow_text="twist", spelling="twist")
        clips, audio = make_clips(voice, [word])
        self.assertIn(("What is he doing?", "question", False), voice.calls)
        self.assertIn(("He is twisting the bottle cap.", "answer", False), voice.calls)
        self.assertIn(("twist", "answer", True), voice.calls)
        self.assertEqual(audio[0].letters, 5)
        self.assertIn("q0", clips)

    def test_mode_labels_fit_and_title_is_changeable(self):
        for theme in C.THEMES:
            label = D.build_label(theme, "He is twisting the bottle cap.")
            self.assertLessEqual(label.width / D.SS, 820)
            meaning = D.build_label(theme, "Improve", "To become better")
            self.assertGreater(meaning.height, 0)
            title = D.build_title(theme, "WHAT IS HE DOING?")
            self.assertGreater(title.width, 0)


if __name__ == "__main__":
    unittest.main()
