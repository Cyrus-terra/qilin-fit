import importlib.util
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

spec = importlib.util.spec_from_file_location("skill_install", Path(__file__).resolve().parents[1] / "scripts" / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = installer.install(directory, ["all"], dry_run=True)
            self.assertEqual(len(paths), 3)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_install_all_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = installer.install(directory, ["all"])
            for path in paths:
                self.assertEqual((path / "SKILL.md").read_bytes(), (installer.SOURCE / "SKILL.md").read_bytes())
            self.assertEqual(paths[2].parent.parent.name, ".agents")
            with self.assertRaises(FileExistsError):
                installer.install(directory, ["all"])

    def test_preflight_checks_all_agents(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / ".agents" / "skills" / installer.NAME
            existing.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                installer.install(directory, ["all"])
            self.assertFalse((Path(directory) / ".codebuddy").exists())

    def test_refuse_symlink_parent(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            (Path(directory) / ".claude").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                installer.install(directory, ["claude"])
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_refuse_install_inside_source(self):
        for target in (installer.SOURCE, installer.SOURCE / "scripts"):
            with self.assertRaises(ValueError):
                installer.install(target, ["claude"])

    def test_refuse_source_root_symlink(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            source = Path(directory) / "linked-source"
            source.symlink_to(installer.SOURCE, target_is_directory=True)
            with patch.object(installer, "SOURCE", source):
                with self.assertRaises(ValueError):
                    installer.install(outside, ["all"])
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_deduplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(len(installer.install(directory, ["codex", "codex"], dry_run=True)), 1)


if __name__ == "__main__":
    unittest.main()
