#!/usr/bin/env python3
"""核验 chunk_history.py 生成的索引、分块哈希和字符覆盖。"""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def chunk_metadata_and_body(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("缺少分块 frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("分块 frontmatter 未结束")

    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.fullmatch(r"([a-z0-9_]+):\s*(.+)", line)
        if not match:
            continue
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        metadata[match.group(1)] = value

    after = text[end + len("\n---\n") :].lstrip("\n")
    if "\n\n" not in after:
        raise ValueError("分块缺少标题或正文")
    return metadata, after.split("\n\n", 1)[1]


def read_index(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    comments: dict[str, str] = {}
    data: list[str] = []
    for line in lines:
        if line.startswith("# "):
            key, separator, value = line[2:].partition("\t")
            if separator:
                comments[key] = value
        elif line:
            data.append(line)
    return comments, list(csv.DictReader(data, delimiter="\t"))


def verify(source: Path, index: Path) -> dict[str, object]:
    errors: list[str] = []
    if not source.is_file():
        return {"ok": False, "errors": [f"未找到源历史：{source}"]}
    if not index.is_file():
        return {"ok": False, "errors": [f"未找到历史索引：{index}"]}

    raw = source.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return {"ok": False, "errors": [f"源历史不是有效 UTF-8：{exc}"]}

    comments, rows = read_index(index)
    source_hash = sha256(raw).hexdigest()
    if comments.get("source_sha256") != source_hash:
        errors.append("索引中的源文件 SHA-256 与当前源文件不一致")
    if comments.get("source_chars") != str(len(text)):
        errors.append("索引中的源字符数与当前源文件不一致")
    if comments.get("coverage_status") != "PASS":
        errors.append("索引未声明 coverage_status=PASS")
    if not rows:
        errors.append("历史索引没有分块数据")

    previous_start = -1
    previous_end = 0
    for number, row in enumerate(rows, start=1):
        required = {
            "chunk_id",
            "relative_path",
            "start_char",
            "end_char_exclusive",
            "chars",
            "chunk_sha256",
        }
        if not required.issubset(row):
            errors.append("历史索引缺少必需列")
            break
        try:
            start = int(row["start_char"])
            end = int(row["end_char_exclusive"])
        except ValueError:
            errors.append(f"分块 {number} 的字符区间不是整数")
            continue

        chunk_path = index.parent / row["relative_path"]
        if not chunk_path.is_file():
            errors.append(f"分块 {number} 不存在：{chunk_path}")
            continue
        if digest(chunk_path) != row["chunk_sha256"]:
            errors.append(f"分块 {number} 文件 SHA-256 不一致")

        try:
            metadata, body = chunk_metadata_and_body(chunk_path)
        except (UnicodeDecodeError, ValueError) as exc:
            errors.append(f"分块 {number} 无法解析：{exc}")
            continue

        if metadata.get("source_sha256") != source_hash:
            errors.append(f"分块 {number} 的源 SHA-256 不一致")
        if metadata.get("start_char") != str(start):
            errors.append(f"分块 {number} 的 start_char 与索引不一致")
        if metadata.get("end_char_exclusive") != str(end):
            errors.append(f"分块 {number} 的 end_char_exclusive 与索引不一致")
        if int(row["chars"]) != end - start:
            errors.append(f"分块 {number} 的字符数与区间不一致")
        if start < 0 or end <= start or end > len(text):
            errors.append(f"分块 {number} 的字符区间越界")
        elif body != text[start:end]:
            errors.append(f"分块 {number} 正文与源字符区间不一致")

        if number == 1 and start != 0:
            errors.append("第一个分块没有从字符 0 开始")
        if number > 1 and (start <= previous_start or start > previous_end):
            errors.append(f"分块 {number} 与前一块之间存在乱序或空洞")
        previous_start, previous_end = start, end

    if rows and previous_end != len(text):
        errors.append("最后一个分块没有覆盖到源历史末尾")

    return {
        "ok": not errors,
        "source": str(source),
        "source_sha256": source_hash,
        "source_chars": len(text),
        "chunks": len(rows),
        "coverage_exact": not errors,
        "errors": errors,
    }


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="核验会话历史分块与源文件完全一致。")
    parser.add_argument("--source", required=True, type=Path, help="原始 UTF-8 历史文件。")
    parser.add_argument(
        "--index", required=True, type=Path, help="chunk_history.py 生成的 history-index.tsv。"
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON。")
    args = parser.parse_args()

    result = verify(args.source.expanduser().resolve(), args.index.expanduser().resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("通过" if result["ok"] else "失败")
        print(
            f"源字符数={result.get('source_chars', 0)} "
            f"分块数={result.get('chunks', 0)} "
            f"精确覆盖={result.get('coverage_exact', False)}"
        )
        for error in result.get("errors", []):
            print(f"错误：{error}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
