# HARA JSON 契约 - Stage 4

所有阶段文件必须是 UTF-8 JSON object。不要输出 Markdown 表格、代码围栏、额外说明文本或数组作为顶层结构。

## 完整输出 Schema（严格遵循）

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "stage": "stage4",
    "generated_at": "ISO时间戳",
    "source_files": [
      "output/<RUN_ID>_stage3_<MF_ID>_hara.json"
    ],
    "knowledge_files_used": []
  },
  "sg_sum": [
    {
      "SG_No": 1,
      "MF_ID": "MF001",
      "安全目标": "<继承最高ASIL路径的安全目标>",
      "ASIL Level": "A/B/C/D",
      "安全状态": "<继承或归纳的安全状态>",
      "操作模式": "<适用操作模式>",
      "FTTI(ms)": 1000,
      "Comments": "<备注或空字符串>"
    }
  ],
  "review_log": []
}
```

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
