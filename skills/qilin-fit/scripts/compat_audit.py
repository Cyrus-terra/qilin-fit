#!/usr/bin/env python3
"""Read-only, offline lexical compatibility candidates; not a browser certification."""
import argparse
import json
import os
from pathlib import Path
import re
import sys


EXTENSIONS = {".css", ".scss", ".less", ".js", ".jsx", ".ts", ".tsx",
              ".mjs", ".cjs", ".vue", ".svelte", ".html", ".json"}
IGNORE = {".git", "node_modules", "vendor", ".venv", ".claude", ".codebuddy",
          ".agents", "coverage"}
BUILD = {"dist", "build", ".next", "out"}
LOCKS = {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
         "bun.lock", "bun.lockb"}
BCD = "https://github.com/mdn/browser-compat-data/blob/main/"
CSS_EXT = {".css", ".scss", ".less", ".js", ".jsx", ".ts", ".tsx",
           ".mjs", ".cjs", ".vue", ".svelte", ".html"}
JS_EXT = CSS_EXT - {".css", ".scss", ".less"}


def rule(name, pattern, chrome, message, evidence, kind="css", review=False):
    return {"id": name, "pattern": re.compile(pattern), "requiredChrome": chrome,
            "message": message, "evidence": BCD + evidence, "kind": kind, "review": review}


RULES = [
    rule("css-lab", r"(?<![\w-])lab\s*\(", 111, "lab() 颜色需检查旧内核回退。", "css/types/color.json"),
    rule("css-oklab", r"(?<![\w-])oklab\s*\(", 111, "oklab() 颜色需检查旧内核回退。", "css/types/color.json"),
    rule("css-lch", r"(?<![\w-])lch\s*\(", 111, "lch() 颜色需检查旧内核回退。", "css/types/color.json"),
    rule("css-oklch", r"(?<![\w-])oklch\s*\(", 111, "oklch() 颜色需检查旧内核回退。", "css/types/color.json"),
    rule("css-color-function", r"(?<![\w-])color\s*\(", 111, "color() 广色域颜色需检查回退及显示差异。", "css/types/color.json"),
    rule("css-color-mix", r"(?<![\w-])color-mix\s*\(", 111, "color-mix() 需检查旧内核回退。", "css/types/color.json"),
    rule("css-light-dark", r"(?<![\w-])light-dark\s*\(", 123, "light-dark() 需检查主题回退。", "css/types/color.json"),
    rule("css-dynamic-viewport", r"(?<![\w-])(?:\d*\.)?\d+(?:[dsl]v(?:h|w|i|b|min|max))\b", 108,
         "动态/小/大视口单位需提供旧视口单位回退。", "css/types/length.json"),
    rule("css-has", r":has\s*\(|(?<![\w-])(?:(?:group|peer|in)-)?has-(?:\[|[a-z])", 105, "检查 :has() 或 Tailwind has-* 编译后选择器及渐进增强。", "css/selectors/has.json"),
    rule("css-container-query", r"@container\b", 105, "容器查询候选；核验查询类型（此阈值仅尺寸查询）与回退。", "css/at-rules/container.json"),
    rule("css-container-units", r"(?<![\w-])(?:\d*\.)?\d+(?:cqw|cqh|cqi|cqb|cqmin|cqmax)\b", 105,
         "容器查询单位需检查布局回退。", "css/types/length.json"),
    rule("css-nesting", r"(?:[{};]\s*|^)\&(?=[\s.:#\[>+~])", 112,
         "显式&嵌套选择器候选；112仅初始语法，放宽语法需120，SCSS/构建编译可消除此风险。", "css/selectors/nesting.json"),
    rule("css-anchor-position", r"\b(?:anchor-name|position-anchor)\s*:|(?<![\w-])anchor(?:-size)?\s*\(", 125,
         "锚点定位候选；具体子特性支持有差异，需核验产物及回退。", "css/properties/anchor-name.json"),
    rule("css-independent-transform", r"(?<![\w-])(?:translate|rotate|scale)\s*:", 104,
         "独立变换属性需旧内核 transform 回退；与 Tailwind 工具类版本区别核验。", "css/properties/translate.json"),
    rule("css-layer", r"@layer\b", 99, "级联层需检查产物与旧内核降级。", "css/at-rules/layer.json"),
    rule("css-property", r"@property\b", 85, "自定义属性注册需检查未注册时的回退。", "css/at-rules/property.json"),
    rule("tailwind-transform-review", r"\b(?:translate-[xy]-|rotate-|scale-)(?:\d|\[)", None,
         "Tailwind 变换工具类需核验版本及生成CSS；v3可生成传统transform，不能一概禁用。",
         "css/properties/translate.json", review=True),
    rule("js-optional-chain", r"\?\.(?!\d)", 80, "可选链语法需检查最终构建目标。", "javascript/operators/optional_chaining.json", "js"),
    rule("js-nullish", r"\?\?(?!=)", 80, "空值合并语法需检查最终构建目标。", "javascript/operators/nullish_coalescing.json", "js"),
    rule("js-logical-assignment", r"(?:\?\?|&&|\|\|)=", 85, "逻辑赋值语法需检查最终构建目标。", "javascript/operators/logical_or_assignment.json", "js"),
    rule("js-private-fields", r"(?:[;{]\s*|^)#[A-Za-z_$][\w$]*\s*(?:=|;)", 74,
         "私有实例字段候选；静态字段、方法等子特性需另行核验。", "javascript/classes.json", "js"),
    rule("js-static-block", r"\bstatic\s*\{", 94, "类静态初始化块需检查构建转译。", "javascript/classes.json", "js"),
    rule("api-structured-clone", r"(?<![\w$])structuredClone\s*\(", 98, "structuredClone() 需检查功能检测及回退。", "api/_globals/structuredClone.json", "js"),
    rule("api-object-hasown", r"\bObject\s*\.\s*hasOwn\s*\(", 93, "Object.hasOwn() 需检查运行时回退。", "javascript/builtins/Object.json", "js"),
    rule("api-array-tosorted", r"\.\s*toSorted\s*\(", 110, "toSorted() 候选；确认接收者及运行时回退。", "javascript/builtins/Array.json", "js"),
    rule("api-array-fromasync", r"\bArray\s*\.\s*fromAsync\s*\(", 121, "Array.fromAsync() 需检查运行时回退。", "javascript/builtins/Array.json", "js"),
    rule("api-promise-withresolvers", r"\bPromise\s*\.\s*withResolvers\s*\(", 119, "Promise.withResolvers() 需检查运行时回退。", "javascript/builtins/Promise.json", "js"),
    rule("api-array-findlast", r"\.\s*findLast(?:Index)?\s*\(", 97, "findLast()/findLastIndex() 候选；确认接收者及回退。", "javascript/builtins/Array.json", "js"),
    rule("api-string-replaceall", r"\.\s*replaceAll\s*\(", 85, "replaceAll() 候选；确认接收者及运行时回退。", "javascript/builtins/String.json", "js"),
    rule("api-intl-segmenter", r"\bIntl\s*\.\s*Segmenter\s*\(", 87, "Intl.Segmenter() 需检查运行时回退及分词差异。", "javascript/builtins/Intl/Segmenter.json", "js"),
    rule("api-resize-observer", r"\bnew\s+ResizeObserver\s*\(", 64, "ResizeObserver 需检查功能检测及布局回退。", "api/ResizeObserver.json", "js"),
    rule("api-intersection-observer", r"\bnew\s+IntersectionObserver\s*\(", 51, "IntersectionObserver 需检查功能检测及回退。", "api/IntersectionObserver.json", "js"),
    rule("api-abort-timeout", r"\bAbortSignal\s*\.\s*timeout\s*\(", 103, "AbortSignal.timeout() 需检查功能检测及超时回退。", "api/AbortSignal.json", "js"),
    rule("api-abort-any", r"\bAbortSignal\s*\.\s*any\s*\(", 116, "AbortSignal.any() 需检查功能检测及回退。", "api/AbortSignal.json", "js"),
    rule("api-random-uuid", r"\bcrypto\s*\.\s*randomUUID\s*\(", 92, "crypto.randomUUID() 还要求安全上下文；需核验实际协议与功能检测。", "api/Crypto.json", "js"),
    rule("html-dialog", r"<dialog(?=[\s>])", 37, "dialog 元素候选；焦点、模态与可访问性需实机验证。", "html/elements/dialog.json", "html"),
    rule("html-popover", r"<[^>]+\s(?:popover(?:\s*=|[\s>])|popovertarget\s*=)", 114,
         "Popover API 标记候选；需检查交互回退。", "html/global_attributes.json", "html"),
]
TAILWIND = {"id": "tailwind-v4", "requiredChrome": 111,
            "message": "Tailwind CSS v4 官方基线为 Chrome 111；需核验最终CSS与厂商内核。",
            "evidence": "https://tailwindcss.com/docs/compatibility"}
LIMITATIONS = ("仅离线词法候选检查，不是兼容性认证。存在注释、字符串、同名成员的误报及动态代码、"
               "间接调用、语法变体及大小写CSS的漏报；不解析AST、guard或构建配置。已做功能检测/渐进增强仍需人工复核。"
               "符号链接及含符号链接祖先的路径一律跳过（含系统路径别名），不保证并发改动下的路径隔离。"
               "Chrome阈值只代表所列子特性的上游参考，不证明厂商浏览器、全部子特性或实际页面行为。")


def finding(path, text, offset, item, baseline):
    line = text.count("\n", 0, offset) + 1
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    excerpt = text[start:end if end >= 0 else len(text)]
    column = offset - start + 1
    # Keep the matched location visible even in minified single-line bundles.
    left = max(0, column - 81)
    return {"filename": str(path), "line": line, "column": column, "rule": item["id"],
            "severity": "warning" if baseline is None or item.get("review") else "error",
            "requiredChrome": item["requiredChrome"], "message": item["message"] +
            (" 未知内核基线，需人工评审。" if baseline is None else " 词法候选，不代表实际运行失败。"),
            "excerpt": excerpt[left:left + 240], "evidence": item["evidence"]}


def scan_text(path, text, baseline):
    results = []
    if path.name == "package.json":
        data = json.loads(text)
        if isinstance(data, dict):
            for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                deps = data.get(section, {})
                value = deps.get("tailwindcss") if isinstance(deps, dict) else None
                if isinstance(value, str) and re.match(r"^[~^=\s]*4(?:\.|$)", value):
                    if baseline is None or baseline < 111:
                        offset = text.find('"tailwindcss"')
                        results.append(finding(path, text, max(0, offset), TAILWIND, baseline))
        return results
    if path.suffix == ".json":
        return results
    for item in RULES:
        if baseline is not None and not item["review"] and baseline >= item["requiredChrome"]:
            continue
        if item["kind"] == "js" and path.suffix not in JS_EXT:
            continue
        if item["kind"] == "html" and path.suffix not in {".html", ".vue", ".svelte", ".jsx", ".tsx"}:
            continue
        for match in item["pattern"].finditer(text):
            results.append(finding(path, text, match.start(), item, baseline))
    return results


def audit(paths, baseline, include_build=False, max_file_bytes=5 * 1024 * 1024):
    results, skipped, errors, scanned, seen = [], [], [], [], set()

    def skip(path, reason):
        skipped.append({"filename": str(path), "reason": reason})

    def visit(path):
        try:
            if any(part.is_symlink() for part in reversed((path,) + tuple(path.parents))):
                skip(path, "symlink-not-followed")
                return
            path = Path(os.path.abspath(path))
            if not path.exists():
                raise FileNotFoundError("path does not exist")
            blocked = set(path.parts) & (IGNORE | (set() if include_build else BUILD))
            if blocked:
                skip(path, "excluded-directory:" + sorted(blocked)[0])
                return
            key = str(path.absolute())
            if key in seen:
                return
            seen.add(key)
            if path.is_dir():
                with os.scandir(path) as entries:
                    children = sorted((Path(entry.path) for entry in entries), key=str)
                for child in children:
                    visit(child)
                return
            if not path.is_file():
                skip(path, "not-regular-file")
                return
            if path.name in LOCKS or path.suffix not in EXTENSIONS:
                skip(path, "lockfile-or-unsupported-extension")
                return
            if path.stat().st_size > max_file_bytes:
                skip(path, "over-max-file-bytes")
                return
            with path.open("rb") as handle:
                raw = handle.read(max_file_bytes + 1)
            if len(raw) > max_file_bytes:
                skip(path, "over-max-file-bytes")
                return
            text = raw.decode("utf-8-sig")
            matches = scan_text(path, text, baseline)
            results.extend(matches)
            scanned.append(str(path))
        except (OSError, ValueError) as exc:
            errors.append({"filename": str(path), "message": str(exc)})

    for value in paths:
        if not value:
            errors.append({"filename": value, "message": "empty path"})
        else:
            path = Path(value)
            visit(path if path.is_absolute() else Path.cwd() / path)
    results.sort(key=lambda x: (x["filename"], x["line"], x["column"], x["rule"]))
    metadata = [{key: value for key, value in item.items() if key not in {"pattern", "kind", "review"}}
                for item in RULES] + [TAILWIND]
    return {"baseline": {"minChromium": baseline, "status": "unknown" if baseline is None else "provided"},
            "findings": results, "skipped": skipped, "errors": errors, "rules": metadata,
            "summary": {"filesScanned": len(scanned), "findings": len(results),
                        "warnings": sum(x["severity"] == "warning" for x in results),
                        "errors": sum(x["severity"] == "error" for x in results),
                        "filesSkipped": len(skipped), "ioErrors": len(errors), "rules": len(metadata)},
            "limitations": LIMITATIONS}


def positive_int(value):
    try:
        result = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer")
    if result <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=["."])
    parser.add_argument("--min-chromium", type=positive_int)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--include-build", action="store_true")
    parser.add_argument("--max-file-bytes", type=positive_int, default=5 * 1024 * 1024)
    parser.add_argument("--fail-on", choices=("none", "warning", "error"), default="none")
    args = parser.parse_args(argv)
    report = audit(args.paths, args.min_chromium, args.include_build, args.max_file_bytes)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        baseline = args.min_chromium if args.min_chromium is not None else "unknown"
        print("Chromium baseline: {}; rules: {}".format(baseline, report["summary"]["rules"]))
        for item in report["findings"]:
            print("{filename}:{line}:{column}: {severity} [{rule}] {message}".format(**item))
            print("  " + item["excerpt"])
        for item in report["skipped"]:
            print("SKIPPED {filename}: {reason}".format(**item))
        for item in report["errors"]:
            print("IO ERROR {filename}: {message}".format(**item))
        print("Summary: " + json.dumps(report["summary"], ensure_ascii=False))
        print(report["limitations"])
    if report["errors"]:
        return 2
    if args.fail_on == "warning" and report["findings"]:
        return 1
    if args.fail_on == "error" and report["summary"]["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
