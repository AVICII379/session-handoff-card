"""离线目录预览的当前未完成实现。"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re


FILENAME_PATTERN = re.compile(
    r"^(?:(?P<year>\d{4})[_ -]+)?(?P<author>[^_]+)_(?P<title>.+)\.pdf$",
    re.IGNORECASE,
)


def parse_filename(name: str) -> dict[str, str]:
    match = FILENAME_PATTERN.match(name)
    if not match:
        return {"year": "", "first_author": "", "title": Path(name).stem, "status": "REVIEW"}
    year = match.group("year") or ""
    return {
        "year": year,
        "first_author": match.group("author").strip(),
        "title": match.group("title").strip(),
        "status": "READY" if year else "REVIEW",
    }


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def mark_duplicates(rows: list[dict[str, str]]) -> None:
    seen: set[str] = set()
    for row in rows:
        digest = row["sha256"]
        if digest in seen:
            row["status"] = "DUPLICATE"
        else:
            seen.add(digest)


def detect_name_collisions(rows: list[dict[str, str]]) -> None:
    """尚未实现：只应检查非 DUPLICATE 行。"""
    raise NotImplementedError
