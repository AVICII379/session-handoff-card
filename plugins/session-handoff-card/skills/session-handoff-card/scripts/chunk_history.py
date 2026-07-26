#!/usr/bin/env python3
"""把超长 UTF-8 会话导出切成连续、带重叠且可核验的 Markdown 分块。"""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
from pathlib import Path
import sys


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def yaml_single_quoted(value: str) -> str:
    return value.replace("'", "''")


def split_ranges(text: str, max_chars: int, overlap_chars: int) -> list[tuple[int, int]]:
    if not text:
        return [(0, 0)]
    ranges: list[tuple[int, int]] = []
    start = 0
    total = len(text)
    while start < total:
        hard_end = min(start + max_chars, total)
        end = hard_end
        if hard_end < total:
            minimum_end = start + max_chars // 2
            newline = text.rfind("\n", minimum_end, hard_end)
            if newline >= minimum_end:
                end = newline + 1
        if end <= start:
            end = hard_end
        ranges.append((start, end))
        if end >= total:
            break
        next_start = end - overlap_chars
        if next_start <= start:
            next_start = end
        start = next_start
    return ranges


def verify_coverage(ranges: list[tuple[int, int]], total_chars: int) -> bool:
    if not ranges or ranges[0][0] != 0 or ranges[-1][1] != total_chars:
        return False
    return all(
        current_start < current_end
        and next_start > current_start
        and next_start <= current_end
        for (current_start, current_end), (next_start, _next_end) in zip(ranges, ranges[1:])
    )


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(
        description="将长会话文本切成连续分块，并生成 history-index.tsv。"
    )
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 文本、Markdown、JSON 或 JSONL。")
    parser.add_argument("--output-dir", required=True, type=Path, help="分块输出目录。")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=40000,
        help="每块最大字符数，默认 40000，最小 1000。",
    )
    parser.add_argument(
        "--overlap-chars",
        type=int,
        default=1000,
        help="相邻块重叠字符数，默认 1000，必须小于 max-chars 的四分之一。",
    )
    args = parser.parse_args()

    if args.max_chars < 1000:
        raise SystemExit("--max-chars 不能小于 1000")
    if args.overlap_chars < 0 or args.overlap_chars >= args.max_chars // 4:
        raise SystemExit("--overlap-chars 必须大于等于 0 且小于 max-chars 的四分之一")

    input_path = args.input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not input_path.is_file():
        raise SystemExit(f"未找到历史文件：{input_path}")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"拒绝写入非空目录：{output_dir}")

    raw = input_path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"历史文件不是有效 UTF-8：{exc}") from exc
    if not text:
        raise SystemExit("历史文件为空，无法创建上下文分块")

    ranges = split_ranges(text, args.max_chars, args.overlap_chars)
    coverage_ok = verify_coverage(ranges, len(text))
    if not coverage_ok:
        raise SystemExit("内部覆盖校验失败，未写出分块")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_hash = sha256_bytes(raw)
    source_label = yaml_single_quoted(str(input_path))
    rows: list[dict[str, object]] = []
    total_chunks = len(ranges)

    for index, (start, end) in enumerate(ranges, start=1):
        chunk_id = f"chunk-{index:04d}"
        chunk_path = output_dir / f"{chunk_id}.md"
        body = text[start:end]
        header = (
            "---\n"
            f'history_chunk: "{index}/{total_chunks}"\n'
            f"source_file: '{source_label}'\n"
            f'source_sha256: "{source_hash}"\n'
            f"start_char: {start}\n"
            f"end_char_exclusive: {end}\n"
            "---\n\n"
            f"# 会话历史分块 {index:04d}/{total_chunks:04d}\n\n"
        )
        chunk_path.write_text(header + body, encoding="utf-8", newline="\n")
        rows.append(
            {
                "chunk_id": chunk_id,
                "relative_path": chunk_path.name,
                "start_char": start,
                "end_char_exclusive": end,
                "chars": end - start,
                "chunk_sha256": sha256_bytes(chunk_path.read_bytes()),
            }
        )

    index_path = output_dir / "history-index.tsv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"# source_file\t{input_path}\n")
        handle.write(f"# source_sha256\t{source_hash}\n")
        handle.write(f"# source_chars\t{len(text)}\n")
        handle.write(f"# max_chars\t{args.max_chars}\n")
        handle.write(f"# overlap_chars\t{args.overlap_chars}\n")
        handle.write("# coverage_status\tPASS\n")
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "chunk_id",
                "relative_path",
                "start_char",
                "end_char_exclusive",
                "chars",
                "chunk_sha256",
            ],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"历史索引={index_path}")
    print(f"源文件SHA256={source_hash}")
    print(f"源字符数={len(text)}")
    print(f"分块数={total_chunks}")
    print("覆盖校验=PASS")
    print("提醒：分块保留原始内容，交给其他模型前请先检查敏感信息。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
