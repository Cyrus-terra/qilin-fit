"""Register the shared Skill without hooks or automatic project configuration."""

import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = next((root for root in (HERE.parent, HERE) if (root / "skills/qilin-fit/SKILL.md").is_file()), HERE.parent)
ENTRY = ROOT / "skills" / "qilin-fit" / "SKILL.md"


def register(ctx):
    if not ENTRY.is_file():
        raise RuntimeError("qilin-fit entry not found: {}".format(ENTRY))
    text = ENTRY.read_text(encoding="utf-8")
    match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
    description = match.group(1).strip() if match else "Opt-in frontend browser compatibility workflow"
    ctx.register_skill("qilin-fit", ENTRY, description=description)
