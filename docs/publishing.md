# GitHub 发布说明

这份清单面向仓库维护者。公开坐标固定为
[`AVICII379/session-handoff-card`](https://github.com/AVICII379/session-handoff-card)，
插件清单只公开 GitHub 用户名和仓库链接，不保存个人邮箱或开发机路径。

## 1. 发布身份和许可边界

当前发布身份：

- GitHub 用户：`AVICII379`；
- 仓库：`https://github.com/AVICII379/session-handoff-card`；
- Git 提交使用 GitHub noreply 地址，仅配置在本仓库的 `.git/config` 中；
- 未选择许可证，因此不在清单中伪造 `license`、隐私政策或条款链接。

没有 `LICENSE` 时，公开可见不等于开源授权。维护者决定许可证后，应以独立提交
增加 `LICENSE`，并在 `plugin.json` 中加入对应 SPDX 标识。

## 2. 本地发布门

在仓库根目录运行：

```powershell
$env:PYTHONUTF8 = "1"
python -m unittest discover -s tests -v
python .\tools\check_publication_privacy.py
python .\examples\run_demo.py
python .\tools\package_release.py --output-dir .\dist
python .\tools\check_publication_privacy.py --archive-dir .\dist
```

必须同时满足：

- 所有测试通过；
- 演示为 `HANDOFF_READY / FULL`；
- `coverage_exact` 为 `true`；
- 校验器错误和警告均为 0；
- 源码与发布 ZIP 的隐私扫描均为 `ok: true`；
- `dist/release-manifest.json` 中的 SHA-256 与
  `dist/SHA256SUMS.txt` 一致。

## 3. 初始化并推送仓库

如果目录尚未初始化 Git：

```powershell
git init
git add .
git commit -m "feat: publish session handoff card skill"
git branch -M main
git remote add origin https://github.com/AVICII379/session-handoff-card.git
git push -u origin main
```

如果远程仓库已有 README、LICENSE 或提交历史，不要直接强推；先拉取并正常
合并。不要为了公开仓库而自动创建或猜测许可证。

## 4. 检查 GitHub Actions

推送后打开 Actions，确认 `validate` 工作流在以下组合全部通过：

- Windows + Python 3.10；
- Windows + Python 3.12；
- Ubuntu + Python 3.10；
- Ubuntu + Python 3.12。

Ubuntu/Python 3.12 任务会上传一个验证用插件 ZIP 工件。

## 5. 创建 Release

建议把以下文件附加到对应版本的 GitHub Release：

- `dist/session-handoff-card-plugin-<version>.zip`；
- `dist/SHA256SUMS.txt`；
- `dist/release-manifest.json`。

Release Notes 可直接从 `CHANGELOG.md` 的对应版本整理。Tag 和
`plugin.json` 的版本应完全一致。

## 6. 从 GitHub 做干净安装验收

在没有本地开发路径残留的环境中运行：

```powershell
codex plugin marketplace add AVICII379/session-handoff-card
codex plugin add session-handoff-card@session-handoff-card
```

新建任务后检查：

1. 插件显示名是“通用会话交接卡”；
2. `session-handoff-card` Skill 能被发现；
3. 中文默认提示词可触发写出模式；
4. `examples/run_demo.py` 的交接包可被新任务正确接收；
5. 卸载或换机后没有依赖开发机绝对路径。

只有这一步通过后，才能把“GitHub 可安装”标记为已验证。
