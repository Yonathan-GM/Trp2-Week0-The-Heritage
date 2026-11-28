import array
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

import check_submission
import run as orchestrator
from pipeline import assemble, keyframes, music, music_synth, radio_cut
from pipeline.validate import load


class PipelineStagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sb = load()

    def test_keyframes_build_prompt_includes_character_and_style(self) -> None:
        shot = self.sb["shots"][0]
        prompt = keyframes.build_prompt(self.sb, shot)
        self.assertIn(shot["image_prompt"], prompt)
        self.assertIn(self.sb["style"]["style_block"], prompt)
        self.assertIn(keyframes.FRAMING, prompt)
        self.assertIn("dark brown woven border", prompt)

    def test_music_build_request(self) -> None:
        req = music.build_request(self.sb)
        self.assertIn("instrumental", req["caption"])
        self.assertEqual(req["bpm"], self.sb["music"]["bpm"])
        self.assertEqual(len(req["hash"]), 16)

    def test_music_synth_curves_handles_short_slots(self) -> None:
        short_sb = {"shots": [{"id": "s01"}, {"id": "s02"}]}
        slots = [1.0, 1.2]
        total = sum(slots)
        t = np.linspace(0.0, total, 100)
        pluck_lv, pad_lv, shake_lv = music_synth.curves(short_sb, slots, total, t)
        self.assertEqual(len(pluck_lv), 100)
        self.assertTrue(np.all(np.isfinite(pad_lv)))
        self.assertTrue(np.all(shake_lv >= 0.0))

    def test_radio_cut_declick_and_trim_artifact_tail(self) -> None:
        rate = radio_cut.RATE
        speech = [int(8000 * math.sin(2 * math.pi * 220 * i / rate)) for i in range(int(0.6 * rate))]
        silence = [0] * int(0.3 * rate)
        click = [12000] * int(0.05 * rate)
        pcm = array.array("h", speech + silence + click)
        trimmed, ms_removed, burst = radio_cut.trim_artifact_tail(pcm)
        self.assertTrue(burst)
        self.assertGreater(ms_removed, 200)
        self.assertLess(len(trimmed), len(pcm))
        declicked = radio_cut.declick(trimmed)
        self.assertEqual(declicked[0], 0)
        self.assertEqual(declicked[-1], 0)

    def test_assemble_subtitles_and_fit_graph(self) -> None:
        self.assertEqual(assemble.smart("'hello'"), "\u2018hello\u2019")
        cues = assemble.make_cues(self.sb["shots"][5]["subtitle_en"], 6.0)
        self.assertGreaterEqual(len(cues), 1)
        for start, end, lines in cues:
            self.assertLess(start, end)
            self.assertLessEqual(len(lines), assemble.SUB_MAX_LINES)
            self.assertTrue(all(len(l) <= assemble.SUB_MAX_CHARS for l in lines))
        self.assertEqual(assemble.make_cues("   ", 3.0), [])
        self.assertIn("crop=1080:1920", assemble.fit_graph("src", 1080, 1920, 480, 832, "out"))
        self.assertIn("boxblur", assemble.fit_graph("src", 1920, 1080, 480, 832, "out"))

    def test_render_text_png_creates_valid_rgba_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "sub.png"
            assemble.render_text_png(["Line one", "Line two"], 320, 180, out, 150, 0.06, boxed=True)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)

    def test_run_resolve_stages(self) -> None:
        self.assertEqual(orchestrator.resolve_stages(), orchestrator.STAGES)
        self.assertEqual(orchestrator.resolve_stages(only="assemble"), ["assemble"])
        self.assertEqual(orchestrator.resolve_stages(start="shots"), ["shots", "music", "assemble"])

    def test_check_submission_scan_line(self) -> None:
        hits = check_submission.scan_line("API_KEY=super_secret_token_123456")
        self.assertTrue(hits)
        self.assertEqual(check_submission.scan_line("ADDIS_API_KEY="), [])


if __name__ == "__main__":
    unittest.main()
