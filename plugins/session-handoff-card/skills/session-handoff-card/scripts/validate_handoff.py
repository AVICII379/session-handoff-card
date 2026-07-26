#!/usr/bin/env python3
"""使用 Python 标准库校验 session-handoff-card/v1.2 中文交接卡。"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys


PROTOCOL = "session-handoff-card/v1.2"
ALLOWED_STATUSES = {"DRAFT", "HANDOFF_READY", "BLOCKED", "WAITING", "COMPLETE"}
HISTORY_COVERAGE = {"UNKNOWN", "FULL", "PARTIAL", "UNAVAILABLE"}
EVIDENCE_STATES = {"VERIFIED", "USER-PROVIDED", "UNVERIFIED", "STALE", "BLOCKED"}
REQUIRED_FRONTMATTER = {
    "handoff_protocol",
    "handoff_id",
    "created_at",
    "updated_at",
    "status",
    "history_coverage",
    "language",
    "project_root",
    "card_path",
    "source_session",
    "target_models",
}
REQUIRED_HEADINGS = [
    "## 1. 当前目标与边界",
    "## 2. 已核验证据与现状",
    "## 3. 唯一下一步",
    "## 4. 接手说明",
]
REQUIRED_BULLETS = [
    "当前目标",
    "当前状态",
    "失效要求",
    "用户边界与偏好",
    "已完成工作",
    "失败、阻塞与未决",
    "下一动作",
    "预期输出",
    "验证方式",
    "停止条件",
    "历史来源与覆盖",
    "上下文缺口与影响",
    "最小接手附件",
    "路径映射或仓库定位",
    "新会话首条提示词",
    "无法访问原环境时的降级方案",
]
SOURCE_PREFIXES = (
    "file:",
    "dir:",
    "command:",
    "git:",
    "url:",
    "artifact:",
    "history:",
    "user-statement:",
)
SECRET_PATTERNS = [
    ("OpenAI 风格 API 密钥", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("GitHub 令牌", re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}\b")),
    ("AWS 访问密钥", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("私钥块", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Bearer 令牌", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE)),
]


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    if not text.startswith("---\n"):
        return {}, ["缺少 YAML frontmatter"]
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, ["frontmatter 未以 --- 结束"]

    fields: dict[str, str] = {}
    errors: list[str] = []
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([a-z_]+):\s*(.+)", line)
        if not match:
            errors.append(f"不支持的 frontmatter 行：{line}")
            continue
        key, raw_value = match.group(1), match.group(2).strip()
        if raw_value.startswith('"') and raw_value.endswith('"'):
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError:
                errors.append(f"{key} 的双引号 YAML 标量无效")
                continue
        elif raw_value.startswith("'") and raw_value.endswith("'"):
            value = raw_value[1:-1].replace("''", "'")
        else:
            value = raw_value
        fields[key] = value
    return fields, errors


def parse_iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return "T" in value and (
            value.endswith("Z") or re.search(r"[+-]\d{2}:\d{2}$", value) is not None
        )
    except ValueError:
        return False


def bullet_values(text: str, label: str) -> list[str]:
    pattern = re.compile(rf"(?m)^-\s+{re.escape(label)}：\s*(.*)$")
    return [value.strip() for value in pattern.findall(text)]


def strip_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
    return value


def section_text(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    content_start = start + len(heading)
    next_heading = re.search(r"(?m)^##\s+", text[content_start:])
    if next_heading:
        return text[content_start : content_start + next_heading.start()]
    return text[content_start:]


def markdown_table_data_rows(section: str, columns: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [strip_cell(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) != columns or all(cell == "---" for cell in cells):
            continue
        rows.append(cells)
    return rows


def evidence_rows(text: str) -> list[list[str]]:
    section = section_text(text, "## 2. 已核验证据与现状")
    rows = markdown_table_data_rows(section, 6)
    return [row for row in rows if row[0] != "ID"]


def source_path(source: str) -> tuple[str, Path] | None:
    source = strip_cell(source)
    if source.startswith("file:"):
        return "file", Path(source[5:].strip())
    if source.startswith("dir:"):
        return "dir", Path(source[4:].strip())
    return None


def resolved_from_root(path: Path, project_root: Path | None) -> Path:
    if path.is_absolute():
        return path
    if project_root is None:
        return path
    return project_root / path


def validate(
    card: Path,
    strict: bool,
    check_paths: bool,
    source_history: Path | None = None,
) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    if not card.is_file():
        return {"ok": False, "errors": [f"未找到交接卡：{card}"], "warnings": []}
    try:
        text = card.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"ok": False, "errors": ["交接卡不是有效 UTF-8"], "warnings": []}

    fields, frontmatter_errors = parse_frontmatter(text)
    errors.extend(frontmatter_errors)
    for key in sorted(REQUIRED_FRONTMATTER - fields.keys()):
        errors.append(f"缺少 frontmatter 字段：{key}")

    if fields.get("handoff_protocol") != PROTOCOL:
        errors.append(f"handoff_protocol 必须为 {PROTOCOL}")
    if fields.get("language") != "zh-CN":
        errors.append("language 必须为 zh-CN")

    status = fields.get("status", "")
    if status not in ALLOWED_STATUSES:
        errors.append(f"status 必须是：{', '.join(sorted(ALLOWED_STATUSES))}")
    if strict and status == "DRAFT":
        errors.append("严格校验不接受 DRAFT")

    history_coverage = fields.get("history_coverage", "")
    if history_coverage not in HISTORY_COVERAGE:
        errors.append(f"history_coverage 必须是：{', '.join(sorted(HISTORY_COVERAGE))}")
    if strict and history_coverage == "UNKNOWN":
        errors.append("严格校验不接受 UNKNOWN 历史覆盖状态")
    if status == "HANDOFF_READY" and history_coverage in {"UNKNOWN", "UNAVAILABLE"}:
        errors.append("HANDOFF_READY 卡片的历史覆盖不能是 UNKNOWN 或 UNAVAILABLE")
    if history_coverage == "UNAVAILABLE" and status != "BLOCKED":
        errors.append("history_coverage=UNAVAILABLE 时 status 必须为 BLOCKED")
    if history_coverage == "PARTIAL":
        warnings.append("历史覆盖为 PARTIAL；接手前必须评估上下文缺口")

    for key in ("created_at", "updated_at"):
        value = fields.get(key, "")
        if value and not parse_iso8601(value):
            errors.append(f"{key} 必须是带时区的 ISO 8601")

    project_root: Path | None = None
    if fields.get("project_root"):
        project_root = Path(fields["project_root"])
        if check_paths and not project_root.is_absolute():
            errors.append(f"project_root 不是绝对路径：{project_root}")
        elif check_paths and not project_root.is_dir():
            errors.append(f"project_root 目录不存在：{project_root}")

    for heading in REQUIRED_HEADINGS:
        count = text.count(heading)
        if count != 1:
            errors.append(f"必填标题必须恰好出现一次：{heading}（实际 {count}）")

    unresolved = sorted(
        set(re.findall(r"\{\{[A-Z0-9_]+\}\}|待填写-必填|TBD-REQUIRED", text))
    )
    if unresolved:
        errors.append("存在未解决模板标记：" + "、".join(unresolved))

    for label in REQUIRED_BULLETS:
        values = bullet_values(text, label)
        if len(values) != 1:
            errors.append(f"必填字段必须恰好出现一次：{label}（实际 {len(values)}）")
        elif not values[0]:
            errors.append(f"必填字段为空：{label}")

    quick_section = section_text(text, "## 1. 当前目标与边界")
    if not re.search(r"(?m)^\s*-\s+\[[ xX]\]\s+\S+", quick_section):
        errors.append("验收标准至少需要一个 Markdown 复选项")

    prompts = bullet_values(text, "新会话首条提示词")
    if len(prompts) == 1 and len(prompts[0]) < 20:
        errors.append("新会话首条提示词过短，必须写明读取、复核和接手要求")

    actions = bullet_values(text, "下一动作")
    if status == "COMPLETE":
        complete_values = {"无，工作已完成", "无；工作已完成", "不适用，工作已完成"}
        if len(actions) > 1:
            errors.append("COMPLETE 卡片最多只能有一个下一动作字段")
        elif len(actions) == 1 and actions[0] not in complete_values:
            warnings.append("COMPLETE 卡片仍写有动作，请确认工作确已完成")
    elif len(actions) != 1 or not actions[0]:
        errors.append(f"非 COMPLETE 卡片必须恰有一个非空下一动作（实际 {len(actions)}）")

    rows = evidence_rows(text)
    if not rows:
        errors.append("证据索引至少需要一条数据")
    evidence_ids: set[str] = set()
    verified_evidence = 0
    for row_number, row in enumerate(rows, start=1):
        evidence_id, _claim, source, _proof, evidence_state, checked = row
        if not re.fullmatch(r"E\d+", evidence_id):
            errors.append(f"证据第 {row_number} 行 ID 无效：{evidence_id}")
        if evidence_id in evidence_ids:
            errors.append(f"证据 ID 重复：{evidence_id}")
        evidence_ids.add(evidence_id)
        if not source.startswith(SOURCE_PREFIXES):
            errors.append(f"证据 {evidence_id} 的来源类型不支持：{source}")
        if evidence_state not in EVIDENCE_STATES:
            errors.append(f"证据 {evidence_id} 的状态无效：{evidence_state}")
        elif evidence_state == "VERIFIED":
            verified_evidence += 1
        if not parse_iso8601(checked):
            errors.append(f"证据 {evidence_id} 的最后核验时间必须是带时区的 ISO 8601")
        if check_paths:
            parsed = source_path(source)
            if parsed:
                expected_type, raw_path = parsed
                path = resolved_from_root(raw_path, project_root)
                if not path.is_absolute():
                    errors.append(f"证据 {evidence_id} 路径无法定位：{raw_path}")
                elif expected_type == "file" and not path.is_file():
                    errors.append(f"证据 {evidence_id} 文件不存在：{path}")
                elif expected_type == "dir" and not path.is_dir():
                    errors.append(f"证据 {evidence_id} 目录不存在：{path}")

    if status == "HANDOFF_READY" and verified_evidence == 0:
        errors.append("HANDOFF_READY 卡片至少需要一条 VERIFIED 证据")
    if status == "COMPLETE" and re.search(r"(?m)^\s*-\s+\[\s\]\s+", text):
        errors.append("COMPLETE 卡片仍有未勾选验收标准")

    for label, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"检测到可能未脱敏的敏感信息：{label}")

    if fields.get("card_path"):
        declared = resolved_from_root(Path(fields["card_path"]), project_root)
        if check_paths and not declared.is_absolute():
            errors.append(f"card_path 无法定位：{fields['card_path']}")
        elif declared.is_absolute() and declared.resolve() != card.resolve():
            warnings.append(f"card_path 指向其他位置：{declared}")

    if not check_paths:
        warnings.append("未检查 file: 和 dir: 证据路径")
    if status in {"BLOCKED", "WAITING"}:
        warnings.append(f"卡片状态为 {status}，执行前应先处理或检查该状态")
    if len(rows) > 6:
        warnings.append("证据超过 6 条；请只在核心卡保留会改变接手决定的高影响项")
    if len(text) > 8000:
        warnings.append("交接卡超过 8000 字符；建议删除重复说明并外置低频细节")
    elif len(text) > 5000:
        warnings.append("交接卡超过 5000 字符；普通任务应压缩到约 1500–3500 字符")

    source_chars: int | None = None
    compression_ratio: float | None = None
    if source_history is not None:
        if not source_history.is_file():
            errors.append(f"未找到源历史：{source_history}")
        else:
            try:
                source_text = source_history.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                errors.append("源历史不是有效 UTF-8")
            else:
                source_chars = len(source_text)
                if source_chars:
                    compression_ratio = round(len(text) / source_chars, 3)
                    if source_chars >= 3000 and compression_ratio >= 0.85:
                        warnings.append(
                            "交接卡已达到源历史的 85% 或更长；请删除复述并外置低频细节"
                        )

    return {
        "ok": not errors,
        "protocol": fields.get("handoff_protocol"),
        "status": status or None,
        "history_coverage": history_coverage or None,
        "evidence_rows": len(rows),
        "card_chars": len(text),
        "source_chars": source_chars,
        "compression_ratio": compression_ratio,
        "path_checks": check_paths,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="校验精简中文会话交接卡。")
    parser.add_argument("card", type=Path, help="待校验的 Markdown 交接卡。")
    parser.add_argument("--strict", action="store_true", help="拒绝 DRAFT/UNKNOWN。")
    parser.add_argument(
        "--check-paths",
        action="store_true",
        help="检查 file: 和 dir: 证据；相对路径以 project_root 为基准。",
    )
    parser.add_argument(
        "--source-history",
        type=Path,
        help="可选源历史；用于报告压缩比并发现交接卡反向膨胀。",
    )
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON。")
    args = parser.parse_args()

    source_history = (
        args.source_history.expanduser().resolve() if args.source_history else None
    )
    result = validate(
        args.card.expanduser().resolve(),
        args.strict,
        args.check_paths,
        source_history,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("通过" if result["ok"] else "失败")
        print(
            f"协议={result.get('protocol')} 状态={result.get('status')} "
            f"历史覆盖={result.get('history_coverage')} "
            f"证据行={result.get('evidence_rows', 0)} "
            f"字符数={result.get('card_chars', 0)} "
            f"压缩比={result.get('compression_ratio')} "
            f"路径检查={result.get('path_checks', False)}"
        )
        for error in result["errors"]:
            print(f"错误：{error}")
        for warning in result["warnings"]:
            print(f"警告：{warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
