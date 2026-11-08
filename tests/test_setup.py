import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "qilin-fit" / "scripts" / "setup.py"
SPEC = importlib.util.spec_from_file_location("qilin_setup", SCRIPT)
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = mock.patch.dict(os.environ)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop("CODEX_HOME", None)

    def configure(self, decision="ask", agents=("all",), dry_run=False):
        return setup.configure_project(self.project, agents, decision, dry_run)

    def global_config(self, decision="ask", agents=setup.GLOBAL_AGENTS, dry_run=False):
        return setup.configure_global(self.home, agents, decision, dry_run)

    def state(self):
        return json.loads((self.project / ".qilin-fit.json").read_text())

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_non_tty_does_not_ask_or_write(self):
        with mock.patch.object(setup.sys.stdin, "isatty", return_value=False), mock.patch("builtins.input", side_effect=AssertionError):
            result = self.configure()
        self.assertEqual(result["decision"], "unknown")
        self.assertTrue(result["needsConfirmation"])
        self.assertEqual(self.snapshot(), {})

    def test_tty_yes_enables_all_and_strict_state(self):
        with mock.patch.object(setup.sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value="y"):
            result = self.configure()
        self.assertEqual(result["decision"], "enabled")
        self.assertEqual(self.state(), {"schemaVersion": 1, "decision": "enabled"})
        self.assertEqual(len(result["changed"]), 5)
        for filename in dict.fromkeys(setup.PROJECT_FILES.values()):
            self.assertIn("qilin-fit:project:begin", (self.project / filename).read_text())

    def test_tty_no_persists_disabled_without_rule_files(self):
        with mock.patch.object(setup.sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value="n"):
            result = self.configure()
        self.assertEqual(result["decision"], "disabled")
        self.assertEqual(list(self.project.iterdir()), [self.project / ".qilin-fit.json"])

    def test_defer_empty_and_eof_leave_no_files(self):
        for answer in ("l", "", "maybe", EOFError(), KeyboardInterrupt()):
            kwargs = {"side_effect": answer} if isinstance(answer, BaseException) else {"return_value": answer}
            with self.subTest(answer=answer), mock.patch.object(setup.sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", **kwargs):
                self.assertTrue(self.configure()["needsConfirmation"])
                self.assertEqual(self.snapshot(), {})

    def test_known_enabled_does_not_ask_and_repairs_selected_rules(self):
        self.configure("enable", ("codex",))
        with mock.patch("builtins.input", side_effect=AssertionError):
            result = self.configure(agents=("claude",))
        self.assertEqual(result["decision"], "enabled")
        self.assertEqual(result["changed"], [str(self.project / "CLAUDE.md")])
        self.assertFalse((self.project / "CODEBUDDY.md").exists())

    def test_known_disabled_never_asks_or_enables(self):
        self.configure("disable")
        with mock.patch("builtins.input", side_effect=AssertionError):
            self.assertEqual(self.configure()["changed"], [])
        self.assertFalse((self.project / "AGENTS.md").exists())

    def test_enable_is_idempotent(self):
        self.configure("enable")
        before = self.snapshot()
        self.assertEqual(self.configure("enable")["changed"], [])
        self.assertEqual(self.snapshot(), before)

    def test_status_is_read_only_even_when_rules_missing(self):
        self.configure("enable", ("codex",))
        before = self.snapshot()
        with mock.patch("builtins.input", side_effect=AssertionError):
            self.assertEqual(self.configure("status")["changed"], [])
        self.assertEqual(before, self.snapshot())

    def test_dry_run_reports_without_prompt_or_writes(self):
        with mock.patch("builtins.input", side_effect=AssertionError):
            self.assertTrue(self.configure(dry_run=True)["needsConfirmation"])
            result = self.configure("enable", dry_run=True)
        self.assertEqual(len(result["changed"]), 5)
        self.assertEqual(self.snapshot(), {})

    def test_transitions_and_reset_clean_all_agents_not_only_selected(self):
        self.configure("enable")
        self.configure("disable", ("codex",))
        for filename in dict.fromkeys(setup.PROJECT_FILES.values()):
            self.assertEqual((self.project / filename).read_bytes(), b"")
        self.assertEqual(self.state()["decision"], "disabled")
        self.configure("enable")
        self.configure("reset", ("claude",))
        self.assertEqual(self.state()["decision"], "unknown")
        for filename in dict.fromkeys(setup.PROJECT_FILES.values()):
            self.assertEqual((self.project / filename).read_bytes(), b"")
        with mock.patch.object(setup.sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value="y") as prompt:
            self.configure()
        prompt.assert_called_once()

    def test_crlf_and_non_utf8_outside_blocks_are_preserved(self):
        for filename in dict.fromkeys(setup.PROJECT_FILES.values()):
            path = self.project / filename
            original = b"# user\r\n\xff keep\r\n"
            path.write_bytes(original)
        self.configure("enable")
        for filename in dict.fromkeys(setup.PROJECT_FILES.values()):
            path = self.project / filename
            data = path.read_bytes()
            self.assertTrue(data.startswith(original))
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
            path.write_bytes(data + b"after\r\n")
        self.configure("enable")
        self.configure("disable")
        for filename in dict.fromkeys(setup.PROJECT_FILES.values()):
            self.assertEqual((self.project / filename).read_bytes(), original + b"after\r\n")

    def test_no_newline_outside_content_stays_unchanged(self):
        path = self.project / "AGENTS.md"
        path.write_bytes(b"keep-without-newline")
        self.configure("enable", ("codex",))
        self.assertTrue(path.read_bytes().startswith(b"keep-without-newline\n"))
        self.assertEqual(self.configure("enable", ("codex",))["changed"], [])

    def test_bad_markers_preflight_all_files_before_writing(self):
        begin = b"<!-- qilin-fit:project:begin -->\n"
        end = b"<!-- qilin-fit:project:end -->\n"
        for content in (begin, end, end + begin, begin + begin + end, b"<!-- qilin-fit:project:typo -->\n", b"prefix " + begin + end):
            with self.subTest(content=content):
                path = self.project / "AGENTS.md"
                path.write_bytes(content)
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    self.configure("enable", ("codebuddy",))
                self.assertEqual(before, self.snapshot())

    def test_corrupt_or_unknown_state_never_overwritten(self):
        path = self.project / ".qilin-fit.json"
        for content in (b"", b"{broken", b"[]", b'{"schemaVersion": 2, "decision": "enabled"}', b'{"schemaVersion": true, "decision": "enabled"}', b'{"schemaVersion": 1, "decision": "maybe"}', b'{"schemaVersion": 1, "decision": "enabled", "path": "x"}'):
            with self.subTest(content=content):
                path.write_bytes(content)
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    self.configure("enable")
                self.assertEqual(before, self.snapshot())

    def test_duplicate_state_keys_rejected_by_status_and_ask_without_writes(self):
        path = self.project / ".qilin-fit.json"
        contents = (
            b'{"schemaVersion":1,"decision":"disabled","decision":"enabled"}',
            b'{"schemaVersion":2,"schemaVersion":1,"decision":"enabled"}',
        )
        for content in contents:
            for decision in ("status", "ask"):
                with self.subTest(content=content, decision=decision):
                    path.write_bytes(content)
                    before = self.snapshot()
                    with mock.patch("builtins.input", side_effect=AssertionError), self.assertRaises(ValueError):
                        self.configure(decision)
                    self.assertEqual(before, self.snapshot())
                    self.assertEqual(list(self.project.iterdir()), [path])

    def test_symlink_directory_and_hardlink_targets_rejected(self):
        path = self.project / "AGENTS.md"
        outside = self.root / "outside"
        outside.write_bytes(b"safe")
        path.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.configure("enable", ("codebuddy",))
        self.assertEqual(outside.read_bytes(), b"safe")
        path.unlink()
        path.mkdir()
        with self.assertRaises(ValueError):
            self.configure("enable")
        path.rmdir()
        os.link(outside, path)
        with self.assertRaises(ValueError):
            self.configure("enable")
        self.assertFalse((self.project / ".qilin-fit.json").exists())

    def test_symlink_state_rejected(self):
        outside = self.root / "state"
        outside.write_text('{"schemaVersion":1,"decision":"unknown"}')
        (self.project / ".qilin-fit.json").symlink_to(outside)
        with self.assertRaises(ValueError):
            self.configure("enable")

    def test_permissions_are_preserved_on_atomic_replace(self):
        rules = self.project / "AGENTS.md"
        rules.write_bytes(b"user\n")
        rules.chmod(0o640)
        self.configure("enable")
        self.assertEqual(stat.S_IMODE(rules.stat().st_mode), 0o640)
        state_path = self.project / ".qilin-fit.json"
        state_path.chmod(0o600)
        self.configure("disable")
        self.assertEqual(stat.S_IMODE(state_path.stat().st_mode), 0o600)

    def test_write_failure_does_not_write_enabled_state(self):
        original = setup._write
        def fail_rules(path, data):
            if path.name == "CLAUDE.md":
                raise OSError("simulated")
            return original(path, data)
        with mock.patch.object(setup, "_write", side_effect=fail_rules), self.assertRaises(OSError):
            self.configure("enable")
        self.assertFalse((self.project / ".qilin-fit.json").exists())

    def test_skill_directory_rejected_and_missing_target_rejected(self):
        with self.assertRaises(ValueError):
            setup.configure_project(SCRIPT.parent, ("all",), "enable")
        with self.assertRaises(ValueError):
            setup.configure_project(self.root / "missing", ("all",), "enable")

    def test_handwritten_legacy_rules_are_not_removed(self):
        path = self.project / "AGENTS.md"
        path.write_text("User handwritten qilin-fit rules\n")
        result = self.configure("disable")
        self.assertTrue(result["notes"])
        self.assertEqual(path.read_text(), "User handwritten qilin-fit rules\n")

    def test_new_codebuddy_preserves_existing_agents_inheritance(self):
        agents = self.project / "AGENTS.md"
        original = b"# Existing agent instructions\r\nkeep these\r\n"
        agents.write_bytes(original)
        self.configure("enable", ("codebuddy",))
        rules = self.project / "CODEBUDDY.md"
        self.assertIn(b"@AGENTS.md", rules.read_bytes())
        self.assertEqual(agents.read_bytes(), original)
        before = rules.read_bytes()
        self.assertEqual(self.configure("enable", ("codebuddy",))["changed"], [])
        self.assertEqual(rules.read_bytes(), before)
        self.configure("disable")
        self.assertEqual(agents.read_bytes(), original)
        self.assertEqual(rules.read_bytes(), b"@AGENTS.md\r\n\r\n")

    def test_project_alternate_configurations_are_reported(self):
        for agent, directory in (("codebuddy", ".codebuddy"), ("claude", ".claude")):
            path = self.project / directory / setup.PROJECT_FILES[agent]
            path.parent.mkdir()
            path.write_text("User configuration\n")
        result = self.configure("enable")
        self.assertEqual(len([note for note in result["notes"] if "并行配置" in note]), 2)

    def test_global_parent_symlink_rejected_before_any_writes(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.home / ".codex").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.global_config("enable")
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.home / ".codebuddy").exists())

    def test_global_non_directory_parent_rejected_before_writes(self):
        (self.home / ".claude").write_bytes(b"not a directory")
        with self.assertRaises(ValueError):
            self.global_config("enable")
        self.assertFalse((self.home / ".codebuddy").exists())

    def test_codex_home_symlink_and_ancestor_symlink_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root / "linked"
        link.symlink_to(outside, target_is_directory=True)
        for custom in (link, link / "nested"):
            os.environ["CODEX_HOME"] = str(custom)
            with self.subTest(custom=custom), self.assertRaises(ValueError):
                self.global_config("enable")
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.home / ".codebuddy").exists())

    def test_codex_override_prevents_claiming_global_success(self):
        path = self.home / ".codex" / "AGENTS.override.md"
        path.parent.mkdir()
        path.write_text("higher priority instructions\n")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "遮蔽"):
            self.global_config("enable")
        self.assertEqual(self.snapshot(), before)
        result = self.global_config("status")
        self.assertEqual(result["decision"], "unknown")
        self.assertTrue(any("遮蔽" in note for note in result["notes"]))
        path.write_text(" \n")
        self.global_config("enable")
        self.assertEqual(self.global_config("status")["decision"], "enabled")

    def test_global_ctrl_c_is_defer_without_writes(self):
        with mock.patch.object(setup.sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", side_effect=KeyboardInterrupt):
            self.assertTrue(self.global_config()["needsConfirmation"])
        self.assertEqual(self.snapshot(), {})

    def test_global_ask_requires_consent_and_lists_paths(self):
        with mock.patch.object(setup.sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value="n") as prompt:
            result = self.global_config()
        self.assertEqual(self.snapshot(), {})
        self.assertFalse(result["needsConfirmation"])
        text = prompt.call_args[0][0]
        self.assertIn("以后项目", text)
        self.assertIn(str(self.home / ".codex" / "AGENTS.md"), text)
        with mock.patch.object(setup.sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value="y"):
            result = self.global_config()
        self.assertEqual(result["decision"], "enabled")
        self.assertEqual(len(result["changed"]), 4)

    def test_global_refusal_preserves_existing_enabled_files(self):
        self.global_config("enable")
        before = self.snapshot()
        with mock.patch.object(setup.sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value="n"):
            result = self.global_config()
        self.assertEqual(result["decision"], "enabled")
        self.assertEqual(result["changed"], [])
        self.assertEqual(before, self.snapshot())

    def test_global_symlink_target_rejected_before_other_writes(self):
        outside = self.root / "outside"
        outside.write_bytes(b"safe")
        path = self.home / ".codex" / "AGENTS.md"
        path.parent.mkdir()
        path.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.global_config("enable")
        self.assertEqual(outside.read_bytes(), b"safe")
        self.assertFalse((self.home / ".codebuddy").exists())

    def test_global_non_tty_defer_and_dry_run_do_not_write(self):
        with mock.patch.object(setup.sys.stdin, "isatty", return_value=False), mock.patch("builtins.input", side_effect=AssertionError):
            self.assertTrue(self.global_config()["needsConfirmation"])
            self.assertTrue(self.global_config(dry_run=True)["needsConfirmation"])
            self.assertEqual(len(self.global_config("enable", dry_run=True)["changed"]), 4)
        self.assertEqual(self.snapshot(), {})

    def test_global_content_is_reminder_not_skill_or_hook(self):
        self.global_config("enable")
        for path in (self.home / ".codebuddy" / "CODEBUDDY.md", self.home / ".claude" / "CLAUDE.md", self.home / ".codex" / "AGENTS.md", self.home / ".gemini" / "GEMINI.md"):
            content = path.read_text()
            for text in ("qilin-fit:reminder:begin", "不是 hook", "用户对话", "--decision enable/disable", "不反复追问", "全局指令目录与 Skill 目录不同"):
                self.assertIn(text, content)
            self.assertNotIn("qilin-fit:project:begin", content)
        self.assertFalse(list(self.home.rglob("SKILL.md")))
        self.assertFalse(list(self.home.rglob("settings.json")))

    def test_global_idempotence_status_reset_and_crlf(self):
        path = self.home / ".claude" / "CLAUDE.md"
        path.parent.mkdir()
        path.write_bytes(b"user\r\n")
        self.global_config("enable")
        before = self.snapshot()
        self.assertEqual(self.global_config("enable")["changed"], [])
        self.assertEqual(self.global_config("status")["decision"], "enabled")
        self.assertEqual(before, self.snapshot())
        self.assertNotIn(b"\n", path.read_bytes().replace(b"\r\n", b""))
        self.global_config("reset")
        self.assertEqual(path.read_bytes(), b"user\r\n")
        self.assertTrue(path.exists())
        self.assertEqual(self.global_config("status")["decision"], "disabled")

    def test_codex_home_is_supported_without_touching_default(self):
        custom = self.root / "custom-codex"
        os.environ["CODEX_HOME"] = str(custom)
        self.global_config("enable", ("codex",))
        self.assertTrue((custom / "AGENTS.md").exists())
        self.assertFalse((self.home / ".codex").exists())

    def test_global_bad_marker_preflights_before_creating_others(self):
        path = self.home / ".codex" / "AGENTS.md"
        path.parent.mkdir()
        path.write_bytes(b"<!-- qilin-fit:reminder:begin -->\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.global_config("enable")
        self.assertEqual(before, self.snapshot())

    def test_shared_agents_file_is_written_once_and_reused_without_prompt(self):
        result = self.configure("enable", ("codex", "hermes", "openclaw"))
        rules = self.project / "AGENTS.md"
        self.assertEqual(result["changed"], [str(rules), str(self.project / ".qilin-fit.json")])
        self.assertEqual(rules.read_text().count("qilin-fit:project:begin"), 1)
        with mock.patch("builtins.input", side_effect=AssertionError):
            self.assertEqual(self.configure(agents=("hermes", "openclaw"))["changed"], [])
            self.assertEqual(self.configure(agents=("gemini",))["changed"], [str(self.project / "GEMINI.md")])
        self.assertTrue(any("workspace" in note for note in result["notes"]))

    def test_unsupported_global_clients_rejected_without_partial_writes(self):
        for agents in (("all",), ("hermes",), ("openclaw",), ("codebuddy", "hermes")):
            for decision in setup.DECISIONS:
                with self.subTest(agents=agents, decision=decision), self.assertRaisesRegex(ValueError, "用户级提醒"):
                    self.global_config(decision, agents)
                self.assertEqual(self.snapshot(), {})

    def test_gemini_global_preserves_content_and_permissions(self):
        path = self.home / ".gemini" / "GEMINI.md"
        path.parent.mkdir()
        path.write_bytes(b"user\r\n")
        path.chmod(0o640)
        self.global_config("enable", ("gemini",))
        self.assertEqual(self.global_config("enable", ("gemini",))["changed"], [])
        self.assertNotIn(b"\n", path.read_bytes().replace(b"\r\n", b""))
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        self.global_config("disable", ("gemini",))
        self.assertEqual(path.read_bytes(), b"user\r\n")

    def test_gemini_bad_marker_and_link_preflight_before_any_writes(self):
        path = self.home / ".gemini" / "GEMINI.md"
        path.parent.mkdir()
        path.write_bytes(b"<!-- qilin-fit:reminder:begin -->\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.global_config("enable")
        self.assertEqual(before, self.snapshot())
        path.unlink()
        outside = self.root / "outside"
        outside.write_bytes(b"safe")
        path.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.global_config("enable")
        self.assertEqual(outside.read_bytes(), b"safe")
        self.assertFalse((self.home / ".codebuddy").exists())

    def test_cli_requires_exclusive_project_or_global_mode(self):
        for arguments in ([], ["--target", str(self.project), "--global-reminder"], ["--home", str(self.home)]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                setup.main(arguments)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(["--target", str(self.project), "--agent", "codex", "--decision", "enable", "--dry-run"]), 0)
        self.assertEqual(self.snapshot(), {})


if __name__ == "__main__":
    unittest.main()
