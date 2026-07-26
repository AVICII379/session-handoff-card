#!/usr/bin/env python3
"""Validate v1.2 legacy and v1.3 session handoff cards with stdlib only."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys


CURRENT_PROTOCOL = "session-handoff-card/v1.3"
LEGACY_PROTOCOL = "session-handoff-card/v1.2"
SUPPORTED_PROTOCOLS = {CURRENT_PROTOCOL, LEGACY_PROTOCOL}
ALLOWED_STATUSES = {"DRAFT", "HANDOFF_READY", "BLOCKED", "WAITING", "COMPLETE"}
HISTORY_COVERAGE = {"UNKNOWN", "FULL", "PARTIAL", "UNAVAILABLE"}
EVIDENCE_STATES = {"VERIFIED", "USER-PROVIDED", "UNVERIFIED", "STALE", "BLOCKED"}
PROFILES = {"QUICK", "VERIFIED"}
DELIVERY_MODES = {"text", "file", "repo"}
EVIDENCE_MODES = {"conversation", "external", "mixed"}
V12_FRONTMATTER = {
    "handoff_protocol", "handoff_id", "created_at", "updated_at", "status",
    "history_coverage", "language", "project_root", "card_path", "source_session",
    "target_models",
}
V13_FRONTMATTER = {
    "handoff_protocol", "handoff_id", "created_at", "updated_at", "status",
    "history_coverage", "language", "profile", "delivery_mode", "evidence_mode",
    "target_models",
}
V13_OPTIONAL_FRONTMATTER = {"project_root", "card_path", "source_session"}
SCHEMAS = {
    ("zh-CN", "VERIFIED"): {
        "headings": ["## 1. 当前目标与边界", "## 2. 已核验证据与现状", "## 3. 唯一下一步", "## 4. 接手说明"],
        "bullets": ["当前目标", "当前状态", "失效要求", "用户边界与偏好", "已完成工作", "失败、阻塞与未决", "下一动作", "预期输出", "验证方式", "停止条件", "后续候选（非授权）", "历史来源与覆盖", "上下文缺口与影响", "最小接手附件", "路径映射或仓库定位", "新会话首条提示词", "无法访问原环境时的降级方案"],
        "action": "下一动作", "prompt": "新会话首条提示词", "later": "后续候选（非授权）", "evidence_heading": "## 2. 已核验证据与现状", "table_header": "ID", "complete": {"无，工作已完成", "无；工作已完成", "不适用，工作已完成"},
    },
    ("zh-CN", "QUICK"): {
        "headings": ["## 1. 现在要做什么", "## 2. 必须带走的上下文", "## 3. 下一步", "## 4. 新会话怎么接"],
        "bullets": ["当前目标", "当前状态", "不要做", "已完成", "关键约束", "未决与缺口", "下一动作", "预期输出", "停止条件", "后续候选（非授权）", "历史覆盖", "最小附件", "新会话首条提示词", "无法访问时"],
        "action": "下一动作", "prompt": "新会话首条提示词", "later": "后续候选（非授权）", "gap": "未决与缺口", "evidence_heading": None, "table_header": "ID", "complete": {"无，工作已完成", "无；工作已完成", "不适用，工作已完成"},
    },
    ("en", "VERIFIED"): {
        "headings": ["## 1. Current goal and boundaries", "## 2. Verified evidence and state", "## 3. The one next step", "## 4. Receiving instructions"],
        "bullets": ["Current goal", "Current state", "Superseded requirements", "User boundaries and preferences", "Completed work", "Failures, blockers, and open issues", "Next action", "Expected output", "Verification", "Stop condition", "Later candidates (not authorized)", "History source and coverage", "Context gaps and impact", "Minimum attachments", "Path mapping or repository location", "First prompt in the new session", "Fallback without the original environment"],
        "action": "Next action", "prompt": "First prompt in the new session", "later": "Later candidates (not authorized)", "evidence_heading": "## 2. Verified evidence and state", "table_header": "ID", "complete": {"None, work is complete", "None; work is complete", "Not applicable, work is complete"},
    },
    ("en", "QUICK"): {
        "headings": ["## 1. What we are doing now", "## 2. Context that must survive", "## 3. Next step", "## 4. How the new session should continue"],
        "bullets": ["Current goal", "Current state", "Do not do", "Completed", "Key constraints", "Open issues and gaps", "Next action", "Expected output", "Stop condition", "Later candidates (not authorized)", "History coverage", "Minimum attachments", "First prompt in the new session", "Fallback when access is unavailable"],
        "action": "Next action", "prompt": "First prompt in the new session", "later": "Later candidates (not authorized)", "gap": "Open issues and gaps", "evidence_heading": None, "table_header": "ID", "complete": {"None, work is complete", "None; work is complete", "Not applicable, work is complete"},
    },
}
V12_HEADINGS = ["## 1. 当前目标与边界", "## 2. 已核验证据与现状", "## 3. 唯一下一步", "## 4. 接手说明"]
V12_BULLETS = ["当前目标", "当前状态", "失效要求", "用户边界与偏好", "已完成工作", "失败、阻塞与未决", "下一动作", "预期输出", "验证方式", "停止条件", "历史来源与覆盖", "上下文缺口与影响", "最小接手附件", "路径映射或仓库定位", "新会话首条提示词", "无法访问原环境时的降级方案"]
SOURCE_PREFIXES = ("file:", "dir:", "command:", "git:", "url:", "artifact:", "history:", "user-statement:")
SECRET_PATTERNS = [
    ("OpenAI 风格 API 密钥", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("GitHub 令牌", re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}\b")),
    ("AWS 访问密钥", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("私钥块", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Bearer 令牌", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.I)),
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
        match = re.fullmatch(r"([a-z_]+):\s*(.*)", line)
        if not match:
            errors.append(f"不支持的 frontmatter 行：{line}")
            continue
        key, raw = match.group(1), match.group(2).strip()
        if raw.startswith('"') and raw.endswith('"'):
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                errors.append(f"{key} 的双引号 YAML 标量无效")
                continue
        elif raw.startswith("'") and raw.endswith("'"):
            value = raw[1:-1].replace("''", "'")
        else:
            value = raw
        fields[key] = value
    return fields, errors


def parse_iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return "T" in value and (value.endswith("Z") or re.search(r"[+-]\d{2}:\d{2}$", value) is not None)
    except ValueError:
        return False


def bullet_values(text: str, label: str) -> list[str]:
    pattern = re.compile(rf"(?m)^-\s+{re.escape(label)}(?:：|:)\s*(.*)$")
    return [value.strip() for value in pattern.findall(text)]


def section_text(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    content_start = start + len(heading)
    next_heading = re.search(r"(?m)^##\s+", text[content_start:])
    return text[content_start:content_start + next_heading.start()] if next_heading else text[content_start:]


def strip_cell(value: str) -> str:
    value = value.strip()
    return value[1:-1].strip() if value.startswith("`") and value.endswith("`") else value


def evidence_rows(text: str, heading: str | None) -> list[list[str]]:
    if not heading:
        return []
    rows: list[list[str]] = []
    for line in section_text(text, heading).splitlines():
        if not line.startswith("|"):
            continue
        cells = [strip_cell(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or all(cell == "---" for cell in cells) or cells[0] == "ID":
            continue
        rows.append(cells)
    return rows


def source_path(source: str) -> tuple[str, Path] | None:
    if source.startswith("file:"):
        return "file", Path(source[5:].strip())
    if source.startswith("dir:"):
        return "dir", Path(source[4:].strip())
    return None


def resolved_from_root(path: Path, project_root: Path | None) -> Path:
    return path if path.is_absolute() or project_root is None else project_root / path


def validate(card: Path, strict: bool, check_paths: bool, source_history: Path | None = None) -> dict[str, object]:
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
    protocol = fields.get("handoff_protocol", "")
    if protocol not in SUPPORTED_PROTOCOLS:
        errors.append(f"handoff_protocol 必须是：{', '.join(sorted(SUPPORTED_PROTOCOLS))}")

    legacy = protocol == LEGACY_PROTOCOL
    required_frontmatter = V12_FRONTMATTER if legacy else V13_FRONTMATTER
    for key in sorted(required_frontmatter - fields.keys()):
        errors.append(f"缺少 frontmatter 字段：{key}")
    allowed_frontmatter = V12_FRONTMATTER if legacy else V13_FRONTMATTER | V13_OPTIONAL_FRONTMATTER
    for key in sorted(fields.keys() - allowed_frontmatter):
        if not key.startswith("x_"):
            errors.append(f"不支持的 frontmatter 字段：{key}；自定义扩展必须使用 x_ 前缀")

    language = fields.get("language", "")
    profile = "VERIFIED" if legacy else fields.get("profile", "")
    if legacy and language != "zh-CN":
        errors.append("v1.2 language 必须为 zh-CN")
    if not legacy:
        if language not in {"zh-CN", "en"}:
            errors.append("v1.3 language 必须为 zh-CN 或 en")
        if profile not in PROFILES:
            errors.append(f"profile 必须是：{', '.join(sorted(PROFILES))}")
        if fields.get("delivery_mode") not in DELIVERY_MODES:
            errors.append(f"delivery_mode 必须是：{', '.join(sorted(DELIVERY_MODES))}")
        if fields.get("evidence_mode") not in EVIDENCE_MODES:
            errors.append(f"evidence_mode 必须是：{', '.join(sorted(EVIDENCE_MODES))}")
        if profile == "QUICK" and fields.get("evidence_mode") not in {"", "conversation"}:
            errors.append("QUICK 卡片必须使用 evidence_mode=conversation；外部证据请改用 VERIFIED")
    for key in ("handoff_id", "target_models"):
        if key in fields and not fields[key].strip():
            errors.append(f"frontmatter 字段不能为空：{key}")

    status = fields.get("status", "")
    if status not in ALLOWED_STATUSES:
        errors.append(f"status 必须是：{', '.join(sorted(ALLOWED_STATUSES))}")
    if strict and status == "DRAFT":
        errors.append("严格校验不接受 DRAFT")
    coverage = fields.get("history_coverage", "")
    if coverage not in HISTORY_COVERAGE:
        errors.append(f"history_coverage 必须是：{', '.join(sorted(HISTORY_COVERAGE))}")
    if strict and coverage == "UNKNOWN":
        errors.append("严格校验不接受 UNKNOWN 历史覆盖状态")
    if status == "HANDOFF_READY" and coverage in {"UNKNOWN", "UNAVAILABLE"}:
        errors.append("HANDOFF_READY 卡片的历史覆盖不能是 UNKNOWN 或 UNAVAILABLE")
    if coverage == "UNAVAILABLE" and status != "BLOCKED":
        errors.append("history_coverage=UNAVAILABLE 时 status 必须为 BLOCKED")
    if coverage == "PARTIAL":
        warnings.append("历史覆盖为 PARTIAL；接手前必须评估上下文缺口")

    for key in ("created_at", "updated_at"):
        if fields.get(key) and not parse_iso8601(fields[key]):
            errors.append(f"{key} 必须是带时区的 ISO 8601")
    if all(parse_iso8601(fields.get(key, "")) for key in ("created_at", "updated_at")):
        created_at = datetime.fromisoformat(fields["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(fields["updated_at"].replace("Z", "+00:00"))
        if updated_at < created_at:
            errors.append("updated_at 不能早于 created_at")

    project_root = Path(fields["project_root"]) if fields.get("project_root") else None
    delivery = fields.get("delivery_mode", "repo" if legacy else "")
    if not legacy and delivery == "repo" and project_root is None:
        errors.append("delivery_mode=repo 时必须填写 project_root")
    if not legacy and delivery in {"file", "repo"} and not fields.get("card_path"):
        errors.append(f"delivery_mode={delivery} 时必须填写 card_path")
    if check_paths and project_root is not None:
        if not project_root.is_absolute():
            errors.append(f"project_root 不是绝对路径：{project_root}")
        elif not project_root.is_dir():
            errors.append(f"project_root 目录不存在：{project_root}")

    schema = SCHEMAS.get((language, profile)) if not legacy else {
        "headings": V12_HEADINGS, "bullets": V12_BULLETS, "action": "下一动作",
        "prompt": "新会话首条提示词", "later": None,
        "evidence_heading": "## 2. 已核验证据与现状", "complete": {"无，工作已完成", "无；工作已完成", "不适用，工作已完成"},
    }
    if schema is None:
        schema = {"headings": [], "bullets": [], "action": "", "prompt": "", "later": None, "evidence_heading": None, "complete": set()}
    for heading in schema["headings"]:
        count = text.count(heading)
        if count != 1:
            errors.append(f"必填标题必须恰好出现一次：{heading}（实际 {count}）")
    unresolved = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}|待填写-必填|TBD-REQUIRED", text)))
    if unresolved:
        errors.append("存在未解决模板标记：" + "、".join(unresolved))
    for label in schema["bullets"]:
        values = bullet_values(text, label)
        if len(values) != 1:
            errors.append(f"必填字段必须恰好出现一次：{label}（实际 {len(values)}）")
        elif not values[0]:
            errors.append(f"必填字段为空：{label}")

    if profile == "QUICK" and schema.get("gap"):
        gap_values = bullet_values(text, schema["gap"])
        if len(gap_values) == 1:
            blocking_marker = r"阻塞|不影响下一动作" if language == "zh-CN" else r"\bblocks?\b|does not affect the (?:one )?next action"
            if re.search(blocking_marker, gap_values[0], re.I) is None:
                errors.append("QUICK 卡片必须明确未决缺口是否阻塞唯一下一动作")

    if profile == "VERIFIED":
        first_section = section_text(text, schema["headings"][0]) if schema["headings"] else ""
        if not re.search(r"(?m)^\s*-\s+\[[ xX]\]\s+\S+", first_section):
            errors.append("VERIFIED 卡片的验收标准至少需要一个 Markdown 复选项")

    prompts = bullet_values(text, schema["prompt"]) if schema["prompt"] else []
    if len(prompts) == 1 and len(prompts[0]) < 20:
        errors.append("新会话首条提示词过短，必须写明读取和接手要求")
    actions = bullet_values(text, schema["action"]) if schema["action"] else []
    if status == "COMPLETE":
        if len(actions) > 1:
            errors.append("COMPLETE 卡片最多只能有一个下一动作字段")
        elif len(actions) == 1 and actions[0] not in schema["complete"]:
            warnings.append("COMPLETE 卡片仍写有动作，请确认工作确已完成")
    elif len(actions) != 1 or not actions[0]:
        errors.append(f"非 COMPLETE 卡片必须恰有一个非空下一动作（实际 {len(actions)}）")

    later_label = schema.get("later")
    if later_label:
        later_values = bullet_values(text, later_label)
        if len(later_values) == 1:
            value = later_values[0].strip()
            candidates = [] if re.fullmatch(r"(?:None|无)[。. ]*", value, re.I) else [item.strip() for item in re.split(r"[；;]", value) if item.strip()]
            if len(candidates) > 3:
                errors.append("后续候选最多 3 项，且它们不构成执行授权")

    rows = evidence_rows(text, schema.get("evidence_heading"))
    if profile == "VERIFIED" and not rows:
        errors.append("VERIFIED 卡片的证据索引至少需要一条数据")
    evidence_ids: set[str] = set()
    verified_count = 0
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
            verified_count += 1
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

    evidence_mode = fields.get("evidence_mode", "external" if legacy else "")
    if status == "HANDOFF_READY" and profile == "VERIFIED" and evidence_mode in {"external", "mixed"} and verified_count == 0:
        errors.append("外部证据型 HANDOFF_READY/VERIFIED 卡片至少需要一条 VERIFIED 证据")
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
    if not check_paths and profile == "VERIFIED" and evidence_mode in {"external", "mixed"}:
        warnings.append("未检查 file: 和 dir: 证据路径")
    if status in {"BLOCKED", "WAITING"}:
        warnings.append(f"卡片状态为 {status}，执行前应先处理或检查该状态")
    if len(rows) > 6:
        warnings.append("证据超过 6 条；请只保留会改变接手决定的高影响项")
    body = text.split("\n---\n", 1)[1] if "\n---\n" in text else text
    body_chars = len(body)
    if profile == "QUICK" and body_chars > 1600:
        warnings.append("QUICK 卡片正文超过 1600 字符；中文目标约为 600–1200 字符")
    elif profile == "VERIFIED" and len(text) > 8000:
        warnings.append("VERIFIED 卡片超过 8000 字符；建议外置低频细节")
    elif profile == "VERIFIED" and len(text) > 5000:
        warnings.append("VERIFIED 卡片超过 5000 字符；普通任务应压缩到约 1500–3500 字符")

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
                        warnings.append("交接卡已达到源历史的 85% 或更长；请删除复述并外置低频细节")

    return {
        "ok": not errors, "protocol": protocol or None, "profile": profile or None,
        "delivery_mode": delivery or None, "evidence_mode": evidence_mode or None,
        "language": language or None, "status": status or None,
        "history_coverage": coverage or None, "evidence_rows": len(rows),
        "card_chars": len(text), "body_chars": body_chars, "source_chars": source_chars,
        "compression_ratio": compression_ratio, "path_checks": check_paths,
        "errors": errors, "warnings": warnings,
    }


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="校验 v1.2/v1.3 会话交接卡。")
    parser.add_argument("card", type=Path)
    parser.add_argument("--strict", action="store_true", help="拒绝 DRAFT/UNKNOWN。")
    parser.add_argument("--check-paths", action="store_true", help="检查已声明的项目和证据路径。")
    parser.add_argument("--source-history", type=Path, help="可选源历史，用于报告压缩比。")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    source = args.source_history.expanduser().resolve() if args.source_history else None
    result = validate(args.card.expanduser().resolve(), args.strict, args.check_paths, source)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("通过" if result["ok"] else "失败")
        print(f"协议={result.get('protocol')} 模式={result.get('profile')} 状态={result.get('status')} 历史覆盖={result.get('history_coverage')} 证据行={result.get('evidence_rows', 0)} 字符数={result.get('card_chars', 0)}")
        for error in result["errors"]:
            print(f"错误：{error}")
        for warning in result["warnings"]:
            print(f"警告：{warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
