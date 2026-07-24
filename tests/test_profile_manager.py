from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "manage_profiles.py"
SPEC = importlib.util.spec_from_file_location("manage_profiles", SCRIPT)
assert SPEC and SPEC.loader
manage_profiles = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manage_profiles)


class ProfileManagerTests(unittest.TestCase):
    def test_canonical_profiles_match_manifest(self) -> None:
        profiles = manage_profiles.load_manifest()
        self.assertEqual(manage_profiles.validate_sources(profiles), [])

    def test_manifest_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            linked_manifest = Path(directory) / "profiles.json"
            linked_manifest.symlink_to(manage_profiles.MANIFEST_PATH)
            with self.assertRaises(ValueError):
                manage_profiles.load_manifest(linked_manifest)

    def test_source_profile_symlink_is_rejected(self) -> None:
        profiles = manage_profiles.load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory) / "agents"
            source_dir.mkdir()
            for name, expected in profiles.items():
                target = source_dir / expected["filename"]
                canonical = ROOT / "agents" / expected["filename"]
                if name == "Explorer":
                    target.symlink_to(canonical)
                else:
                    target.write_bytes(canonical.read_bytes())

            errors = manage_profiles.validate_sources(profiles, source_dir)
            self.assertTrue(
                any("Explorer.toml" in error and "symlink" in error for error in errors)
            )

    def test_install_missing_never_replaces_existing_files(self) -> None:
        profiles = manage_profiles.load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / ".codex" / "agents"
            destination.mkdir(parents=True)
            protected = destination / "Explorer.toml"
            protected.write_text("user-owned = true\n", encoding="utf-8")

            entries = manage_profiles.classify_destination(profiles, destination)
            statuses = {name: status for name, status, _, _ in entries}
            self.assertEqual(statuses["Explorer"], "conflict")

            manage_profiles.install_missing(entries, destination)
            self.assertEqual(protected.read_text(encoding="utf-8"), "user-owned = true\n")
            self.assertTrue((destination / "Executor.toml").is_file())

    def test_installed_profiles_verify_after_clean_preflight(self) -> None:
        profiles = manage_profiles.load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / ".codex" / "agents"
            entries = manage_profiles.classify_destination(profiles, destination)
            self.assertTrue(all(status == "missing" for _, status, _, _ in entries))
            manage_profiles.install_missing(entries, destination)
            self.assertEqual(manage_profiles.verify_destination(profiles, destination), [])

    def test_profile_symlink_is_always_a_conflict(self) -> None:
        profiles = manage_profiles.load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / ".codex" / "agents"
            destination.mkdir(parents=True)
            external = root / "external.toml"
            external.write_bytes((ROOT / "agents" / "Explorer.toml").read_bytes())
            linked = destination / "Explorer.toml"
            linked.symlink_to(external)

            entries = manage_profiles.classify_destination(profiles, destination)
            statuses = {name: status for name, status, _, _ in entries}
            self.assertEqual(statuses["Explorer"], "conflict")
            self.assertTrue(
                any(
                    "symlink" in error
                    for error in manage_profiles.verify_destination(profiles, destination)
                )
            )

    def test_destination_directory_symlink_is_rejected(self) -> None:
        profiles = manage_profiles.load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            external = root / "external"
            external.mkdir()
            linked_parent = project / ".codex"
            linked_parent.symlink_to(external, target_is_directory=True)
            destination = linked_parent / "agents"

            errors = manage_profiles.validate_destination_path(destination)
            self.assertTrue(
                any(
                    str(linked_parent) in error and "symlink" in error
                    for error in errors
                )
            )
            with self.assertRaises(ValueError):
                manage_profiles.install_missing(
                    manage_profiles.classify_destination(profiles, destination),
                    destination,
                )


if __name__ == "__main__":
    unittest.main()
