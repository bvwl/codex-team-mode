#!/usr/bin/env python3
"""Safely preflight, install, or verify Team Mode Agent profiles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    print(
        "Team Mode profile management requires Python 3.11 or newer. "
        "Activate a compatible environment and run this script with its python or python3 command.",
        file=sys.stderr,
    )
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "agents"
MANIFEST_PATH = ROOT / "skills" / "team-mode" / "references" / "profiles.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight, install, or verify the five Team Mode Agent profiles without overwriting files."
    )
    parser.add_argument("--scope", choices=("personal", "project"), required=True)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root used with --scope project (default: current directory).",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--apply",
        action="store_true",
        help="Install missing profiles after a successful preflight. Without this flag, no files are written.",
    )
    action.add_argument(
        "--verify",
        action="store_true",
        help="Verify an existing installation without writing files.",
    )
    return parser.parse_args()


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("profiles"), dict):
        raise ValueError(f"Unsupported or malformed profile manifest: {path}")
    profiles = data["profiles"]
    for name, expected in profiles.items():
        if not isinstance(expected, dict):
            raise ValueError(f"Profile manifest entry must be an object: {name}")
        required = {"filename", "working_role", "model", "effort", "sandbox"}
        missing = required - expected.keys()
        if missing:
            raise ValueError(f"Profile manifest entry {name!r} is missing: {sorted(missing)}")
        filename = expected["filename"]
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError(f"Profile manifest entry {name!r} has an unsafe filename")
        for field in ("model", "effort", "sandbox"):
            if not isinstance(expected[field], str) or not expected[field]:
                raise ValueError(f"Profile manifest entry {name!r} has an invalid {field}")
        if not isinstance(expected["working_role"], bool):
            raise ValueError(f"Profile manifest entry {name!r} has an invalid working_role")
    return profiles


def destination_for(args: argparse.Namespace) -> Path:
    if args.scope == "personal":
        return Path.home() / ".codex" / "agents"
    return args.project_root.expanduser().resolve() / ".codex" / "agents"


def validate_profile(path: Path, name: str, expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"{path}: cannot parse TOML: {exc}"]

    actual = {
        "name": data.get("name"),
        "model": data.get("model"),
        "effort": data.get("model_reasoning_effort"),
        "sandbox": data.get("sandbox_mode"),
    }
    wanted = {
        "name": name,
        "model": expected["model"],
        "effort": expected["effort"],
        "sandbox": expected["sandbox"],
    }
    for field, wanted_value in wanted.items():
        if actual[field] != wanted_value:
            errors.append(
                f"{path}: {field} is {actual[field]!r}; expected {wanted_value!r}"
            )
    instructions = data.get("developer_instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        errors.append(f"{path}: developer_instructions must be a non-empty string")
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{path}: description must be a non-empty string")
    return errors


def validate_sources(
    profiles: dict[str, dict[str, Any]], source_dir: Path = SOURCE_DIR
) -> list[str]:
    errors: list[str] = []
    for name, expected in profiles.items():
        errors.extend(validate_profile(source_dir / expected["filename"], name, expected))
    return errors


def classify_destination(
    profiles: dict[str, dict[str, Any]],
    destination: Path,
    source_dir: Path = SOURCE_DIR,
) -> list[tuple[str, str, Path, Path]]:
    result: list[tuple[str, str, Path, Path]] = []
    for name, expected in profiles.items():
        source = source_dir / expected["filename"]
        target = destination / expected["filename"]
        if not target.exists():
            status = "missing"
        elif not target.is_file():
            status = "conflict"
        elif target.read_bytes() == source.read_bytes():
            status = "current"
        else:
            status = "conflict"
        result.append((name, status, source, target))
    return result


def verify_destination(
    profiles: dict[str, dict[str, Any]], destination: Path
) -> list[str]:
    errors: list[str] = []
    for name, expected in profiles.items():
        target = destination / expected["filename"]
        if not target.is_file():
            errors.append(f"{target}: profile is missing")
            continue
        errors.extend(validate_profile(target, name, expected))
    return errors


def install_missing(entries: list[tuple[str, str, Path, Path]], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for _, status, source, target in entries:
        if status != "missing":
            continue
        with target.open("xb") as output:
            output.write(source.read_bytes())


def main() -> int:
    args = parse_args()
    try:
        profiles = load_manifest()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    source_errors = validate_sources(profiles)
    if source_errors:
        print("Canonical profile validation failed:", file=sys.stderr)
        for error in source_errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    destination = destination_for(args)
    if args.verify:
        errors = verify_destination(profiles, destination)
        if errors:
            print(f"Profile verification failed: {destination}", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print(f"Verified {len(profiles)} Team Mode profiles: {destination}")
        return 0

    entries = classify_destination(profiles, destination)
    print(f"Team Mode profile preflight: {destination}")
    for name, status, _, target in entries:
        print(f"- {status:<8} {name}: {target}")

    conflicts = [entry for entry in entries if entry[1] == "conflict"]
    if conflicts:
        print(
            "Installation stopped because existing files differ; no files were written.",
            file=sys.stderr,
        )
        return 1

    missing = [entry for entry in entries if entry[1] == "missing"]
    if not args.apply:
        print(f"Dry run only: {len(missing)} profile(s) would be installed. Pass --apply to write them.")
        return 0

    install_missing(entries, destination)
    errors = verify_destination(profiles, destination)
    if errors:
        print("Post-install verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    print(f"Installed and verified {len(missing)} missing profile(s); existing files were not overwritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
