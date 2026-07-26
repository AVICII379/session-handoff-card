# 兼容性矩阵

“跨模型”指核心卡是普通 Markdown，能在没有插件的模型中阅读；不代表每个平台的私有导出
格式都已经实机覆盖。

| 使用方式 | 当前状态 | 说明 |
| --- | --- | --- |
| Codex 安装 Skill | 已在本仓库自动测试 | 生成器、v1.2/v1.3 校验器、演示和发布包进入 CI |
| 任意模型粘贴 Markdown | 协议级兼容 | 使用 `prompts/` 的通用写出/接收提示词；效果取决于模型遵循指令能力 |
| ChatGPT `mapping` JSON 导出 | 有合成夹具测试 | 支持选择会话并按父链恢复消息顺序 |
| Claude `chat_messages` JSON | 有合成夹具测试 | 识别 human/assistant 消息 |
| Codex 或常见 JSONL | 有合成夹具测试 | 识别逐行 role/content 记录 |
| Gemini/DeepSeek/通义千问等 role/content JSON | 通用适配 | 选择 `generic`；平台改版或私有结构需先转换 |
| 纯文本/Markdown 历史 | 支持 | 包装为可分块的标准化历史，不推断消息角色 |
| 英文 QUICK/VERIFIED 卡 | 本地结构测试 | 字段和校验器支持 `language: en` |

未列为“实机验证”的平台，不应在 README 或发布说明中宣传为已通过官方导入测试。
