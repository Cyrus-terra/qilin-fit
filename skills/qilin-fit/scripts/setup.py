#!/usr/bin/env python3
"""以显式项目决定管理 Qilin Fit 指令；仅使用 Python 3.9 标准库。"""

import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

AGENTS = ("codebuddy", "claude", "codex")
PROJECT_FILES = {"codebuddy": "CODEBUDDY.md", "claude": "CLAUDE.md", "codex": "AGENTS.md"}
DECISIONS = ("ask", "enable", "disable", "reset", "status")
PROJECT_BODY = """## Qilin Fit 项目约定

开展前端业务开发前，先读取本项目根目录的 `.qilin-fit.json`，不得推断其他目录的状态。
- 只有 schemaVersion 为 1 且 decision 为 enabled，才表示已明确同意；前端任务必须加载本项目或已安装的 qilin-fit Skill，并遵循其规范。
- decision 为 disabled：不自动调用或加载 Qilin Fit，不再次询问、不自动改决定。
- 状态文件不存在或 decision 为 unknown：先通过 Agent 的用户对话询问是否启用，未确认前不要加载，不得默认选择 102 或其他风格。明确同意/拒绝后才调用 setup.py --target <项目根> --agent <当前客户端> --decision enable/disable 记录决定。
- 暂缓或取消只表示本次不启用，本会话不反复追问；无交互能力时不得默认同意。损坏或未知 schema 的状态应报告错误，不得覆盖。
- 找不到 Skill 时报告缺失，请用户安装；不要把此指令文件或全局配置目录当成 Skill 目录。
"""
REMINDER_BODY = """## Qilin Fit 可选项目提醒

这是用户级指令提醒，不是 hook，不保证客户端强制触发，也不代表对任何项目的授权。
在首次业务开发前，先确定本次业务的实际项目根目录，再读取该目录的 `.qilin-fit.json`；不要把用户主目录、此全局指令目录或 Skill 安装目录当成业务项目。
- 仅 schemaVersion 为 1 且 decision 为 enabled 表示明确同意：前端任务必须加载可用的 qilin-fit Skill。
- decision 为 disabled：不自动加载、不再询问、不改变决定。
- 文件缺失或 decision 为 unknown：通过 Agent 的用户对话询问是否启用，而不是直接运行需要 shell stdin 的询问脚本。只有明确同意/拒绝后，才调用可用 Skill 中的 scripts/setup.py --target <项目根> --agent <当前客户端> --decision enable/disable 记录决定。
- 用户暂缓、取消或未答复，本次不启用，本会话不反复追问；无交互时不默认同意，不默认选择 102 或其他风格。
- 状态损坏或未知 schema 时报告错误，不得覆盖；新项目找不到 Skill 时先报告缺失并请用户安装。全局指令目录与 Skill 目录不同，不可用此提醒代替 Skill。
"""


def _agents(agents):
    if isinstance(agents, str):
        agents = [agents]
    values = list(agents)
    if any(value not in AGENTS + ("all",) for value in values):
        raise ValueError("不支持的客户端")
    return list(AGENTS) if not values or "all" in values else list(dict.fromkeys(values))


def _check_parents(path, root):
    relative = path.relative_to(root)
    directory = root
    for part in (None,) + relative.parts[:-1]:
        if part is not None:
            directory = directory / part
        try:
            info = directory.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("拒绝符号链接或非目录的父路径：{}".format(directory))


def _read(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return b""
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("拒绝处理符号链接、目录或硬链接文件：{}".format(path))
    return path.read_bytes()


def _span(data, kind, path):
    begin = "<!-- qilin-fit:{}:begin -->".format(kind).encode()
    end = "<!-- qilin-fit:{}:end -->".format(kind).encode()
    count_begin, count_end = data.count(begin), data.count(end)
    if count_begin == count_end == 0:
        # 本命名空间中拼错的标记也不能当普通文本覆盖。
        if ("<!-- qilin-fit:{}:".format(kind).encode()) in data:
            raise ValueError("无效的 Qilin Fit 标记：{}".format(path))
        return None
    if count_begin != 1 or count_end != 1 or data.count("<!-- qilin-fit:{}:".format(kind).encode()) != 2:
        raise ValueError("不完整或重复的 Qilin Fit 标记：{}".format(path))
    start, finish = data.index(begin), data.index(end)
    if start >= finish:
        raise ValueError("倒序的 Qilin Fit 标记：{}".format(path))
    for offset, marker in ((start, begin), (finish, end)):
        after = offset + len(marker)
        if (offset and data[offset - 1:offset] != b"\n") or (after < len(data) and data[after:after + 1] not in (b"\r", b"\n")):
            raise ValueError("Qilin Fit 标记必须独占一行：{}".format(path))
        if data[after:after + 1] == b"\r" and data[after:after + 2] != b"\r\n":
            raise ValueError("无效的 Qilin Fit 标记换行：{}".format(path))
    stop = finish + len(end)
    if data[stop:stop + 2] == b"\r\n":
        stop += 2
    elif data[stop:stop + 1] == b"\n":
        stop += 1
    return start, stop


def _merge(data, kind, body, enabled, path):
    span = _span(data, kind, path)
    if not enabled:
        return data if span is None else data[:span[0]] + data[span[1]:]
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    text = "<!-- qilin-fit:{0}:begin -->\n{1}<!-- qilin-fit:{0}:end -->\n".format(kind, body)
    block = text.encode("utf-8").replace(b"\n", newline)
    if span is not None:
        return data[:span[0]] + block + data[span[1]:]
    separator = newline if data and not data.endswith(b"\n") else b""
    return data + separator + block


def _write(path, content):
    _read(path)
    old_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".qilin-fit-", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if old_mode is not None:
            os.chmod(temporary, old_mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("重复的 JSON 键：{}".format(key))
        value[key] = item
    return value


def _state(path, data):
    if not path.exists():
        return "unknown"
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("项目状态损坏：{}".format(path)) from exc
    if (not isinstance(value, dict) or set(value) != {"schemaVersion", "decision"}
            or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1
            or value["decision"] not in ("enabled", "disabled", "unknown")):
        raise ValueError("不支持或损坏的项目状态：{}".format(path))
    return value["decision"]


def _answer(prompt):
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return ""


def _notes(files, kind):
    return ["可能存在旧版手工 Qilin Fit 规则，请人工检查（未删除）：{}".format(path)
            for path, data in files.items()
            if b"qilin-fit" in data.lower() and _span(data, kind, path) is None]


def configure_project(target, agents, decision="ask", dry_run=False):
    """配置一个显式项目目录；全量预检完成后规则先写，状态最后写。"""
    selected = _agents(agents)
    if decision not in DECISIONS:
        raise ValueError("不支持的决定")
    target = Path(target).expanduser().resolve()
    if not target.is_dir():
        raise ValueError("项目目录必须已经存在：{}".format(target))
    skill_root = Path(__file__).resolve().parents[1]
    if target == skill_root or skill_root in target.parents:
        raise ValueError("不可将 Skill 根目录或其子目录设为业务项目")
    state_path = target / ".qilin-fit.json"
    current = _state(state_path, _read(state_path))
    files = {target / PROJECT_FILES[agent]: _read(target / PROJECT_FILES[agent]) for agent in AGENTS}
    for path, data in files.items():
        _span(data, "project", path)
    result = {"decision": current, "changed": [], "needsConfirmation": current == "unknown",
              "notes": _notes(files, "project")}
    for agent, directory in (("codebuddy", ".codebuddy"), ("claude", ".claude")):
        alternate = target / directory / PROJECT_FILES[agent]
        if agent in selected:
            _check_parents(alternate, target)
            if _read(alternate):
                result["notes"].append("检测到并行配置 {}；客户端加载优先级可能不同，请人工确认，不能保证根目录规则生效。".format(alternate))
    if decision == "status":
        return result
    if decision == "ask" and current == "unknown":
        if dry_run or not sys.stdin.isatty():
            return result
        answer = _answer("是否为项目 {} 启用 Qilin Fit？[y=启用 / n=禁用 / l或回车=稍后] ".format(target))
        if answer not in ("y", "n"):
            return result
        decision = "enable" if answer == "y" else "disable"
    desired = {"enable": "enabled", "disable": "disabled", "reset": "unknown"}.get(decision, current)
    changes = []
    for path, data in files.items():
        if desired == "enabled" and path.name not in [PROJECT_FILES[a] for a in selected]:
            continue
        original = data
        if desired == "enabled" and path.name == "CODEBUDDY.md" and not path.exists() and files[target / "AGENTS.md"]:
            newline = b"\r\n" if b"\r\n" in files[target / "AGENTS.md"] else b"\n"
            # 保留在管理块之外，禁用后空的 CODEBUDDY.md 也不能遮蔽旧 AGENTS.md。
            data = b"@AGENTS.md" + newline + newline
        updated = _merge(data, "project", PROJECT_BODY, desired == "enabled", path)
        if updated != original:
            changes.append((path, updated))
    if desired != current or (decision in ("enable", "disable", "reset") and not state_path.exists()):
        state_data = (json.dumps({"schemaVersion": 1, "decision": desired}, ensure_ascii=False, indent=2) + "\n").encode()
        changes.append((state_path, state_data))
    result.update(decision=desired, changed=[str(path) for path, _ in changes], needsConfirmation=desired == "unknown")
    if not dry_run:
        for path, data in changes:
            _write(path, data)
    return result


def configure_global(home, agents, decision="ask", dry_run=False):
    """可选用户级提醒，不安装 hook，也不替任何项目做授权决定。"""
    selected = _agents(agents)
    if decision not in DECISIONS:
        raise ValueError("不支持的决定")
    home = Path(home).expanduser().resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", str(home / ".codex"))).expanduser().absolute()
    paths = {"codebuddy": home / ".codebuddy" / "CODEBUDDY.md",
             "claude": home / ".claude" / "CLAUDE.md", "codex": codex_home / "AGENTS.md"}
    roots = {agent: home for agent in AGENTS}
    if "CODEX_HOME" in os.environ:
        roots["codex"] = home if home in codex_home.parents or codex_home == home else Path(codex_home.anchor)
    for agent in selected:
        _check_parents(paths[agent], roots[agent])
    files = {paths[agent]: _read(paths[agent]) for agent in selected}
    override = codex_home / "AGENTS.override.md"
    shadowed = "codex" in selected and bool(_read(override).strip())
    spans = [_span(data, "reminder", path) for path, data in files.items()]
    current = "enabled" if all(span is not None for span in spans) else ("disabled" if all(span is None for span in spans) else "unknown")
    result = {"decision": current, "changed": [], "needsConfirmation": False, "notes": _notes(files, "reminder")}
    if shadowed:
        result["notes"].append("{} 非空，会遮蔽 AGENTS.md；请先人工合并或移除 override，当前提醒不能保证生效。".format(override))
        result["decision"] = "unknown"
        if decision in ("enable", "ask"):
            raise ValueError(result["notes"][-1])
    if decision == "status":
        return result
    if decision == "ask":
        result["needsConfirmation"] = True
        if dry_run or not sys.stdin.isatty():
            return result
        answer = _answer("这将为以后项目添加用户级提醒（不是自动授权），影响以下文件：\n{}\n是否同意？[y=同意 / n=拒绝 / 回车=稍后] ".format("\n".join(str(path) for path in files)))
        if answer != "y":
            result["needsConfirmation"] = answer != "n"
            return result
        decision = "enable"
    enabled = decision == "enable"
    changes = []
    for path, data in files.items():
        updated = _merge(data, "reminder", REMINDER_BODY, enabled, path)
        if updated != data:
            changes.append((path, updated))
    result.update(decision="enabled" if enabled else "disabled",
                  changed=[str(path) for path, _ in changes], needsConfirmation=False)
    if not dry_run:
        for path, data in changes:
            _write(path, data)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Qilin Fit 项目确认与可选全局提醒（不安装 hooks）")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--target", type=Path, help="已存在的业务项目目录")
    mode.add_argument("--global-reminder", action="store_true", help="配置可选用户级提醒，影响以后的项目")
    parser.add_argument("--agent", action="append", choices=("all",) + AGENTS, help="可重复指定，默认 all")
    parser.add_argument("--decision", choices=DECISIONS, default="ask")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不询问、不写入")
    args = parser.parse_args(argv)
    try:
        if args.global_reminder:
            result = configure_global(Path.home(), args.agent or ["all"], args.decision, args.dry_run)
        else:
            result = configure_project(args.target, args.agent or ["all"], args.decision, args.dry_run)
    except (OSError, ValueError) as exc:
        print("配置失败：{}".format(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["needsConfirmation"]:
        print("尚需用户明确确认；未默认启用。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
