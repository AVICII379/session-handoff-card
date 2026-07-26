# 长会话交接演示

演示历史故意包含“容易失忆”的覆盖关系：早期英文优先后来改为中文优先；早期允许自动安装
依赖，后来明确禁止；中间还有失败且不应重试的路线。目标是验证新会话不会复活旧要求，
并只获得一个下一动作。

## 运行

```powershell
$env:PYTHONUTF8 = "1"
python .\examples\run_demo.py --output-dir .\.demo-output
```

脚本会：连续分块 `conversation.md`、逐字符核验覆盖、生成 v1.3 `VERIFIED` 卡、检查实际
证据路径并输出 JSON。输出目录包含 `history/`、`history-index.tsv` 和 `handoff-card.md`。

只想自检、不保留文件时：

```powershell
python .\examples\run_demo.py
```

合格结果必须满足：`HANDOFF_READY / FULL`、`coverage_exact: true`、校验器零错误零警告、
3–6 条高影响证据、卡片短于源历史，且唯一下一动作没有恢复英文优先、自动安装依赖或失败
联网路线。

## 模拟失忆接手

只把生成卡和卡内点名的最高影响证据交给没有旧聊天记录的新模型，发送：

```text
请完整读取交接卡，先报告当前目标、失效要求、证据状态、唯一下一动作和停止条件。无法访问的来源标成 UNVERIFIED 或 BLOCKED；不要恢复旧要求，不要执行后续候选。只有卡片冲突或关键证据缺失时，才索取历史索引和原始分块。
```

接收方应先报告审计结果，再执行唯一下一动作；不得声称无法访问的本机文件已经验证。
