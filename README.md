# AI 续聊交接卡

把长聊天安全带到下一次：不重讲、不返工、不越权。

`session-handoff-card` 是中文优先、跨模型可读的会话交接 Skill。它把当前工作整理成普通
UTF-8 Markdown，新会话即使没有旧聊天记忆，也能恢复最新目标、已经完成的事、被覆盖或
禁止的要求、关键证据、唯一下一动作和停止条件。

当前版本：`0.4.0`；当前协议：`session-handoff-card/v1.3`；旧 v1.2 卡仍可读取。

## 30 秒开始

在当前聊天直接说：

```text
帮我做一张轻量续聊卡，我要换到新聊天继续。
```

把模型输出的完整卡片复制到新聊天，再说：

```text
请先完整读取这张卡，复述目标、不要做的事、唯一下一步和停止条件，然后只执行唯一下一步。
```

这条路径不需要 Python、项目目录、插件或证据表，适合大多数普通对话。也可以直接复制
[中文轻量写出提示词](prompts/quick-write.zh-CN.txt)和
[中文接收提示词](prompts/receive.zh-CN.txt)到任意模型。

## 自动选择两种档位

| 档位 | 适合 | 典型长度 | 外部证据 |
| --- | --- | --- | --- |
| `QUICK` 轻量续聊卡 | 写作、计划、问答、纯聊天 | 中文正文约 600–1200 字符，英文可放宽 | 不要求；只诚实记录对话内已知内容 |
| `VERIFIED` 核验交接卡 | 代码、科研、浏览器、外部任务、权限敏感工作 | 1500–3500 字符 | 3–6 条会改变接手决定的高影响证据 |

存在文件、Git、测试、网页实时状态、失败路线、发布/删除权限或高返工风险时自动使用
`VERIFIED`；其他情况优先 `QUICK`。用户可明确指定。

## 安装到 Codex

```powershell
codex plugin marketplace add AVICII379/session-handoff-card
codex plugin add session-handoff-card@session-handoff-card
```

安装后可以说：

```text
使用 $session-handoff-card 帮我做续聊卡。
```

Skill 的核心说明在 [SKILL.md](plugins/session-handoff-card/skills/session-handoff-card/SKILL.md)。
没有安装条件时，使用 `prompts/` 中的通用提示词仍可读写同一协议。

## 高级：生成和校验文件

Windows PowerShell：

```powershell
$env:PYTHONUTF8 = "1"
$skill = ".\plugins\session-handoff-card\skills\session-handoff-card"

# 纯文本轻量草稿；project_root 和 card_path 可以为空
python "$skill\scripts\new_handoff.py" --output .\quick-handoff.md --profile quick --delivery text

# 仓库核验版草稿
python "$skill\scripts\new_handoff.py" --output .\handoff.md --profile verified --delivery repo --project-root .

# 填完模板后校验
python "$skill\scripts\validate_handoff.py" .\quick-handoff.md --strict --json
python "$skill\scripts\validate_handoff.py" .\handoff.md --strict --check-paths --json
```

生成器拒绝覆盖已有卡。`HANDOFF_READY/VERIFIED` 的外部证据型卡必须至少有一条当前
`VERIFIED` 证据；`QUICK/conversation` 不伪造外部核验。

## 很长的历史导出

先把常见导出统一成按序 Markdown，再按需分块：

```powershell
python "$skill\scripts\normalize_history.py" --input .\export.json --output .\normalized.md --platform auto
python "$skill\scripts\chunk_history.py" --input .\normalized.md --output-dir .\history
python "$skill\scripts\verify_history.py" --source .\normalized.md --index .\history\history-index.tsv
```

当前归一化器覆盖 ChatGPT `mapping`、Claude `chat_messages`、常见 `role/content` JSON、
JSONL 和纯文本。各平台私有格式可能变化，准确边界见[兼容性矩阵](docs/compatibility-matrix.md)。
无法证明完整覆盖时必须写 `PARTIAL`，不能用抽样冒充 `FULL`。归一化输出保留原消息，
应留在本地并按原历史同等级保护，不能直接提交仓库或作为默认接手附件。

## 分享前隐私预览

```powershell
# 只看风险类别和数量，不显示原始值，也不改文件
python "$skill\scripts\redact_handoff.py" .\handoff.md

# 创建新脱敏副本，并把项目根路径改成 <PROJECT_ROOT>
python "$skill\scripts\redact_handoff.py" .\handoff.md --output .\handoff.public.md --project-root E:\example\project
```

脚本处理常见令牌、私钥、邮箱、手机号、来源会话标识、URL 凭据和用户目录路径，并拒绝覆盖输出。规则匹配不是绝对保证，
公开前仍需人工检查。仓库本身和发布 ZIP 另有独立隐私门。

## 接手原则

- 先读完整卡片，默认不重读全部旧历史。
- 不让早期已覆盖要求复活。
- `QUICK` 中“对话说过”不等于外部状态已验证。
- 只执行唯一下一动作；最多 3 个“后续候选”不构成授权。
- 缺关键历史、证据、访问或权限时标为 `BLOCKED` 并停止。

## 演示和大众场景测试

- [长会话可复现演示](docs/demo.md)：完整历史分块、覆盖校验、核验版卡和接手提示词。
- [五场景基准](docs/benchmarks.md)：编程、科研、写作、浏览器和日常规划。
- [可用性评估](docs/usability-evaluation.md)：早期版本为何过重，以及 v1.2 的压缩结果。

运行全部本地检查：

```powershell
$env:PYTHONUTF8 = "1"
python -m unittest discover -s tests -v
python .\tools\run_benchmark_checks.py
python .\examples\run_demo.py
python .\tools\check_publication_privacy.py
python .\tools\package_release.py --output-dir .\dist
python .\tools\check_publication_privacy.py --archive-dir .\dist
```

## 仓库结构

```text
plugins/session-handoff-card/   可安装插件与 Skill
prompts/                        无插件也能使用的中英文提示词
examples/                       长会话演示
benchmarks/                     五领域源会话与隔离评分标准
docs/                           协议体验、兼容和发布说明
tests/                          回归、隐私、打包与格式适配测试
tools/                          发布包、隐私门和基准检查
```

## 发布与许可证边界

公开仓库坐标是 [`AVICII379/session-handoff-card`](https://github.com/AVICII379/session-handoff-card)。
发布步骤见[发布说明](docs/publishing.md)，安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

当前尚未由维护者选择开源许可证，因此仓库没有 `LICENSE`，清单也不伪造 `license` 字段。
公开可见不等于已经授予复制、修改或再分发许可；确定许可证后应单独提交许可证文件和 SPDX
标识。
