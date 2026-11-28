import copy
import unittest

from pipeline.validate import load, validate


class ValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sb = load()

    def test_repo_storyboard_is_valid(self) -> None:
        self.assertEqual(validate(self.sb), [])

    def test_duplicate_shot_id_fails(self) -> None:
        sb = copy.deepcopy(self.sb)
        sb["shots"][1]["id"] = sb["shots"][0]["id"]
        errors = validate(sb)
        self.assertTrue(any("duplicate shot ids" in e for e in errors), errors)

    def test_unknown_character_fails(self) -> None:
        sb = copy.deepcopy(self.sb)
        sb["shots"][0]["characters"] = ["nonexistent_character"]
        errors = validate(sb)
        self.assertTrue(any("unknown character" in e for e in errors), errors)

    def test_unknown_music_cue_shot_fails(self) -> None:
        sb = copy.deepcopy(self.sb)
        sb["music"]["cues"][0]["at_shot"] = "s99"
        errors = validate(sb)
        self.assertTrue(any("unknown shot s99" in e for e in errors), errors)

    def test_duration_outside_range_fails(self) -> None:
        sb = copy.deepcopy(self.sb)
        for shot in sb["shots"]:
            shot["duration_s"] = 3
        errors = validate(sb)
        self.assertTrue(any("outside 60-90s" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
