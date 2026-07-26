#!/usr/bin/env python3
"""扫描公开源码和发布 ZIP 中常见的秘密、个人信息与开发机路径。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".ab-eval", ".demo-output", "dist", "__pycache__"}
MAX_TEXT_BYTES = 5 * 1024 * 1024

PATTERNS = {
    "windows_user_path": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.I),
    "local_work_path": re.compile(r"[A-Za-z]:\\WORK\\", re.I),
    "email_address": re.compile(
        r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])"
    ),
    "openai_api_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "github_token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private_key_block": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.I),
}


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def decode_text(data: bytes) -> str | None:
    if len(data) > MAX_TEXT_BYTES or b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def dynamic_denied_terms() -> list[str]:
    terms: list[str] = []
    home_name = Path.home().name.strip()
    if len(home_name) >= 3:
        terms.append(home_name)
    return terms


def scan_text(label: str, text: str, denied_terms: list[str]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append(
                {"source": label, "kind": kind, "line": text.count("\n", 0, match.start()) + 1}
            )
    folded = text.casefold()
    for term in denied_terms:
        start = folded.find(term.casefold())
        if start >= 0:
            findings.append(
                {
                    "source": label,
                    "kind": "local_account_name",
                    "line": text.count("\n", 0, start) + 1,
                }
            )
    return findings


def repository_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts)
    )


def scan_repository(denied_terms: list[str]) -> tuple[int, list[dict[str, object]]]:
    scanned = 0
    findings: list[dict[str, object]] = []
    for path in repository_files():
        text = decode_text(path.read_bytes())
        if text is None:
            continue
        scanned += 1
        findings.extend(scan_text(path.relative_to(ROOT).as_posix(), text, denied_terms))
    return scanned, findings


def scan_archive(path: Path, denied_terms: list[str]) -> tuple[int, list[dict[str, object]]]:
    scanned = 0
    findings: list[dict[str, object]] = []
    with zipfile.ZipFile(path) as package:
        for info in package.infolist():
            if info.is_dir():
                continue
            text = decode_text(package.read(info))
            if text is None:
                continue
            scanned += 1
            label = f"{path.name}!/{info.filename}"
            findings.extend(scan_text(label, text, denied_terms))
    return scanned, findings


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", action="append", type=Path, default=[])
    parser.add_argument(
        "--archive-dir",
        type=Path,
        help="扫描该目录中的全部 ZIP；通常传入 dist。",
    )
    args = parser.parse_args()

    archives = [path.expanduser().resolve() for path in args.archive]
    if args.archive_dir:
        archive_dir = args.archive_dir.expanduser().resolve()
        archives.extend(sorted(archive_dir.glob("*.zip")))
        if not archives:
            parser.error(f"目录中没有 ZIP：{archive_dir}")
    missing = [str(path) for path in archives if not path.is_file()]
    if missing:
        parser.error("ZIP 不存在：" + ", ".join(missing))

    denied_terms = dynamic_denied_terms()
    repo_count, findings = scan_repository(denied_terms)
    archive_counts: dict[str, int] = {}
    for archive in archives:
        count, archive_findings = scan_archive(archive, denied_terms)
        archive_counts[archive.name] = count
        findings.extend(archive_findings)

    result = {
        "ok": not findings,
        "repository_text_files": repo_count,
        "archives": archive_counts,
        "findings": findings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
