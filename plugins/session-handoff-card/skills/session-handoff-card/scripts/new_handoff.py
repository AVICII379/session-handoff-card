#!/usr/bin/env python3
"""从内置模板创建中文会话交接卡草稿。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def yaml_single_quoted(value: str) -> str:
    return value.replace("'", "''")


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(
        description="创建 session-handoff-card/v1.2 精简中文 Markdown 草稿。"
    )
    parser.add_argument("--output", required=True, type=Path, help="交接卡输出路径。")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="写入交接卡的项目根目录；默认使用当前目录。",
    )
    parser.add_argument(
        "--source-session",
        default="未记录",
        help="不含秘密的来源会话或模型标识。",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    template = script_dir.parent / "assets" / "handoff-card-template.md"
    if not template.is_file():
        raise SystemExit(f"未找到模板：{template}")

    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit(
            f"拒绝覆盖已有交接卡：{output}\n"
            "请先读取并更新现有规范交接卡。"
        )

    project_root = args.project_root.expanduser().resolve()
    timestamp = utc_now()
    handoff_id = f"HOF-{timestamp.replace('-', '').replace(':', '')}-{uuid.uuid4().hex[:8]}"

    replacements = {
        "{{HANDOFF_ID}}": handoff_id,
        "{{CREATED_AT}}": timestamp,
        "{{UPDATED_AT}}": timestamp,
        "{{PROJECT_ROOT}}": yaml_single_quoted(str(project_root)),
        "{{CARD_PATH}}": yaml_single_quoted(str(output)),
        "{{SOURCE_SESSION}}": yaml_single_quoted(args.source_session.strip() or "未记录"),
    }

    content = template.read_text(encoding="utf-8")
    for token, value in replacements.items():
        content = content.replace(token, value)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8", newline="\n")
    print(f"交接卡={output}")
    print(f"交接ID={handoff_id}")
    print("状态=DRAFT")
    print("历史覆盖=UNKNOWN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
