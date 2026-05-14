#!/usr/bin/env python3
"""
Validates all rules files and generates index.json with the manifest.
Runs in validate-rules.yml and release-rules.yml workflows.

Usage:
  python scripts/validate_rules.py          # Validate and generate index.json
  python scripts/validate_rules.py --check-only  # Validate only, do not generate index
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

RULES_DIR = Path("rules")
INDEX_FILE = Path("index.json")

REQUIRED_FILES: list[str] = [
    "whitelist.yaml",
    "blacklist.yaml",
    "false_positives.yaml",
    "label_overrides.yaml",
    "keyword_overrides.yaml",
]

SCHEMAS: dict[str, dict] = {
    "whitelist.yaml": {
        "root_key": "repositories",
        "entry_keys": {"full_name", "reason", "ha_version", "added", "issue"},
        "required_keys": {"full_name", "reason"},
    },
    "blacklist.yaml": {
        "root_key": "repositories",
        "entry_keys": {"full_name", "reason", "ha_version", "added", "issue"},
        "required_keys": {"full_name", "reason"},
    },
    "false_positives.yaml": {
        "root_key": "issues",
        "entry_keys": {"full_name", "issue_number", "reason", "added", "issue"},
        "required_keys": {"full_name", "issue_number", "reason"},
    },
    "label_overrides.yaml": {
        "root_key": "overrides",
        "entry_keys": {"full_name", "labels"},
        "required_keys": {"full_name", "labels"},
    },
    "keyword_overrides.yaml": {
        "root_key": "overrides",
        "entry_keys": {"full_name", "keywords"},
        "required_keys": {"full_name", "keywords"},
    },
}


def validate_file(filepath: Path, schema: dict) -> tuple[list[str], list[dict], int]:
    """Validates a rules file. Returns (errors, entries, count)."""
    errors: list[str] = []
    entries: list[dict] = []

    if not filepath.exists():
        errors.append(f"File not found: {filepath}")
        return errors, entries, 0

    with open(filepath, encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"YAML error in {filepath}: {e}")
            return errors, entries, 0

    if data is None:
        data = {}

    root_key = schema["root_key"]
    raw_entries = data.get(root_key, [])

    if not isinstance(raw_entries, list):
        errors.append(f"'{root_key}' must be a list in {filepath}")
        return errors, entries, 0

    seen_keys: set[str] = set()

    for i, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            errors.append(f"Entry {i} in {filepath} is not a dictionary")
            continue

        # Check required keys
        for key in schema["required_keys"]:
            if key not in entry or entry[key] == "":
                errors.append(f"Entry {i} in {filepath}: missing required field '{key}'")
                continue

        # Check for unknown keys
        for key in entry:
            if key not in schema["entry_keys"]:
                errors.append(f"Entry {i} in {filepath}: unknown key '{key}'")

        # Detect duplicates
        dedup_key = str(entry.get("full_name", ""))
        if "issue_number" in entry:
            dedup_key += f"#{entry['issue_number']}"
        if dedup_key in seen_keys:
            errors.append(f"Duplicate entry: {dedup_key} in {filepath}")
        seen_keys.add(dedup_key)

        entries.append(entry)

    return errors, entries, len(entries)


def generate_index(stats: dict) -> dict:
    """Generates the index.json manifest."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    index = {
        "version": "1.0.0",
        "updated": now,
        "source": "https://github.com/RmG152/hacs-compatibility-auditor-rules",
        "rules": {
            key: {
                "count": info["count"],
                "file": str(info["file"].as_posix()),
            }
            for key, info in stats.items()
        },
    }

    content = json.dumps(index, indent=2, ensure_ascii=False)
    index["checksum"] = hashlib.sha256(content.encode("utf-8")).hexdigest()

    return index


def main():
    parser = argparse.ArgumentParser(description="Validate rules and generate index.json")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only validate, do not generate index.json",
    )
    args = parser.parse_args()

    all_errors: list[str] = []
    stats: dict[str, dict] = {}

    for filename in REQUIRED_FILES:
        filepath = RULES_DIR / filename
        schema = SCHEMAS.get(filename, {})
        errors, entries, count = validate_file(filepath, schema)

        for err in errors:
            print(f"::error file={filepath},line=1::{err}", file=sys.stderr)

        all_errors.extend(errors)

        key = filename.replace(".yaml", "")
        stats[key] = {
            "count": count,
            "entries": entries,
            "file": filepath,
        }

    if all_errors:
        print(f"[ERROR] Validation failed: {len(all_errors)} error(s)", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    if not args.check_only:
        index = generate_index(stats)
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        total = sum(s["count"] for s in stats.values())
        print(f"[OK] index.json generated with {total} rules total")
    else:
        print("[OK] Validation successful")

    # Summary per file
    for key, info in stats.items():
        print(f"  {key}: {info['count']} entries")


if __name__ == "__main__":
    main()
