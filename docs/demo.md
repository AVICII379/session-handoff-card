# 长会话交接演示

这个演示故意构造了一段“容易失忆”的会话：早期要求英文、后来改为中文；
早期允许自动安装依赖、后来明确禁止；中间还有一条已失败且不应重试的路线。

演示的目标不是展示一段漂亮摘要，而是证明：

1. 全部已提供历史都被连续读取；
2. 新要求正确覆盖旧要求，同时保留覆盖关系；
3. 失败路线、权限边界和证据位置没有丢失；
4. 新会话只获得一个可执行下一动作；
5. 卡片可以被机器严格校验。

## 运行

Windows PowerShell：

```powershell
$env:PYTHONUTF8 = "1"
python .\examples\run_demo.py --output-dir .\.demo-output
```

macOS 或 Linux：

```bash
PYTHONUTF8=1 python examples/run_demo.py --output-dir .demo-output
```

输出目录：

```text
.demo-output/
├─ history/
│  ├─ chunk-0001.md
│  ├─ chunk-0002.md
│  ├─ ...
│  ├─ chunk-N.md
│  └─ history-index.tsv
└─ handoff-card.md
```

分块数量会由样例字符数和分块参数决定；脚本不依赖固定的块数来判断成功。

## 检查关键结果

打开 `.demo-output/handoff-card.md`，至少应看到：

- `status: "HANDOFF_READY"`；
- `history_coverage: "FULL"`；
- 当前有效要求是“中文优先”；
- 英文优先和自动安装依赖均被标记为已覆盖；
- 失败的联网摘要路线被记录为不应盲目重试；
- 唯一下一动作是让新会话先复核两条高影响证据，而不是直接扩大工作范围。

脚本随后调用：

```powershell
python .\plugins\session-handoff-card\skills\session-handoff-card\scripts\validate_handoff.py `
  .\.demo-output\handoff-card.md --strict --check-paths `
  --source-history .\examples\long-session\conversation.md --json
```

如果任一证据路径不存在、模板标记未替换、必填章节缺失、出现多个下一动作，
或 `HANDOFF_READY` 卡片没有 `VERIFIED` 证据，演示会返回非零退出码。

## 无输出目录模式

只想做一次自检、不保留文件时：

```powershell
python .\examples\run_demo.py
```

脚本会在临时目录中运行同样的流程，打印 JSON 结果后自动清理。

## 模拟新模型接手

先只把生成的 `handoff-card.md` 和卡片列出的最高影响证据交给一个没有旧会话
记录的新模型，然后发送：

```text
请完整读取交接卡，并复核其中最高影响、会变化的证据。不要立即继续原任务。
先用中文报告当前目标、覆盖状态、被废弃要求、证据状态、唯一下一动作和停止
条件。无法访问的来源必须标成 UNVERIFIED 或 BLOCKED。只有卡片冲突、覆盖不全、
关键证据缺失或我要求审计时，才索取 history-index.tsv 和原始历史分块。
```

一个合格的接收方应先报告接手审计结果，再执行唯一下一动作；它不应默认重读
全部旧历史，也不应恢复早期已经被覆盖的英文要求，更不应声称无法访问的本机
文件已经验证。
