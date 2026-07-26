#!/usr/bin/env python3
"""Preview and redact common secrets, personal data, and machine-specific paths."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys


PATTERNS = [
    ("openai_api_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"), "<REDACTED_API_KEY>"),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"), "<REDACTED_GITHUB_TOKEN>"),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "<REDACTED_AWS_KEY>"),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.I), "Bearer <REDACTED_TOKEN>"),
    ("email_address", re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])"), "<REDACTED_EMAIL>"),
    ("cn_mobile_number", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "<REDACTED_PHONE>"),
    ("windows_home_path", re.compile(r"[A-Za-z]:\\Users\\[^\\\r\n]+", re.I), "<HOME>"),
    ("posix_home_path", re.compile(r"(?<![\w.-])/(?:home|Users)/[^/\s]+(?:/[^\s]*)?"), "<HOME>"),
]
PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.S,
)


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def literal_alias(text: str, value: str, alias: str, counts: Counter[str]) -> str:
    if not value:
        return text
    variants = {value, value.replace("\\", "/"), value.replace("/", "\\")}
    for variant in sorted(variants, key=len, reverse=True):
        found = text.count(variant)
        if found:
            text = text.replace(variant, alias)
            counts["project_root_alias"] += found
    return text


def redact(text: str, project_root: str = "") -> tuple[str, dict[str, int]]:
    counts: Counter[str] = Counter()
    text = literal_alias(text, project_root, "<PROJECT_ROOT>", counts)

    def replace_source_session(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        if raw in {"", "''", '\"\"'}:
            return match.group(0)
        counts["source_session"] += 1
        return "source_session: '<REDACTED_SESSION>'"

    text = re.sub(r"(?m)^source_session:\s*(.*)$", replace_source_session, text)

    def replace_url_credential(match: re.Match[str]) -> str:
        counts["url_credential"] += 1
        return match.group(1) + "<REDACTED>"

    text = re.sub(
        r"(?i)([?&](?:token|key|signature|sig|auth)=)[^&#\s]+",
        replace_url_credential,
        text,
    )

    def replace_private(match: re.Match[str]) -> str:
        counts["private_key_block"] += 1
        return "<REDACTED_PRIVATE_KEY>"

    text = PRIVATE_KEY.sub(replace_private, text)
    for name, pattern, replacement in PATTERNS:
        text, count = pattern.subn(replacement, text)
        counts[name] += count
    return text, {key: value for key, value in sorted(counts.items()) if value}


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="要预览或脱敏的 UTF-8 文件。")
    parser.add_argument("--output", type=Path, help="写入脱敏副本；省略时只预览统计。")
    parser.add_argument("--project-root", help="将这个根路径替换为 <PROJECT_ROOT>。")
    parser.add_argument("--report", type=Path, help="可选 JSON 报告；不包含原始敏感值。")
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    if not source.is_file():
        parser.error(f"输入文件不存在：{source}")
    try:
        original = source.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        parser.error("输入文件不是有效 UTF-8")
    redacted, counts = redact(original, args.project_root or "")

    output: Path | None = None
    if args.output:
        output = args.output.expanduser().resolve()
        if output.exists():
            parser.error(f"拒绝覆盖已有文件：{output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(redacted, encoding="utf-8", newline="\n")

    result = {
        "ok": True,
        "mode": "write" if output else "preview",
        "changed": redacted != original,
        "replacement_counts": counts,
        "output": output.name if output else None,
        "warning": "规则匹配只能降低泄漏风险，公开前仍需人工复核。",
    }
    if args.report:
        report = args.report.expanduser().resolve()
        if report.exists():
            parser.error(f"拒绝覆盖已有报告：{report}")
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
