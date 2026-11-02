import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "qilin-fit"


class SkillPackageTests(unittest.TestCase):
    def test_required_standard_frontmatter(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        frontmatter = content.split("---\n", 2)[1]
        name = re.search(r"^name: (.+)$", frontmatter, re.M).group(1)
        description = re.search(r"^description: (.+)$", frontmatter, re.M).group(1)
        compatibility = re.search(r"^compatibility: (.+)$", frontmatter, re.M).group(1)
        self.assertEqual(name, SKILL.name)
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertTrue(1 <= len(description) <= 1024)
        self.assertTrue(1 <= len(compatibility) <= 500)
        self.assertNotIn("disable-model-invocation:", frontmatter)

    def test_markdown_local_links_resolve(self):
        for path in [*ROOT.glob("*.md"), *SKILL.rglob("*.md")]:
            text = path.read_text(encoding="utf-8")
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in link or link.startswith("#"):
                    continue
                destination = path.parent / link.split("#", 1)[0]
                self.assertTrue(destination.exists(), "%s -> %s" % (path, link))

    def test_payload_complete_and_licensed(self):
        for relative in ("LICENSE", "scripts/compat_audit.py", "scripts/setup.py", "assets/browser-probe.html",
                         "assets/support-matrix.example.json", "references/browser-matrix.md",
                         "references/css.md", "references/javascript.md", "references/platform.md",
                         "references/verification.md", "references/sources.md"):
            self.assertTrue((SKILL / relative).is_file(), relative)
        self.assertEqual((ROOT / "LICENSE").read_bytes(), (SKILL / "LICENSE").read_bytes())

    def test_python_syntax_parses_as_39(self):
        for path in [ROOT / "scripts" / "install.py", SKILL / "scripts" / "compat_audit.py", SKILL / "scripts" / "setup.py"]:
            ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))


if __name__ == "__main__":
    unittest.main()
