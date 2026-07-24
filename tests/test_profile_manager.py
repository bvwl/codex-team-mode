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


if __name__ == "__main__":
    unittest.main()
