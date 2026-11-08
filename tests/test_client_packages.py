import ast
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "skills/qilin-fit/SKILL.md"
VERSION = re.search(r'^  version: "([^"]+)"$', ENTRY.read_text(encoding="utf-8"), re.M).group(1)


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ClientPackageTests(unittest.TestCase):
    def test_manifests_share_name_version_and_payload(self):
        for relative in (".claude-plugin/plugin.json", ".codebuddy-plugin/plugin.json", ".codex-plugin/plugin.json",
                         "gemini-extension.json", "openclaw.plugin.json", "package.json"):
            with self.subTest(relative=relative):
                manifest = read_json(relative)
                self.assertEqual(manifest["name"], "qilin-fit")
                self.assertEqual(manifest["version"], VERSION)
                self.assertNotIn("mcpServers", manifest)
        self.assertEqual(read_json(".codex-plugin/plugin.json")["skills"], "./skills/")
        self.assertEqual(read_json(".codex-plugin/plugin.json")["hooks"], {})
        self.assertEqual(read_json("openclaw.plugin.json")["skills"], ["./skills"])
        self.assertTrue(ENTRY.is_file())
        self.assertFalse((ROOT / "hooks").exists())

    def test_marketplaces_use_local_root(self):
        for relative in (".claude-plugin/marketplace.json", ".codebuddy-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
            marketplace = read_json(relative)
            self.assertEqual(marketplace["name"], "qilin-fit")
            self.assertEqual(len(marketplace["plugins"]), 1)
            plugin = marketplace["plugins"][0]
            self.assertEqual(plugin["name"], "qilin-fit")
            self.assertIn(plugin["source"], ("./", {"source": "local", "path": "./"}))
            if "version" in plugin:
                self.assertEqual(plugin["version"], VERSION)

    def test_hermes_registers_shared_skill_without_hooks(self):
        manifest = (ROOT / ".hermes-plugin/plugin.yaml").read_text(encoding="utf-8")
        self.assertIn("name: qilin-fit\n", manifest)
        self.assertIn("version: " + VERSION + "\n", manifest)
        self.assertNotIn("provides_hooks", manifest)
        adapter = ROOT / ".hermes-plugin/__init__.py"
        ast.parse(adapter.read_text(encoding="utf-8"), feature_version=(3, 9))

        class Context:
            def __init__(self):
                self.skills = []

            def register_skill(self, name, path, description):
                self.skills.append((name, path, description))

            def register_hook(self, *args, **kwargs):
                raise AssertionError("qilin-fit must not install hooks")

        with tempfile.TemporaryDirectory(prefix="qilin 包 ") as directory:
            root = Path(directory)
            shutil.copytree(ROOT / ".hermes-plugin", root / ".hermes-plugin")
            shutil.copytree(ENTRY.parent, root / "skills/qilin-fit")
            spec = importlib.util.spec_from_file_location("qilin_hermes", root / ".hermes-plugin/__init__.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            context = Context()
            module.register(context)
            self.assertEqual(len(context.skills), 1)
            name, path, description = context.skills[0]
            self.assertEqual(name, "qilin-fit")
            self.assertEqual(path.read_bytes(), ENTRY.read_bytes())
            self.assertIn("麒麟", description)
            self.assertFalse((root / ".qilin-fit.json").exists())
            module.ENTRY = root / "missing.md"
            with self.assertRaises(RuntimeError):
                module.register(context)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for the OpenClaw import smoke test")
    def test_openclaw_entry_has_no_dependencies_or_registration_side_effects(self):
        package = read_json("package.json")
        self.assertNotIn("dependencies", package)
        self.assertNotIn("scripts", package)
        self.assertEqual(package["openclaw"]["extensions"], ["./index.js"])
        result = subprocess.run([
            "node", "--input-type=module", "-e",
            'const {default: plugin} = await import(process.argv[1]); '
            'if (plugin.id !== "qilin-fit") throw new Error("wrong plugin"); '
            'plugin.register(new Proxy({}, {get() {throw new Error("unexpected host operation");}}));',
            (ROOT / "index.js").as_uri(),
        ], text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
