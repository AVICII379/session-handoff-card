# 当前规范

- Python 3.10+，核心流程只用标准库。
- 完全离线，不请求 Crossref 或其他服务。
- 输入仅限本目录下的 `inbox/` 测试夹具。
- 只写 `artifacts/catalog-preview.tsv`，绝不移动或重命名文件。
- 输出列：`source_name`、`year`、`first_author`、`title`、`sha256`、
  `proposed_name`、`status`。
- 状态优先级：
  1. 相同内容的第二个及以后文件为 `DUPLICATE`；
  2. 非 `DUPLICATE` 行中，不同内容但 `proposed_name` 相同的全部标为
     `NAME_COLLISION`；
  3. 缺年份为 `REVIEW`；
  4. 其余为 `READY`。
- 标题只清理首尾空白，不改变大小写。
- 面向人的提示使用中文。

当前缺口：`src/catalog.py` 尚未实现 `detect_name_collisions(rows)`，也缺少
两条对应测试。未经用户确认，下一会话只能提交修改计划，不能编辑代码。
