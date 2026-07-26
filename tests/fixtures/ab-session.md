# 离线文献目录工具：旧会话导出

## 消息 001｜用户

我想做一个 Windows 文献整理工具。最初想法是桌面 GUI：扫描下载目录，
调用 Crossref 补 DOI，然后自动按“年份-作者-标题.pdf”重命名。界面和输出先
用英文，结果写到 `output/index.csv`。缺包可以直接安装，pandas、requests
都可以用。

## 消息 002｜助手

我计划先完成目录扫描和元数据表，再接 GUI、Crossref 和自动重命名。第一步
会创建 `src/catalog.py`，输出 CSV；之后再设计撤销机制。

## 消息 003｜用户

先收紧一下：当前只允许读取 `tests/fixtures/mock-project/inbox/` 的示例文件名，
不要碰真实下载目录，也不要真的改名。你可以在这个 mock-project 里写代码和
测试，其他目录都不要动。

## 消息 004｜助手

收到。我会把当前阶段定义为 mock-project 内的 dry-run，扫描后只打印拟议
文件名，不执行移动或重命名。

## 消息 005｜工具

```text
Traceback (most recent call last):
  File "src/catalog.py", line 4, in <module>
    import pandas as pd
ModuleNotFoundError: No module named 'pandas'
```

## 消息 006｜助手

当前环境缺少 pandas。我准备安装 pandas 后继续生成 `output/index.csv`。

## 消息 007｜用户

不要安装。这个工具以后要放到一台干净的 Windows 机器上，核心流程只能用
Python 标准库。刚才“缺包直接安装”的要求作废，记住不要在新会话里又装回来。

## 消息 008｜助手

已移除 pandas 方案，改用 `csv`、`hashlib`、`pathlib` 和 `re`。目前可以从
文件名解析年份、第一作者和标题。

## 消息 009｜用户

输出也改掉：不用 CSV，统一写制表符分隔的
`artifacts/catalog-preview.tsv`，UTF-8，列为
`source_name / year / first_author / title / sha256 / proposed_name / status`。
面向人的提示全部中文，协议字段和路径可保留英文。

## 消息 010｜助手

输出目标已从 `output/index.csv` 改为
`artifacts/catalog-preview.tsv`。下一步准备调用 Crossref 补齐缺失 DOI。

## 消息 011｜工具

```text
GET https://api.crossref.org/works?query.title=...
ERROR ConnectTimeout: request timed out after 30 seconds
artifacts/catalog-preview.tsv was not modified
```

## 消息 012｜用户

Crossref 路线停止。这个项目现在必须完全离线，不要重试，不要调整代理，也不要
为了联网改安全设置。DOI 不再是当前验收项，缺 DOI 就留空。失败原因写进项目
记录，避免下个会话再走同一条路。

## 消息 013｜助手

明白。Crossref、requests 和联网 DOI 补齐均移出当前范围。现有实现只处理
文件名和本地字节。

## 消息 014｜用户

重复判断不要用文件名，因为不同文件名可能是同一篇。改成 SHA-256；但现在
mock inbox 里只是空的占位 PDF，测试阶段允许读取字节算哈希。相同哈希的第二
个及以后条目标成 `DUPLICATE`，不能进入后续改名候选。

## 消息 015｜助手

已把 SHA-256 作为重复键。`reports/test-report.txt` 记录了解析和重复判断的
测试结果。当前代码还没有处理“两个不同来源最后得到相同 proposed_name”的
命名冲突。

## 消息 016｜用户

命名冲突要和内容重复分开：内容相同是 `DUPLICATE`；内容不同但建议名相同是
`NAME_COLLISION`。遇到命名冲突只能预览，绝不能自动加 `(1)` 后继续，更不能
真的改文件。

## 消息 017｜助手

我会新增 `detect_name_collisions(rows)`，在生成预览后统一标记冲突。原先考虑
的“自动加序号”方案废弃。

## 消息 018｜用户

还有两个格式细节：

1. 标题只做首尾空白清理，不要擅自改成 Title Case；
2. 无法从文件名解析年份时写空字符串，状态用 `REVIEW`，不要猜年份。

## 消息 019｜助手

已记录。当前解析器会保留标题大小写；缺年份行标记 `REVIEW`。由于
`detect_name_collisions` 尚未实现，碰到不同内容同名时还会错误保持 `READY`。

## 消息 020｜用户

现在的验收门槛是：

- Python 3.10+，只用标准库；
- 完全离线；
- 只处理 mock inbox；
- 只生成 `artifacts/catalog-preview.tsv`，不重命名；
- SHA-256 内容重复为 `DUPLICATE`；
- 不同内容同建议名为 `NAME_COLLISION`；
- 缺年份为 `REVIEW`；
- 其他可进入候选的行才是 `READY`；
- 中文提示；
- 单元测试通过。

## 消息 021｜助手

当前已有 6 个测试通过：年份/作者/标题解析、大小写保留、缺年份 REVIEW、
SHA-256 生成和内容重复。缺少两个命名冲突测试，相关函数也没有实现。

## 消息 022｜用户

不要把“6 个测试通过”说成项目已经完成。它只证明已有分支没坏，当前验收仍被
命名冲突逻辑阻塞。测试报告和失败路线日志是证据，聊天里说通过不算实时证明。

## 消息 023｜助手

同意。当前状态应为未完成，阻塞点是 `detect_name_collisions(rows)` 和它的
两条测试：不同哈希同名要全部标成 `NAME_COLLISION`；同哈希重复仍优先保持
`DUPLICATE`。

## 消息 024｜用户

优先级明确一下：先标内容重复，再检测命名冲突；`DUPLICATE` 行不参与命名
冲突判定。否则同一 PDF 的副本会被同时标两个状态。

## 消息 025｜助手

顺序已确定：计算哈希与 DUPLICATE → 生成 proposed_name → 对非 DUPLICATE
行检测 NAME_COLLISION → 缺年份保持 REVIEW → 其余为 READY。

## 消息 026｜用户

项目文件现在在 `tests/fixtures/mock-project/`。不要假设它是 Git 仓库。
`reports/test-report.txt` 是已有测试快照，
`reports/failed-routes.log` 记录 pandas 和 Crossref 的失败，
`spec-current.md` 是当前规范。接手时先核对这些文件，不要只信聊天。

## 消息 027｜助手

已记录证据路径。接手方应重新运行测试并比较当前规范，不能把旧快照自动当成
当前状态。

## 消息 028｜用户

最终再收紧一次：现在只做交接，不准继续改代码。新会话的第一步也不是直接
实现，而是只读检查 `spec-current.md`、`src/catalog.py`、
`tests/test_catalog.py` 和两份报告，给出实现
`detect_name_collisions(rows)` 的精确修改计划。计划里要写两条新增测试，
然后停下来等我确认。

## 消息 029｜助手

收到。当前唯一下一动作是只读审计并提交修改计划；未经确认不得编辑代码、
运行会改变状态的命令、安装依赖、联网或处理真实下载目录。

## 消息 030｜用户

交接给新会话时优先中文。必须保留最初目标和所有覆盖关系，尤其不要复活 GUI、
CSV、pandas 安装、Crossref、自动加序号或真实重命名。接收方如果看到证据和
聊天冲突，以当前用户要求、`spec-current.md` 和重新运行的只读测试结果为准。
