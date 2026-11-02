import importlib.util
import contextlib
import io
import json
import subprocess
import sys
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

    def test_cli_noninteractive_keeps_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(Path(installer.__file__)), "--target", directory, "--agent", "all"], input="", text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((Path(directory) / ".qilin-fit.json").exists())
            self.assertFalse((Path(directory) / "AGENTS.md").exists())
            self.assertIn("待用户确认", result.stdout)
            self.assertTrue((Path(directory) / ".agents/skills/qilin-fit/scripts/setup.py").is_file())

    def test_cli_explicit_enable_and_disable(self):
        for decision in ("enable", "disable"):
            with tempfile.TemporaryDirectory() as directory:
                result = subprocess.run([sys.executable, str(Path(installer.__file__)), "--target", directory, "--agent", "all", "--decision", decision], input="", text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                state = json.loads((Path(directory) / ".qilin-fit.json").read_text())
                self.assertEqual(state["decision"], "enabled" if decision == "enable" else "disabled")
                self.assertEqual((Path(directory) / "AGENTS.md").exists(), decision == "enable")

    def test_cli_dry_run_does_not_configure(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(Path(installer.__file__)), "--target", directory, "--agent", "all", "--decision", "enable", "--dry-run"], input="", text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_user_scope_dry_run_never_writes_home(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(installer.Path, "home", return_value=Path(directory)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(["--scope", "user", "--agent", "all", "--global-reminder", "--dry-run"]), 0)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_user_scope_installs_without_implicit_global_change(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(installer.Path, "home", return_value=Path(directory)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(["--scope", "user", "--agent", "all"]), 0)
            self.assertTrue((Path(directory) / ".agents/skills/qilin-fit/SKILL.md").is_file())
            for path in (".codebuddy/CODEBUDDY.md", ".claude/CLAUDE.md", ".codex/AGENTS.md", ".qilin-fit.json"):
                self.assertFalse((Path(directory) / path).exists(), path)

    def test_deduplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(len(installer.install(directory, ["codex", "codex"], dry_run=True)), 1)


if __name__ == "__main__":
    unittest.main()
