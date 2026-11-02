#!/usr/bin/env python3
"""Install the bundled skill into explicitly selected project discovery paths."""
import argparse
import shutil
import sys
from pathlib import Path

NAME = "qilin-fit"
DIRECTORIES = {"codebuddy": ".codebuddy", "claude": ".claude", "codex": ".agents"}
SOURCE = Path(__file__).resolve().parents[1] / "skills" / NAME


def install(target, agents, dry_run=False):
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
    selected = list(DIRECTORIES) if "all" in agents else list(dict.fromkeys(agents))
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
    parser = argparse.ArgumentParser(description="将同一标准 Skill 复制到各 Agent 的项目级发现目录；不修改项目指令或配置")
    parser.add_argument("--target", required=True, help="现有项目目录；可使用绝对路径")
    parser.add_argument("--agent", action="append", required=True, choices=list(DIRECTORIES) + ["all"], help="可多次指定；all 安装三个 Agent")
    parser.add_argument("--dry-run", action="store_true", help="仅检查并列出目标，不写入")
    args = parser.parse_args(argv)
    try:
        destinations = install(args.target, args.agent, args.dry_run)
    except (OSError, ValueError) as exc:
        print("安装失败：%s" % exc, file=sys.stderr)
        print("未覆盖既有 Skill；若发生写入阶段错误，请检查是否有部分新目录已创建。", file=sys.stderr)
        return 2
    for destination in destinations:
        print(("计划安装 " if args.dry_run else "已安装 ") + str(destination))
    print("重新启动 Agent 或按其文档刷新技能；自动匹配不是强制调用。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
