import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from cachesade.core import RULES, CacheRule, clean_result, resolve_rule_paths, scan_rule


class CoreTests(unittest.TestCase):
    def test_scan_and_clean_only_exact_rule_root(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            known = root / "Local" / "NVIDIA" / "DXCache"
            unknown = root / "Local" / "SomeApp" / "Cache"
            known.mkdir(parents=True)
            unknown.mkdir(parents=True)
            (known / "shader.bin").write_bytes(b"x" * 2048)
            (unknown / "keep.bin").write_bytes(b"keep")
            env = self._env(root)
            rule = CacheRule("test", "Test", "Test", ("{LOCALAPPDATA}/NVIDIA/DXCache",), "")

            result = scan_rule(rule, env)
            self.assertEqual(result.size_bytes, 2048)
            outcome = clean_result(result)

            self.assertEqual(outcome.deleted_files, 1)
            self.assertFalse((known / "shader.bin").exists())
            self.assertTrue((unknown / "keep.bin").exists())
            self.assertTrue(known.exists(), "Known root folder must be preserved")

    def test_temp_rule_only_counts_files_at_least_seven_days_old(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            temp = root / "Temp"
            temp.mkdir()
            old_file = temp / "old.tmp"
            recent_file = temp / "recent.tmp"
            old_file.write_bytes(b"old")
            recent_file.write_bytes(b"recent")
            now = time.time()
            os.utime(old_file, (now - 8 * 86400, now - 8 * 86400))
            env = self._env(root)
            temp_rule = next(rule for rule in RULES if rule.key == "user-temp")

            result = scan_rule(temp_rule, env, now=now)
            self.assertEqual(result.file_count, 1)
            clean_result(result, now=now)

            self.assertFalse(old_file.exists())
            self.assertTrue(recent_file.exists())

    def test_epic_glob_is_limited_to_direct_webcache_children(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            saved = root / "Local" / "EpicGamesLauncher" / "Saved"
            (saved / "webcache_4430").mkdir(parents=True)
            (saved / "Logs").mkdir()
            env = self._env(root)
            rule = next(rule for rule in RULES if rule.key == "epic")

            paths = resolve_rule_paths(rule, env)

            self.assertEqual(paths, ((saved / "webcache_4430").resolve(),))

    def test_locked_file_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            cache = root / "Local" / "NVIDIA" / "DXCache"
            cache.mkdir(parents=True)
            locked = cache / "locked.bin"
            locked.write_bytes(b"locked")
            env = self._env(root)
            rule = CacheRule("test", "Test", "Test", ("{LOCALAPPDATA}/NVIDIA/DXCache",), "")
            result = scan_rule(rule, env)

            with patch.object(Path, "unlink", side_effect=PermissionError("in use")):
                outcome = clean_result(result)

            self.assertEqual(outcome.deleted_files, 0)
            self.assertEqual(len(outcome.skipped), 1)
            self.assertTrue(locked.exists())

    @staticmethod
    def _env(root: Path) -> dict[str, str]:
        return {
            "USERPROFILE": str(root / "User"),
            "LOCALAPPDATA": str(root / "Local"),
            "APPDATA": str(root / "Roaming"),
            "TEMP": str(root / "Temp"),
        }


if __name__ == "__main__":
    unittest.main()

