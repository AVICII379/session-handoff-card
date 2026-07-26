# session-handoff-card/v1.3 协议

## 设计目标

核心协议只依赖 UTF-8 Markdown、简单 YAML 标量和固定字段。平台适配器可以帮助导入，
但任何模型即使不安装 Skill，也应能读懂卡片并按“唯一下一动作”继续。

## Frontmatter

v1.3 必填字段：

- `handoff_protocol: session-handoff-card/v1.3`
- `handoff_id`、`created_at`、`updated_at`
- `status`: `DRAFT | HANDOFF_READY | BLOCKED | WAITING | COMPLETE`
- `history_coverage`: `UNKNOWN | FULL | PARTIAL | UNAVAILABLE`
- `language`: `zh-CN | en`
- `profile`: `QUICK | VERIFIED`
- `delivery_mode`: `text | file | repo`
- `evidence_mode`: `conversation | external | mixed`
- `target_models`

可选字段：`project_root`、`card_path`、`source_session`。`text` 可全部留空；`file`
需要 `card_path`；`repo` 需要 `project_root` 和 `card_path`。
自定义 frontmatter 字段必须使用 `x_` 前缀，避免不同模型发明相似但不兼容的核心字段。

## 两种档位

`QUICK` 不要求证据表或复选框，允许 `HANDOFF_READY + conversation`。这只表示已完整
整合所见对话，不表示外部状态已验证。

`VERIFIED` 要求验收复选框与六列表格：ID、证明内容、来源、核验方法/结果、状态、最后
核验时间。`HANDOFF_READY + external/mixed` 至少一条 `VERIFIED`。来源前缀为
`file:`、`dir:`、`command:`、`git:`、`url:`、`artifact:`、`history:` 或
`user-statement:`。证据状态为 `VERIFIED`、`USER-PROVIDED`、`UNVERIFIED`、
`STALE` 或 `BLOCKED`。

## 覆盖语义

- `FULL`：全部已提供且当前可访问的历史已按顺序处理；不声称平台未导出的更早消息存在。
- `PARTIAL`：已知有缺块、截断或无法读取的附件；必须写明缺口与影响。
- `UNAVAILABLE`：没有足够历史重建工作；状态必须为 `BLOCKED`。
- `UNKNOWN`：草稿阶段尚未审计；严格校验不接受。

## 下一动作和后续候选

非 `COMPLETE` 卡片必须恰有一个“下一动作”。QUICK 卡的每个缺口必须写明是否阻塞这个
动作；未明确阻塞的缺口不能成为接收方擅自改写动作的理由。“后续候选（非授权）”最多 3 项，只用于
防止远期想法丢失，不能触发执行、发布、删除、付款或权限扩大。

## 状态转换

`DRAFT` 经覆盖检查、隐私预览和相应档位校验后才能变为 `HANDOFF_READY`。
证据变化用 `STALE` 描述证据，不伪装为仍已核验；缺权限或必要输入时卡片使用
`BLOCKED`。工作真正完成且没有下一动作时才使用 `COMPLETE`。

## 兼容性

校验器继续接受 v1.2 中文核验卡，按旧规则要求路径与至少一条 `VERIFIED` 证据。更新或
重写旧卡时应迁移到 v1.3；不要只改协议号而遗漏新 frontmatter。
