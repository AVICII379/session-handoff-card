---
handoff_protocol: "session-handoff-card/v1.3"
handoff_id: "{{HANDOFF_ID}}"
created_at: "{{CREATED_AT}}"
updated_at: "{{UPDATED_AT}}"
status: "DRAFT"
history_coverage: "UNKNOWN"
language: "zh-CN"
profile: "QUICK"
delivery_mode: "{{DELIVERY_MODE}}"
evidence_mode: "{{EVIDENCE_MODE}}"
project_root: '{{PROJECT_ROOT}}'
card_path: '{{CARD_PATH}}'
source_session: '{{SOURCE_SESSION}}'
target_models: "any"
---

# 会话续聊卡（轻量版）

## 1. 现在要做什么

- 当前目标：待填写-必填
- 当前状态：待填写-必填
- 不要做：待填写-必填；没有则写“无”。

## 2. 必须带走的上下文

- 已完成：待填写-必填
- 关键约束：待填写-必填
- 未决与缺口：待填写-必填；逐项写明“阻塞”或“不阻塞唯一下一动作”，没有则写“无，不阻塞唯一下一动作”。

## 3. 下一步

- 下一动作：待填写-必填
- 预期输出：待填写-必填
- 停止条件：待填写-必填
- 后续候选（非授权）：无；如有，用分号列 1–3 项。

## 4. 新会话怎么接

- 历史覆盖：待填写-必填
- 最小附件：仅本卡；如确有必要再补充。
- 新会话首条提示词：请先完整读取这张续聊卡，用中文复述当前目标、不要做的事、唯一下一动作和停止条件；缺失内容标为未知。除非卡片明确写为阻塞，否则不得改写唯一下一动作，也不要执行后续候选。
- 无法访问时：按唯一下一动作继续；只有卡片明确标为 BLOCKED 或缺口明确写为“阻塞”时，才停止并向用户询问。
