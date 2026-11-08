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
PROJECT_AGENTS = ("codebuddy", "claude", "codex", "gemini")
PROJECT_ARGS = [argument for agent in PROJECT_AGENTS for argument in ("--agent", agent)]


class InstallerTests(unittest.TestCase):
    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = installer.install(directory, ["all"], dry_run=True, scope="user")
            self.assertEqual(len(paths), 6)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_install_all_user_paths_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = installer.install(directory, ["all"], scope="user")
            self.assertEqual([path.relative_to(Path(directory).resolve()).as_posix() for path in paths], [
                ".codebuddy/skills/qilin-fit", ".claude/skills/qilin-fit", ".agents/skills/qilin-fit",
                ".gemini/skills/qilin-fit", ".hermes/skills/qilin-fit", ".openclaw/skills/qilin-fit",
            ])
            payload = {path.relative_to(installer.SOURCE) for path in installer.SOURCE.rglob("*")
                       if path.is_file() and "__pycache__" not in path.parts and path.name != ".DS_Store"}
            for path in paths:
                for relative in payload:
                    self.assertEqual((path / relative).read_bytes(), (installer.SOURCE / relative).read_bytes())
            with self.assertRaises(FileExistsError):
                installer.install(directory, ["all"], scope="user")

    def test_project_install_four_discovery_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = installer.install(directory, PROJECT_AGENTS)
            self.assertEqual(len(paths), 4)
            self.assertEqual(paths[-1], Path(directory).resolve() / ".gemini/skills/qilin-fit")

    def test_unsupported_project_scope_never_writes(self):
        for agents in (["hermes"], ["openclaw"], ["codebuddy", "hermes"], ["all"]):
            with self.subTest(agents=agents), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "项目级"):
                    installer.install(directory, agents)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_unknown_agent_and_scope_never_write(self):
        with tempfile.TemporaryDirectory() as directory:
            for agents, scope in ((["unknown"], "user"), (["codex"], "unknown")):
                with self.assertRaises(ValueError):
                    installer.install(directory, agents, scope=scope)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_preflight_checks_all_agents(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / ".openclaw" / "skills" / installer.NAME
            existing.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                installer.install(directory, ["all"], scope="user")
            self.assertFalse((Path(directory) / ".codebuddy").exists())

    def test_refuse_symlink_parent(self):
        for agent in installer.DIRECTORIES:
            with self.subTest(agent=agent), tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
                (Path(directory) / installer.DIRECTORIES[agent]).symlink_to(outside, target_is_directory=True)
                with self.assertRaises(ValueError):
                    installer.install(directory, [agent], scope="user")
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
                    installer.install(outside, PROJECT_AGENTS)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_cli_noninteractive_keeps_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-B", str(Path(installer.__file__)), "--target", directory, *PROJECT_ARGS], input="", text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((Path(directory) / ".qilin-fit.json").exists())
            self.assertFalse((Path(directory) / "AGENTS.md").exists())
            self.assertIn("待用户确认", result.stdout)
            self.assertTrue((Path(directory) / ".gemini/skills/qilin-fit/scripts/setup.py").is_file())

    def test_cli_explicit_enable_and_disable(self):
        for decision in ("enable", "disable"):
            with tempfile.TemporaryDirectory() as directory:
                result = subprocess.run([sys.executable, "-B", str(Path(installer.__file__)), "--target", directory, *PROJECT_ARGS, "--decision", decision], input="", text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                state = json.loads((Path(directory) / ".qilin-fit.json").read_text())
                self.assertEqual(state["decision"], "enabled" if decision == "enable" else "disabled")
                for filename in ("AGENTS.md", "GEMINI.md"):
                    self.assertEqual((Path(directory) / filename).exists(), decision == "enable")

    def test_cli_dry_run_does_not_configure(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-B", str(Path(installer.__file__)), "--target", directory, *PROJECT_ARGS, "--decision", "enable", "--dry-run"], input="", text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_user_scope_dry_run_never_writes_home(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(installer.Path, "home", return_value=Path(directory)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(["--scope", "user", *PROJECT_ARGS, "--global-reminder", "--dry-run"]), 0)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_unsupported_reminder_preflight_before_copy(self):
        for arguments in (["--agent", "all"], ["--agent", "hermes"], ["--agent", "codex", "--agent", "openclaw"]):
            with tempfile.TemporaryDirectory() as directory:
                with patch.object(installer.Path, "home", return_value=Path(directory)), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(installer.main(["--scope", "user", *arguments, "--global-reminder"]), 2)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_user_scope_installs_without_implicit_global_change(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(installer.Path, "home", return_value=Path(directory)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(["--scope", "user", "--agent", "all"]), 0)
            self.assertTrue((Path(directory) / ".openclaw/skills/qilin-fit/SKILL.md").is_file())
            for path in (".codebuddy/CODEBUDDY.md", ".claude/CLAUDE.md", ".codex/AGENTS.md", ".gemini/GEMINI.md", ".hermes/AGENTS.md", ".openclaw/AGENTS.md", ".qilin-fit.json"):
                self.assertFalse((Path(directory) / path).exists(), path)

    def test_deduplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(len(installer.install(directory, ["codex", "codex"], dry_run=True)), 1)


if __name__ == "__main__":
    unittest.main()
