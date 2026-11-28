import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import common


class CommonTests(unittest.TestCase):
    def test_content_hash_is_deterministic_and_sensitive(self) -> None:
        h1 = common.content_hash("a", {"x": 1, "y": 2})
        h2 = common.content_hash("a", {"y": 2, "x": 1})
        h3 = common.content_hash("a", {"x": 1, "y": 3})
        self.assertEqual(len(h1), 16)
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_redact_masks_credentials(self) -> None:
        raw = "Bearer secret_token_1234567890 key=abcdef123456 AIzaSyDummySecretKey12345"
        cleaned = common.redact(raw)
        self.assertNotIn("secret_token_1234567890", cleaned)
        self.assertNotIn("abcdef123456", cleaned)
        self.assertNotIn("AIzaSyDummySecretKey12345", cleaned)

    def test_retry_succeeds_after_transient_error(self) -> None:
        calls = {"n": 0}

        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("transient")
            return "ok"

        with mock.patch.object(common.time, "sleep"):
            self.assertEqual(common.retry(flaky, attempts=3, base_delay=0.01), "ok")
        self.assertEqual(calls["n"], 2)

    def test_retry_rejects_non_positive_attempts(self) -> None:
        with self.assertRaises(ValueError):
            common.retry(lambda: None, attempts=0)

    def test_cached_output_hits_and_does_not_cache_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "runs.jsonl"
            cache = root / ".cache"
            out = root / "out" / "sample.txt"
            with mock.patch.object(common, "RUNS", runs), mock.patch.object(common, "CACHE", cache):
                calls = {"n": 0}

                def producer(p: Path) -> None:
                    calls["n"] += 1
                    p.write_text("hello", encoding="utf-8")

                _, hit1 = common.cached_output("test", "k1", out, producer, "m", {"a": 1})
                _, hit2 = common.cached_output("test", "k1", out, producer, "m", {"a": 1})
                self.assertFalse(hit1)
                self.assertTrue(hit2)
                self.assertEqual(calls["n"], 1)

                bad_out = root / "out" / "bad.txt"
                with self.assertRaises(RuntimeError):
                    with mock.patch.object(common.time, "sleep"):
                        common.cached_output(
                            "test",
                            "k2",
                            bad_out,
                            lambda _p: (_ for _ in ()).throw(RuntimeError("boom")),
                            "m",
                            {},
                        )
                self.assertFalse((cache / "test" / "bad.txt.hash").exists())

                lines = [json.loads(l) for l in runs.read_text(encoding="utf-8").splitlines()]
                self.assertEqual([l["cache"] for l in lines[:2]], ["miss", "hit"])
                self.assertFalse(lines[2]["ok"])


if __name__ == "__main__":
    unittest.main()
