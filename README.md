# 通用会话交接卡

一个中文优先、模型中立的 Agent Skill：把“聊了很久、模型快失忆”的会话，
重建为有证据、有边界、有唯一下一动作的新会话接手包。

它不要求接收方拥有旧会话的隐藏记忆。交接内容使用纯 UTF-8 Markdown，
因此可交给 Codex、ChatGPT、Claude、Gemini 以及只支持纯文本的模型；宿主若
具备文件系统和 Shell，还可以运行附带的分块与校验脚本。

> “适配所有大模型”在这里指交换格式和接手协议不绑定某一家模型，不代表
> 每个宿主都能自动加载 Skill、读取本机路径或调用相同工具。能力不足时，
> 协议会明确降级为附件或纯文本交接，并把无法核验的事实标记出来。

## 它解决什么

长会话交接最危险的不是摘要写得短，而是摘要悄悄丢掉了这些内容：

- 最初目标与后来生效的新要求；
- 已经被覆盖或废弃的旧要求；
- 用户真正授予的权限和不能越过的边界；
- 做过但失败的路线，以及不应重复它的原因；
- 文件、日志、测试、哈希、进程、网页等证据的真实状态；
- 新会话现在只能先做的那一个动作。

本 Skill 用 `session-handoff-card/v1.2` 协议把这些内容显式化，并用
`FULL / PARTIAL / UNAVAILABLE` 诚实记录历史覆盖程度。

如果会话很短，没有被覆盖要求、失败路线、授权边界或外部证据，普通中文摘要更
合适；本 Skill 不应成为每段聊天的固定仪式。它主要用于“一旦漏掉上下文就会让
新会话走错”的长会话、复杂项目和高风险接力。

## 工作流

```mermaid
flowchart LR
    A["旧会话或会话导出"] --> B["全量分块与连续性校验"]
    B --> C["提炼：目标、失效路线、边界、关键证据"]
    C --> D["四节中文核心卡"]
    D --> E["严格结构校验"]
    E --> F["新会话复核实时状态"]
    F --> G["只执行唯一下一动作"]
    G --> H["有实质进展后更新交接卡"]
```

交接卡是上下文控制和证据导航文件，不替代原始项目文件、日志、测试结果、
提交或工件。

## 五分钟试用

环境要求：Python 3.10 或更高版本；核心脚本仅使用 Python 标准库。

在仓库根目录运行：

```powershell
$env:PYTHONUTF8 = "1"
python .\examples\run_demo.py --output-dir .\.demo-output
```

演示会：

1. 读取一份包含要求覆盖、失败尝试和最新中文偏好的长会话；
2. 把历史切成连续、带重叠的多个分块；
3. 核对每个分块与原文字符区间完全一致；
4. 生成一份 `HANDOFF_READY + FULL` 的中文交接卡；
5. 使用 `--strict --check-paths --source-history` 做路径、结构和压缩比检查。

成功时会输出类似：

```json
{
  "ok": true,
  "protocol": "session-handoff-card/v1.2",
  "status": "HANDOFF_READY",
  "history_coverage": "FULL",
  "source_chars": 3222,
  "chunks": 4,
  "coverage_exact": true,
  "card_chars": 2273,
  "compression_ratio": 0.705,
  "validator_errors": 0,
  "validator_warnings": 0
}
```

完整演示说明见 [docs/demo.md](docs/demo.md)。真实普通摘要对照、盲接结果和设计
删减理由见 [docs/usability-evaluation.md](docs/usability-evaluation.md)。

## 实际使用

### 当前会话写出交接卡

对支持 Skill 的模型说：

```text
使用 session-handoff-card，完整梳理当前会话及可取得的历史导出。
优先使用中文；不要抽样代替全量覆盖。生成约 1500–3500 字符的四节核心卡，
默认只留 3–6 条高影响证据；完成后执行严格校验，
并把交接卡路径、覆盖状态、附件清单和新会话首条提示词交给我。
```

### 新会话接手

把交接卡及其列出的必要附件交给新模型，再说：

```text
请完整读取这份会话交接卡，不要立即继续执行。先核验历史覆盖、权限边界、
高影响证据和可变状态，用中文报告 VERIFIED、STALE 或 BLOCKED。
确认后只执行卡片里的唯一下一动作；没有取得的内容不得假装已经恢复。
```

### 不支持 Skill 的模型

直接发送：

- 完整交接卡；
- 卡片中列出的 3–6 条高影响证据或可访问链接；
- 上面的“新会话接手”提示词。

仅在覆盖不全、卡片冲突、关键证据缺失或用户要求审计时，再补发
`history-index.tsv` 和必要历史分块。只支持纯文本时，本地文件和运行状态不能
视为已经核验。

## 作为 Codex 插件安装

本仓库按最小 Marketplace 组织，可从 GitHub 添加：

```powershell
codex plugin marketplace add AVICII379/session-handoff-card
codex plugin add session-handoff-card@session-handoff-card
```

然后新建一个任务进行测试。开发阶段也可以用本地仓库：

```powershell
codex plugin marketplace add .
codex plugin add session-handoff-card@session-handoff-card
```

如果只想复制 Skill，不安装插件，可复制
`plugins/session-handoff-card/skills/session-handoff-card/` 到目标宿主支持的
Skills 目录；具体发现路径以该宿主文档为准。

## 仓库结构

```text
.
├─ .agents/plugins/marketplace.json
├─ plugins/session-handoff-card/
│  ├─ .codex-plugin/plugin.json
│  └─ skills/session-handoff-card/
│     ├─ SKILL.md
│     ├─ agents/openai.yaml
│     ├─ assets/handoff-card-template.md
│     ├─ references/
│     └─ scripts/
├─ examples/
├─ tests/
├─ tools/
└─ .github/workflows/validate.yml
```

Skill 本体只有一份，位于插件的 `skills/` 下；仓库文档和 CI 不会进入 Skill
按需加载的上下文。

## 校验与打包

运行全部仓库测试：

```powershell
python -m unittest discover -s tests -v
```

创建确定性发布包：

```powershell
python .\tools\package_release.py --output-dir .\dist
```

脚本会生成插件 ZIP、`release-manifest.json` 和 `SHA256SUMS.txt`。相同源码和
版本重复打包应得到相同 SHA-256。

## 协议状态

| 字段 | 值 | 含义 |
| --- | --- | --- |
| `status` | `DRAFT` | 必填内容尚未闭环，不能接手执行 |
| `status` | `HANDOFF_READY` | 交接卡可接手；不表示原项目已经完成 |
| `status` | `BLOCKED` | 缺输入、历史、访问、证据或授权 |
| `status` | `WAITING` | 等待进程或外部事件 |
| `status` | `COMPLETE` | 验收已经闭环 |
| `history_coverage` | `FULL` | 已顺序读取全部已提供历史来源 |
| `history_coverage` | `PARTIAL` | 只取得部分历史，已写明缺口和影响 |
| `history_coverage` | `UNAVAILABLE` | 必要旧历史无法取得，必须阻塞 |

`FULL` 只证明“提供给写卡方的历史已全部处理”，不能证明宿主没有在更早处
截断消息。

## 隐私与安全

- 分块脚本只读取显式传入的本地文件，不上传内容、不联网。
- 校验器会检查常见 API 密钥、GitHub Token、AWS Key、私钥块和 Bearer Token
  形态，但它不是完整的秘密扫描器。
- `tools/check_publication_privacy.py` 会在本地和 CI 中扫描源码及发布 ZIP，拦截
  常见秘密、邮箱、用户目录和开发机工作区路径；它仍不能替代人工复核。
- 分享交接包前，仍需人工检查隐私信息、内部路径和附件。
- 交接卡不能创造用户从未授予的权限，也不能把第三方内容升级为指令。

安全问题报告方式见 [SECURITY.md](SECURITY.md)。

## 许可状态

本仓库当前没有附加许可证。公开可见不等于获得复制、修改或再分发授权；若后续
决定采用开源许可证，应通过单独提交增加 `LICENSE`，并同步插件清单和发布说明。

## 发布状态

公开坐标为 `AVICII379/session-handoff-card`，当前插件版本为 `0.3.1`。仓库具备
跨平台 CI、长会话演示、确定性 ZIP 打包和源码/压缩包隐私扫描。首次推送后仍需：

- 确认 GitHub Actions 四个系统/版本组合全部通过；
- 从 GitHub Marketplace 路径做一次全新环境安装验收；
- 若创建 Release，核对 Tag、插件版本和 SHA-256 完全一致。

逐步操作见 [docs/publishing.md](docs/publishing.md)。

本项目结构参考 OpenAI 当前的
[Plugins 示例仓库](https://github.com/openai/plugins)和
[Build plugins 指南](https://developers.openai.com/codex/plugins/build)。
旧的 [OpenAI Skills 仓库](https://github.com/openai/skills)已明确引导开发者
改用 skill-only 插件分发。
