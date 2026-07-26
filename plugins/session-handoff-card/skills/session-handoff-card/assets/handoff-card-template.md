---
handoff_protocol: "session-handoff-card/v1.3"
handoff_id: "{{HANDOFF_ID}}"
created_at: "{{CREATED_AT}}"
updated_at: "{{UPDATED_AT}}"
status: "DRAFT"
history_coverage: "UNKNOWN"
language: "zh-CN"
profile: "VERIFIED"
delivery_mode: "{{DELIVERY_MODE}}"
evidence_mode: "{{EVIDENCE_MODE}}"
project_root: '{{PROJECT_ROOT}}'
card_path: '{{CARD_PATH}}'
source_session: '{{SOURCE_SESSION}}'
target_models: "any"
---

# 会话交接卡（核验版）

## 1. 当前目标与边界

- 当前目标：待填写-必填
- 当前状态：待填写-必填
- 验收标准：
  - [ ] 待填写-必填
- 失效要求：待填写-必填；没有则写“无”。
- 用户边界与偏好：待填写-必填

## 2. 已核验证据与现状

| ID | 证明内容或用途 | 来源 | 核验方法或结果 | 状态 | 最后核验时间 |
| --- | --- | --- | --- | --- | --- |
| E1 | 待填写-必填 | file:待填写-必填 | 待填写-必填 | UNVERIFIED | {{UPDATED_AT}} |

- 已完成工作：待填写-必填
- 失败、阻塞与未决：待填写-必填；没有则写“无”。

## 3. 唯一下一步

- 下一动作：待填写-必填
- 预期输出：待填写-必填
- 验证方式：待填写-必填
- 停止条件：待填写-必填
- 后续候选（非授权）：无；如有，用分号列 1–3 项，不得当作已授权动作。

## 4. 接手说明

- 历史来源与覆盖：待填写-必填
- 上下文缺口与影响：待填写-必填；没有则写“无”。
- 最小接手附件：待填写-必填
- 路径映射或仓库定位：待填写-必填；纯文本交接可写“不适用”。
- 新会话首条提示词：请完整读取本交接卡，先报告当前目标、失效要求、证据状态、唯一下一动作和停止条件；不能访问的证据标为 UNVERIFIED 或 BLOCKED，不要擅自执行后续候选。
- 无法访问原环境时的降级方案：待填写-必填
