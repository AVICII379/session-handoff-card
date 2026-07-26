#!/usr/bin/env python3
"""Create a v1.3 session handoff draft from a bundled template."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid


TEMPLATES = {
    ("verified", "zh-CN"): "handoff-card-template.md",
    ("quick", "zh-CN"): "quick-handoff-card-template.md",
    ("verified", "en"): "handoff-card-template.en.md",
    ("quick", "en"): "quick-handoff-card-template.en.md",
}


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
    parser = argparse.ArgumentParser(description="创建 session-handoff-card/v1.3 草稿。")
    parser.add_argument("--output", required=True, type=Path, help="交接卡输出路径。")
    parser.add_argument(
        "--profile", choices=("quick", "verified"), default="quick",
        help="quick 适合纯聊天，verified 适合项目或外部证据；默认 quick。",
    )
    parser.add_argument(
        "--delivery", choices=("text", "file", "repo"), default="text",
        help="交付方式；text 不要求项目路径，默认 text。",
    )
    parser.add_argument("--language", choices=("zh-CN", "en"), default="zh-CN")
    parser.add_argument("--project-root", type=Path, help="可选项目根目录。")
    parser.add_argument("--source-session", default="", help="不含秘密的来源会话标识。")
    parser.add_argument(
        "--evidence-mode", choices=("conversation", "external", "mixed"),
        help="证据类型；quick 默认 conversation，verified 默认 mixed。",
    )
    args = parser.parse_args()

    if args.delivery == "repo" and args.project_root is None:
        parser.error("delivery=repo 时必须提供 --project-root")

    script_dir = Path(__file__).resolve().parent
    template = script_dir.parent / "assets" / TEMPLATES[(args.profile, args.language)]
    if not template.is_file():
        raise SystemExit(f"未找到模板：{template}")

    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"拒绝覆盖已有交接卡：{output}\n请先读取并更新现有交接卡。")

    project_root = args.project_root.expanduser().resolve() if args.project_root else None
    timestamp = utc_now()
    handoff_id = f"HOF-{timestamp.replace('-', '').replace(':', '')}-{uuid.uuid4().hex[:8]}"
    evidence_mode = args.evidence_mode or (
        "conversation" if args.profile == "quick" else "mixed"
    )
    card_path = str(output) if args.delivery in {"file", "repo"} else ""
    replacements = {
        "{{HANDOFF_ID}}": handoff_id,
        "{{CREATED_AT}}": timestamp,
        "{{UPDATED_AT}}": timestamp,
        "{{DELIVERY_MODE}}": args.delivery,
        "{{EVIDENCE_MODE}}": evidence_mode,
        "{{PROJECT_ROOT}}": yaml_single_quoted(str(project_root) if project_root else ""),
        "{{CARD_PATH}}": yaml_single_quoted(card_path),
        "{{SOURCE_SESSION}}": yaml_single_quoted(args.source_session.strip()),
    }

    content = template.read_text(encoding="utf-8")
    for token, value in replacements.items():
        content = content.replace(token, value)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8", newline="\n")
    labels = {"zh-CN": ("交接卡", "交接ID", "状态", "模式"), "en": ("card", "handoff_id", "status", "profile")}
    card_label, id_label, status_label, profile_label = labels[args.language]
    print(f"{card_label}={output}")
    print(f"{id_label}={handoff_id}")
    print(f"{status_label}=DRAFT")
    print(f"{profile_label}={args.profile.upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
