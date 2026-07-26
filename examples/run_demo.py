#!/usr/bin/env python3
"""运行一个不联网、可重复的长会话交接演示。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "long-session"
PLUGIN_ROOT = REPO_ROOT / "plugins" / "session-handoff-card"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "session-handoff-card"
CHUNK_SCRIPT = SKILL_ROOT / "scripts" / "chunk_history.py"
VERIFY_HISTORY_SCRIPT = SKILL_ROOT / "scripts" / "verify_history.py"
VALIDATE_SCRIPT = SKILL_ROOT / "scripts" / "validate_handoff.py"
CONVERSATION = EXAMPLE_DIR / "conversation.md"
CARD_TEMPLATE = EXAMPLE_DIR / "handoff-card.template.md"


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def yaml_single_quoted(value: str) -> str:
    return value.replace("'", "''")


def create_card(output_dir: Path, history_index: Path) -> Path:
    card_path = output_dir / "handoff-card.md"
    replacements = {
        "{{PROJECT_ROOT}}": yaml_single_quoted(str(REPO_ROOT)),
        "{{CARD_PATH}}": yaml_single_quoted(str(card_path.resolve())),
        "{{CONVERSATION_PATH}}": str(CONVERSATION.resolve()),
        "{{HISTORY_INDEX}}": str(history_index.resolve()),
        "{{SKILL_PATH}}": str((SKILL_ROOT / "SKILL.md").resolve()),
    }
    content = CARD_TEMPLATE.read_text(encoding="utf-8")
    for token, value in replacements.items():
        content = content.replace(token, value)
    if "{{" in content or "}}" in content:
        raise RuntimeError("演示交接卡仍含未替换占位符")
    card_path.write_text(content, encoding="utf-8", newline="\n")
    return card_path


def execute_demo(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise RuntimeError(f"拒绝写入非空输出目录：{output_dir}")

    history_dir = output_dir / "history"
    run_checked(
        [
            sys.executable,
            str(CHUNK_SCRIPT),
            "--input",
            str(CONVERSATION),
            "--output-dir",
            str(history_dir),
            "--max-chars",
            "1000",
            "--overlap-chars",
            "200",
        ]
    )
    history_index = history_dir / "history-index.tsv"
    source_text = CONVERSATION.read_text(encoding="utf-8-sig")
    history_checked = run_checked(
        [
            sys.executable,
            str(VERIFY_HISTORY_SCRIPT),
            "--source",
            str(CONVERSATION),
            "--index",
            str(history_index),
            "--json",
        ]
    )
    history_validation = json.loads(history_checked.stdout)
    chunks = int(history_validation["chunks"])
    coverage_exact = bool(history_validation["coverage_exact"])
    if not coverage_exact:
        raise RuntimeError("历史分块未与源文件字符区间完全一致")

    card_path = create_card(output_dir, history_index)
    validated = run_checked(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            str(card_path),
            "--strict",
            "--check-paths",
            "--source-history",
            str(CONVERSATION),
            "--json",
        ]
    )
    validation = json.loads(validated.stdout)
    result = {
        "ok": bool(validation["ok"] and coverage_exact),
        "protocol": validation.get("protocol"),
        "status": validation.get("status"),
        "history_coverage": validation.get("history_coverage"),
        "source_chars": len(source_text),
        "chunks": chunks,
        "coverage_exact": coverage_exact,
        "evidence_rows": validation.get("evidence_rows"),
        "card_chars": validation.get("card_chars"),
        "compression_ratio": validation.get("compression_ratio"),
        "validator_errors": len(validation.get("errors", [])),
        "validator_warnings": len(validation.get("warnings", [])),
        "card_path": str(card_path.resolve()),
        "history_index": str(history_index.resolve()),
    }
    if not result["ok"]:
        raise RuntimeError(json.dumps(validation, ensure_ascii=False))
    return result


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="运行长会话交接卡端到端演示。")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="保留演示产物的空目录；省略时使用并清理临时目录。",
    )
    args = parser.parse_args()

    if args.output_dir:
        result = execute_demo(args.output_dir.expanduser().resolve())
        result["persisted"] = True
    else:
        with tempfile.TemporaryDirectory(prefix="session-handoff-demo-") as temp:
            result = execute_demo(Path(temp))
            result["persisted"] = False
            result["card_path"] = None
            result["history_index"] = None

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
