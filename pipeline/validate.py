"""Validate storyboard.json against the JSON schema plus cross-field rules.

Run before every stage. Exits non-zero on any error.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
STORYBOARD = ROOT / "storyboard.json"
SCHEMA = ROOT / "schema" / "storyboard.schema.json"


def load(path: str | Path = STORYBOARD) -> dict[str, Any]:
    """Load and parse a storyboard JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(sb: dict[str, Any], schema: dict[str, Any] | None = None) -> list[str]:
    """Validate storyboard data against schema and cross-field invariants."""
    schema = schema or json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in Draft202012Validator(schema).iter_errors(sb)
    ]
    if errors:
        return errors

    # Cross-field rules the JSON schema cannot express.
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


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate a storyboard JSON file.")
    ap.add_argument("path", nargs="?", default=str(STORYBOARD), help="Path to storyboard.json")
    args = ap.parse_args()

    sb = load(args.path)
    errors = validate(sb)
    if errors:
        print(f"{Path(args.path).name} is INVALID:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    total = sum(s["duration_s"] for s in sb["shots"]) + sb["end_card"]["duration_s"]
    print(f"{Path(args.path).name} OK: {len(sb['shots'])} shots, {total:.0f}s total")


if __name__ == "__main__":
    main()
