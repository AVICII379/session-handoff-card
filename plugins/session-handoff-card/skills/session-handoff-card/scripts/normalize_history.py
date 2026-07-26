#!/usr/bin/env python3
"""Normalize common conversation exports into stable UTF-8 Markdown messages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


ROLES = {
    "user": "USER", "human": "USER", "client": "USER",
    "assistant": "ASSISTANT", "ai": "ASSISTANT", "bot": "ASSISTANT",
}


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def content_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [content_text(item) for item in value]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(value, dict):
        for key in ("text", "content", "value"):
            if key in value:
                found = content_text(value[key])
                if found:
                    return found
        if "parts" in value:
            return content_text(value["parts"])
    return ""


def message_from_object(obj: Any) -> tuple[str, str] | None:
    if not isinstance(obj, dict):
        return None
    role_raw: Any = obj.get("role") or obj.get("sender") or obj.get("author")
    if isinstance(role_raw, dict):
        role_raw = role_raw.get("role") or role_raw.get("name")
    role = ROLES.get(str(role_raw).casefold())
    if not role:
        return None
    content = content_text(obj.get("content", obj.get("text", obj.get("message", ""))))
    return (role, content) if content else None


def chatgpt_messages(conversation: dict[str, Any]) -> list[tuple[str, str]]:
    mapping = conversation.get("mapping")
    if not isinstance(mapping, dict):
        return []
    ordered: list[dict[str, Any]] = []
    current = conversation.get("current_node")
    visited: set[str] = set()
    while isinstance(current, str) and current in mapping and current not in visited:
        visited.add(current)
        node = mapping[current]
        if isinstance(node, dict) and isinstance(node.get("message"), dict):
            ordered.append(node["message"])
        current = node.get("parent") if isinstance(node, dict) else None
    if ordered:
        ordered.reverse()
    else:
        nodes = [node for node in mapping.values() if isinstance(node, dict) and isinstance(node.get("message"), dict)]
        nodes.sort(key=lambda node: node["message"].get("create_time") or 0)
        ordered = [node["message"] for node in nodes]
    return [message for item in ordered if (message := message_from_object(item))]


def generic_messages(data: Any) -> list[tuple[str, str]]:
    if isinstance(data, dict):
        for key in ("messages", "chat_messages", "conversation", "turns", "items"):
            if isinstance(data.get(key), list):
                messages = [message for item in data[key] if (message := message_from_object(item))]
                if messages:
                    return messages
        direct = message_from_object(data)
        if direct:
            return [direct]
        for value in data.values():
            messages = generic_messages(value)
            if messages:
                return messages
    elif isinstance(data, list):
        direct = [message for item in data if (message := message_from_object(item))]
        if direct:
            return direct
        for item in data:
            messages = generic_messages(item)
            if messages:
                return messages
    return []


def select_conversation(data: Any, selector: str | None) -> Any:
    if not isinstance(data, list) or not data:
        return data
    candidates = [item for item in data if isinstance(item, dict)]
    if not candidates:
        return data
    if selector:
        if selector.isdigit():
            index = int(selector)
            if 0 <= index < len(candidates):
                return candidates[index]
        folded = selector.casefold()
        for item in candidates:
            title = str(item.get("title") or item.get("name") or "")
            if folded in title.casefold():
                return item
        raise ValueError(f"找不到会话：{selector}")
    return candidates[0]


def detect_platform(data: Any, suffix: str) -> str:
    sample = data[0] if isinstance(data, list) and data else data
    if isinstance(sample, dict) and "mapping" in sample:
        return "chatgpt"
    if isinstance(sample, dict) and "chat_messages" in sample:
        return "claude"
    if suffix == ".jsonl":
        return "codex"
    return "generic"


def parse_export(path: Path, platform: str, selector: str | None) -> tuple[str, list[tuple[str, str]]]:
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.casefold() not in {".json", ".jsonl"}:
        return "plain", [("SOURCE", raw.strip())]
    if path.suffix.casefold() == ".jsonl":
        data: Any = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        data = json.loads(raw)
    direct_message_list = isinstance(data, list) and any(message_from_object(item) for item in data)
    selected = data if path.suffix.casefold() == ".jsonl" or direct_message_list else select_conversation(data, selector)
    actual = detect_platform(data, path.suffix.casefold()) if platform == "auto" else platform
    messages = chatgpt_messages(selected) if actual == "chatgpt" else generic_messages(selected)
    if not messages:
        raise ValueError("没有找到可识别的 user/assistant 消息；可先转为 role/content JSON。")
    return actual, messages


def markdown_output(source_name: str, platform: str, messages: list[tuple[str, str]]) -> str:
    lines = [
        "---", 'normalized_history: "session-handoff-card/history-v1"',
        f'source_name: "{source_name.replace(chr(34), chr(39))}"',
        f'platform: "{platform}"', f"message_count: {len(messages)}", "---", "",
        "# Normalized conversation history", "",
    ]
    for index, (role, content) in enumerate(messages, start=1):
        safe = re.sub(r"\r\n?", "\n", content).strip()
        lines.extend([f"## {index:04d} {role}", "", safe, ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--platform", choices=("auto", "chatgpt", "claude", "gemini", "codex", "generic"), default="auto")
    parser.add_argument("--conversation", help="多会话导出中的零基索引或标题片段；默认第一项。")
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_file():
        parser.error(f"输入不存在：{source}")
    if output.exists():
        parser.error(f"拒绝覆盖已有输出：{output}")
    try:
        platform, messages = parse_export(source, args.platform, args.conversation)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_output(source.name, platform, messages), encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "platform": platform, "messages": len(messages), "output": output.name}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
