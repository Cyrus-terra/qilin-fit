import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/qilin-fit/scripts/compat_audit.py"
SPEC = importlib.util.spec_from_file_location("compat_audit", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class CompatAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=cwd,
                              text=True, capture_output=True, check=False)

    def test_unknown_baseline_and_shape(self):
        path = self.put("demo.js", "structuredClone({})")
        result = self.run_cli(path, "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["baseline"], {"minChromium": None, "status": "unknown"})
        self.assertEqual(data["summary"]["warnings"], 1)
        item = data["findings"][0]
        self.assertTrue({"filename", "line", "column", "rule", "severity", "requiredChrome",
                         "message", "excerpt", "evidence"} <= set(item))
        self.assertTrue(all(rule["evidence"].startswith("https://") for rule in data["rules"]))
        self.assertIn("不是兼容性认证", data["limitations"])

    def test_supported_at_102_not_reported(self):
        text = "obj?.x ?? 0; obj.findLast(x => x); @layer x {} @property --x {}"
        self.assertEqual(AUDIT.scan_text(Path("app.js"), text, 102), [])

    def test_threshold_boundary_and_location(self):
        text = "/* heading */\n.a { color: oklch(0.8 0.1 20) }"
        item = AUDIT.scan_text(Path("a.css"), text, 110)[0]
        self.assertEqual((item["line"], item["column"], item["requiredChrome"]), (2, 13, 111))
        self.assertEqual(item["severity"], "error")
        self.assertEqual(AUDIT.scan_text(Path("a.css"), text, 111), [])

    def test_modern_css_candidates(self):
        text = ("@container x { .a:has(b) {height:100dvh; width:2cqw; translate:2px;"
                "color:color-mix(in oklab, red, blue);background:light-dark(red,blue);"
                "anchor-name:--a; & .child {color:lab(20 1 2)}}}")
        ids = {x["rule"] for x in AUDIT.scan_text(Path("a.css"), text, 102)}
        self.assertTrue({"css-container-query", "css-has", "css-dynamic-viewport",
                         "css-container-units", "css-independent-transform", "css-color-mix",
                         "css-light-dark", "css-anchor-position", "css-nesting", "css-lab"} <= ids)

    def test_small_large_dynamic_viewport_units(self):
        for prefix in "dsl":
            for dimension in ("h", "w", "i", "b", "min", "max"):
                text = "a{height:10" + prefix + "v" + dimension + "}"
                self.assertEqual(AUDIT.scan_text(Path("a.css"), text, 107)[0]["requiredChrome"], 108)
                self.assertEqual(AUDIT.scan_text(Path("a.css"), text, 108), [])

    def test_tailwind_has_named_variants(self):
        for variant in ("has-[a]", "has-data-[selected]", "group-has-data-[active]",
                        "peer-has-checked", "in-has-[a]", "hover:has-focus"):
            text = '<div class="' + variant + ':bg-red-500">'
            self.assertEqual(AUDIT.scan_text(Path("a.html"), text, 102)[0]["rule"], "css-has")
            self.assertEqual(AUDIT.scan_text(Path("a.html"), text, 105), [])

    def test_symlink_ancestor_before_dotdot_normalization(self):
        self.put("actual/a.css", "a{height:100svh}")
        (self.root / "link").symlink_to(self.root / "actual", target_is_directory=True)
        for suffix in ("link/a.css", "link/../actual/a.css"):
            report = AUDIT.audit([str(self.root) + "/" + suffix], 102)
            self.assertEqual(report["summary"]["filesScanned"], 0)
            self.assertEqual(report["skipped"][0]["reason"], "symlink-not-followed")
        self.assertEqual(AUDIT.audit([str(self.root / "actual/a.css")], 102)["summary"]["filesScanned"], 1)

    def test_package_json_only_and_tailwind_versions(self):
        for version, expected in (("^4.0.0", 1), ("~4.1.2", 1), ("^3.4.0", 0)):
            text = json.dumps({"devDependencies": {"tailwindcss": version}})
            self.assertEqual(len(AUDIT.scan_text(Path("package.json"), text, 102)), expected)
            self.assertEqual(AUDIT.scan_text(Path("other.json"), text, 102), [])
            self.assertEqual(AUDIT.scan_text(Path("package.json"), text, 111), [])
        self.assertEqual(AUDIT.scan_text(Path("package.json"), '{"tailwindcss":"4"}', 102), [])
        item = AUDIT.scan_text(Path("app.html"), '<div class="translate-x-2">', 102)[0]
        self.assertEqual(item["severity"], "warning")
        self.assertIn("v3可生成传统transform", item["message"])

    def test_calls_guards_and_minified_files(self):
        path = self.put("app.min.js", 'if (typeof structuredClone === "function") { structuredClone(x) }')
        self.assertEqual(len(AUDIT.audit([str(path)], 97)["findings"]), 1)
        self.assertEqual(AUDIT.scan_text(Path("a.js"), 'const label = "structuredClone";', 80), [])

    def test_skip_build_direct_root_and_include(self):
        path = self.put("dist/app.js", "structuredClone(x)")
        for root in (path.parent, path):
            report = AUDIT.audit([str(root)], 80)
            self.assertEqual(report["summary"]["filesScanned"], 0)
            self.assertIn("excluded-directory:dist", report["skipped"][0]["reason"])
            self.assertEqual(len(AUDIT.audit([str(root)], 80, True)["findings"]), 1)

    def test_ignored_symlinks_large_files_locks_and_maps(self):
        for folder in AUDIT.IGNORE:
            self.put(folder + "/app.js", "structuredClone(x)")
        self.put("large.js", "x" * 51)
        self.put("package-lock.json", "structuredClone(x)")
        self.put("app.js.map", "structuredClone(x)")
        self.put("notes.md", "structuredClone(x)")
        (self.root / "loop").symlink_to(self.root, target_is_directory=True)
        (self.root / "broken.js").symlink_to(self.root / "missing")
        self.put("keep.min.js", "structuredClone(x)")
        self.assertEqual(AUDIT.audit([str(self.root / "loop" / "keep.min.js")], 80)["summary"]["filesScanned"], 0)
        report = AUDIT.audit([str(self.root)], 80, max_file_bytes=50)
        self.assertEqual(report["summary"]["filesScanned"], 1)
        self.assertEqual(report["summary"]["findings"], 1)
        reasons = {x["reason"] for x in report["skipped"]}
        self.assertTrue({"over-max-file-bytes", "symlink-not-followed"} <= reasons)
        self.assertEqual(report["errors"], [])

    def test_exit_statuses_io_invalid_json_and_empty_path(self):
        path = self.put("app.js", "structuredClone(x)")
        for extra, code in (([], 0), (["--fail-on", "warning"], 1),
                            (["--fail-on", "error"], 0),
                            (["--min-chromium", "97", "--fail-on", "error"], 1)):
            self.assertEqual(self.run_cli(path, *extra).returncode, code)
        for bad in ("0", "-1", "unknown", "1.5"):
            self.assertEqual(self.run_cli(path, "--min-chromium", bad).returncode, 2)
        for bad_path in (self.root / "missing", "", self.put("package.json", "{")):
            self.assertEqual(self.run_cli(bad_path, "--format", "json").returncode, 2)
        binary = self.root / "invalid.js"
        binary.write_bytes(b"\xff")
        self.assertEqual(self.run_cli(binary).returncode, 2)

    def test_default_path_multi_path_and_empty_scan(self):
        first = self.put("a.js", "structuredClone(x)")
        second = self.put("b.js", "Array.fromAsync(xs)")
        result = self.run_cli(first, second, "--format", "json")
        self.assertEqual(json.loads(result.stdout)["summary"]["filesScanned"], 2)
        self.assertEqual(self.run_cli(cwd=self.root).returncode, 0)
        empty = self.root / "empty"
        empty.mkdir()
        result = self.run_cli(empty)
        self.assertEqual(result.returncode, 0)
        self.assertIn('"filesScanned": 0', result.stdout)
        self.assertIn("不是兼容性认证", result.stdout)
        self.assertNotIn("PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
