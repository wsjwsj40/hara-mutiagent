# HARA JSON 契约 - Stage 4

所有阶段文件必须是 UTF-8 JSON object。不要输出 Markdown 表格、代码围栏、额外说明文本或数组作为顶层结构。

## 本阶段文件

文件：`output/<run_id>_stage4_sg_sum.json`

只允许顶层 key：`meta`、`sg_sum`、`review_log`。

### sg_sum 固定列

- `SG_No`
- `MF_ID`
- `安全目标`
- `ASIL Level`
- `安全状态`
- `操作模式`
- `FTTI(ms)`
- `Comments`

### QM 规则

如果某个 MF 的最高 ASIL 为 `QM`，该 MF 在 `sg_sum` 中不得出现任何条目。
