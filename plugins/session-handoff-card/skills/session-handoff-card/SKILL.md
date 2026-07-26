---
name: session-handoff-card
description: 创建、更新、校验并接收中文优先、跨大模型可读的会话交接卡，让没有旧聊天记忆的新会话恢复目标、失效要求、边界、证据和唯一下一步。用户说“帮我做续聊卡”“换新聊天继续”“保存进度”“接着上次”“让另一个 AI 接手”“上下文快满了”“把聊天带到新窗口”，或要求交接、压缩上下文、切换模型、从聊天导出恢复工作、审计既有交接卡时使用。适用于编程、科研、写作、浏览器和日常规划；支持轻量纯文本与可核验项目交接。
---

# 通用会话交接卡

把当前工作的“控制权”安全带到下一次会话：保留会改变接手决定的信息，删除复述，
不把未知写成事实，不把候选事项写成授权。

面向人的内容默认中文；用户明确使用其他语言时跟随用户，内置英文模板。状态码、命令
和路径保持原样。

## 先选交接档位

默认自动选择，用户可明确指定。

- `QUICK`：纯聊天、写作、计划、问答或轻量任务；主要证据就是当前会话；中文正文目标
  600–1200 字符，英文可适当放宽；可直接贴到新聊天，不要求项目目录、证据表或 Shell。
- `VERIFIED`：代码、科研、浏览器自动化、外部任务或任何依赖文件、日志、Git、测试、
  权限、失败路线的工作；目标 1500–3500 字符；保留 3–6 条高影响证据并严格校验。

有以下任一情况就选 `VERIFIED`：错误执行会造成返工；状态可能已变化；存在不可重试路线；
存在授权/发布/删除边界；接手方必须访问外部产物才能继续。其余优先 `QUICK`。

## 写出交接卡

1. 读取全部当前可见历史。若用户提供了结构化导出，先运行：

   ```text
   python scripts/normalize_history.py --input <导出文件> --output <normalized.md> --platform auto
   ```

   只有单次无法读完或完整性不确定时，才继续分块并核验：

   ```text
   python scripts/chunk_history.py --input <normalized.md> --output-dir <分块目录>
   python scripts/verify_history.py --source <normalized.md> --index <分块目录/history-index.tsv>
   ```

   必须按顺序处理全部已提供历史。无法取得完整历史时标成 `PARTIAL` 或
   `UNAVAILABLE`，不得用抽样冒充 `FULL`。
2. 合并最新有效要求，明确记录：当前目标、已完成、被覆盖/禁止事项、失败且不应重试的
   路线、权限边界、未决和上下文缺口。每个缺口必须写明是否阻塞唯一下一动作。聊天只证明“对话中说过什么”；项目状态必须对照
   实际证据。
3. 只保留一个可立即执行的“下一动作”。可另列 1–3 个“后续候选（非授权）”，但接手方
   不得把它们视为用户授权。
4. 选择模板：
   - 中文轻量：`assets/quick-handoff-card-template.md`
   - 中文核验：`assets/handoff-card-template.md`
   - 英文轻量：`assets/quick-handoff-card-template.en.md`
   - 英文核验：`assets/handoff-card-template.en.md`
5. 纯文本交接使用 `delivery_mode: text`；`project_root`、`card_path`、`source_session`
   可以为空，直接在聊天中完整输出卡片。文件交接用 `file`，仓库内长期维护用 `repo`。
6. `QUICK` 通常使用 `evidence_mode: conversation`，不伪造 `VERIFIED`；
   `VERIFIED` 使用 `external` 或 `mixed`，`HANDOFF_READY` 前至少有一条当前核验的
   `VERIFIED` 外部证据。
7. 写入或对外分享前先做隐私预览：

   ```text
   python scripts/redact_handoff.py <交接卡>
   python scripts/redact_handoff.py <交接卡> --output <脱敏副本> --project-root <项目根目录>
   ```

   预览只报告类别与数量，不显示原值。自动脱敏是降低风险，不代替人工复核。不要写入
   密钥、令牌、私钥、直接个人信息或无必要的本机绝对路径。
8. 创建草稿与校验：

   ```text
   python scripts/new_handoff.py --output <交接卡> --profile quick --delivery text
   python scripts/new_handoff.py --output <交接卡> --profile verified --delivery repo --project-root <根目录>
   python scripts/validate_handoff.py <交接卡> --strict --json
   python scripts/validate_handoff.py <交接卡> --strict --check-paths --source-history <历史>
   ```

9. 返回完整卡片或路径，以及 `profile`、状态、历史覆盖、校验结果和最小附件。不要只说
   “已经交接”而不提供可带走的内容。

## 接收交接卡

1. 先完整读取卡片；默认不重读全部旧历史。
2. 检查协议、模式、历史覆盖、失效要求、唯一下一动作、停止条件和隐私占位符。
3. `QUICK/conversation` 的事实只能标为对话内已知；不能据此声称本机文件、外部网页或
   任务状态已核验。`VERIFIED` 重新检查会变化的 Git、文件、测试、进程、外部任务和界面。
4. 分类为：
   - `VERIFIED`：关键上下文和当前证据一致；
   - `STALE`：现实状态已变化，先更新卡；
   - `BLOCKED`：缺历史、证据、访问、授权或必要输入。
5. 先向用户复述目标、禁止/失效事项、缺口、唯一下一动作和停止条件，再执行唯一下一动作。
   除非卡片明确标为 `BLOCKED`、缺口明确阻塞或当前证据已冲突，不得因为“还可以问得更细”
   而自行替换唯一下一动作。后续候选不构成执行授权。
6. 仅在卡片冲突、覆盖为 `PARTIAL/UNAVAILABLE`、高影响证据缺失、用户要求审计，或卡片
   无法解释关键决定时，升级读取历史索引和原始分块。

## 更新交接卡

保留旧决定和失败记录，刷新 `updated_at`、状态、证据、阻塞与唯一下一动作。将失效项
标为 `SUPERSEDED`，重新做隐私预览和严格校验。不要同时维护两张“当前活动卡”。

## 不可违背

- 不记录思维链，只记录恢复工作所需的结论、依据、边界和决定。
- 不把结构校验通过当成事实核验通过。
- 不扩大用户授权，不静默解除阻塞或停止条件。
- 不因追求“兼容所有模型”而依赖某家平台专有语法；核心卡必须是普通 UTF-8 Markdown。
- v1.2 卡片可继续接收；新写出的卡片使用 v1.3。细节见
  `references/handoff-protocol.md`、`references/long-context-reconstruction.md` 和
  `references/model-compatibility.md`。
