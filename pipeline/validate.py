"""Validate storyboard.json against the schema plus cross-field rules.

Run before every stage. Exits non-zero on any error.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
STORYBOARD = ROOT / "storyboard.json"
SCHEMA = ROOT / "schema" / "storyboard.schema.json"


def load(path=STORYBOARD):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(sb, schema=None):
    schema = schema or json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in Draft202012Validator(schema).iter_errors(sb)
    ]
    if errors:
        return errors

    # Cross-field rules the schema cannot express.
    ids = [s["id"] for s in sb["shots"]]
    if len(ids) != len(set(ids)):
        errors.append("shots: duplicate shot ids")
    char_ids = {c["id"] for c in sb["characters"]}
    for s in sb["shots"]:
        for c in s.get("characters", []):
            if c not in char_ids:
                errors.append(f"{s['id']}: unknown character '{c}'")
    for cue in sb["music"]["cues"]:
        if cue["at_shot"] not in ids:
            errors.append(f"music cue references unknown shot {cue['at_shot']}")
    total = sum(s["duration_s"] for s in sb["shots"]) + sb["end_card"]["duration_s"]
    if not 60 <= total <= 90:
        errors.append(f"total duration {total:.1f}s is outside 60-90s")
    return errors


def main():
    errors = validate(load())
    if errors:
        print("storyboard.json is INVALID:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    sb = load()
    total = sum(s["duration_s"] for s in sb["shots"]) + sb["end_card"]["duration_s"]
    print(f"storyboard.json OK: {len(sb['shots'])} shots, {total:.0f}s total")


if __name__ == "__main__":
    main()
