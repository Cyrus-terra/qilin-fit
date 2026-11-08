#!/usr/bin/env python3
"""Install the bundled Skill into explicitly selected client discovery paths."""
import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

NAME = "qilin-fit"
SOURCE = Path(__file__).resolve().parents[1] / "skills" / NAME


def load_setup():
    spec = importlib.util.spec_from_file_location("qilin_fit_setup", SOURCE / "scripts" / "setup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SETUP = load_setup()
DIRECTORIES = {agent: client["directory"] for agent, client in SETUP.CLIENTS.items()}


def install(target, agents, dry_run=False, scope="project"):
    target = Path(target).expanduser().resolve(strict=True)
    if not target.is_dir():
        raise ValueError("目标必须是现有项目目录")
    if SOURCE.is_symlink():
        raise ValueError("Skill 源根目录不能是符号链接")
    if not (SOURCE / "SKILL.md").is_file():
        raise ValueError("发布包不完整：缺少 SKILL.md")
    # Refuse links even inside the distributed payload.
    for item in SOURCE.rglob("*"):
        if item.is_symlink():
            raise ValueError("Skill 源目录不能包含符号链接：%s" % item)
    selected = SETUP._agents(agents)
    if scope not in ("project", "user"):
        raise ValueError("不支持的安装范围")
    unsupported = [agent for agent in selected if scope == "project" and not SETUP.CLIENTS[agent]["project_install"]]
    if unsupported:
        raise ValueError("不支持自动项目级安装：{}；请使用用户级安装、原生插件，或核实实际 profile/workspace 后手动复制。all 表示全部六客户端。".format(", ".join(unsupported)))
    destinations = []
    for agent in selected:
        destination = target / DIRECTORIES[agent] / "skills" / NAME
        if destination == SOURCE.resolve() or SOURCE.resolve() in destination.parents:
            raise ValueError("拒绝向 Skill 源目录内部安装，避免递归复制")
        for part in (destination.parent.parent, destination.parent, destination):
            if part.is_symlink():
                raise ValueError("拒绝写入符号链接：%s" % part)
            if part.exists() and not part.is_dir():
                raise ValueError("路径不是目录：%s" % part)
        if destination.exists():
            raise FileExistsError("已有 Skill，未覆盖；请先人工比对：%s" % destination)
        destinations.append(destination)
    # All collision checks happen before the first write. No overwrite/force mode.
    for destination in destinations:
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    return destinations


def main(argv=None):
    parser = argparse.ArgumentParser(description="安装 qilin-fit，并在交互终端首次询问当前项目是否启用；可选用户级安装及全局提醒")
    parser.add_argument("--target", help="现有项目根目录；项目级安装必填")
    parser.add_argument("--scope", choices=("project", "user"), default="project", help="默认 project；user 安装到当前用户目录")
    parser.add_argument("--decision", choices=("ask", "enable", "disable", "reset", "status"), default="ask", help="项目首次选择；默认 ask，不在非交互环境擅自同意")
    parser.add_argument("--global-reminder", action="store_true", help="仅用户级安装：额外询问是否合并跨项目首次确认提醒")
    parser.add_argument("--agent", action="append", required=True, choices=list(DIRECTORIES) + ["all"], help="可多次指定；all 表示六客户端，仅用户级安装可用")
    parser.add_argument("--dry-run", action="store_true", help="仅检查并列出目标，不写入")
    args = parser.parse_args(argv)
    if args.scope == "project" and not args.target:
        parser.error("项目级安装必须指定 --target")
    if args.scope == "user" and args.target:
        parser.error("用户级安装使用当前用户主目录，不接受 --target")
    if args.scope == "project" and args.global_reminder:
        parser.error("--global-reminder 仅用于 --scope user")
    if args.scope == "user" and args.decision != "ask":
        parser.error("--decision 用于项目状态；用户级安装的全局提醒会另行征求同意")
    target = Path.home() if args.scope == "user" else args.target
    try:
        if args.global_reminder:
            SETUP.validate_global_agents(args.agent)
        destinations = install(target, args.agent, args.dry_run, args.scope)
    except (OSError, ValueError) as exc:
        print("安装失败：%s" % exc, file=sys.stderr)
        print("未覆盖既有 Skill；若发生写入阶段错误，请检查是否有部分新目录已创建。", file=sys.stderr)
        return 2
    for destination in destinations:
        print(("计划安装 " if args.dry_run else "已安装 ") + str(destination))
    try:
        if args.scope == "project":
            result = SETUP.configure_project(target, args.agent, args.decision, args.dry_run)
        elif args.global_reminder:
            result = SETUP.configure_global(Path.home(), args.agent, "ask", args.dry_run)
        else:
            result = None
        if result is not None:
            print("项目决定：" + result["decision"] if args.scope == "project" else "全局提醒：" + result["decision"])
            for path in result["changed"]:
                print(("计划配置 " if args.dry_run else "已配置 ") + str(path))
            for note in result.get("notes", []):
                print("注意：" + note)
            if result["needsConfirmation"]:
                print("待用户确认，未自动启用。请在 Agent 中加载 qilin-fit 并确认，或手动运行 Skill 内 scripts/setup.py。")
    except (OSError, ValueError) as exc:
        print("Skill 复制已完成或已预演，但首次配置失败：%s" % exc, file=sys.stderr)
        print("不要重新覆盖安装；修复后直接运行 Skill 内 scripts/setup.py。", file=sys.stderr)
        return 2
    print("重新启动 Agent 或按其文档刷新技能；自动匹配不是强制调用。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
