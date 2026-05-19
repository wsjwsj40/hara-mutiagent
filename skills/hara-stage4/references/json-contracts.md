# HARA JSON 契约 - Stage 4

所有阶段文件必须是 UTF-8 JSON object。不要输出 Markdown 表格、代码围栏、额外说明文本或数组作为顶层结构。

## 输出 Schema

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "stage": "stage4",
    "source": "output 或合并 JSON 路径",
    "generation": "deterministic_group_by_mf_and_safety_goal_highest_asil_min_ftti_except_operation_mode",
    "operation_mode_policy": "only 操作模式 is model-filled; rows are grouped within each MF by safety goal with highest ASIL and minimum FTTI"
  },
  "sg_sum": [
    {
      "SG_No": "SG001",
      "MF_ID": "MF001",
      "安全目标": "<工具按同一 MF 内相同安全目标汇总>",
      "ASIL Level": "A/B/C/D",
      "安全状态": "<工具从代表 HARA 场景继承>",
      "操作模式": "<模型填写>",
      "FTTI(ms)": "<同一 MF/安全目标组合的最小 FTTI>",
      "Comments": "<工具生成的分组和来源场景证据>"
    }
  ],
  "review_log": []
}
```

## 固定列

- `SG_No`
- `MF_ID`
- `安全目标`
- `ASIL Level`
- `安全状态`
- `操作模式`
- `FTTI(ms)`
- `Comments`

## 约束

- 同一 `MF_ID` 内相同 `安全目标` 只能有一条 SG_Sum；不同 MF 不合并。
- 仅由 `QM` 场景组成的 MF/安全目标组合不得出现在 `sg_sum`。
- `ASIL Level` 必须等于该 MF/安全目标组合在 HARA 中的最高 ASIL。
- `FTTI(ms)` 必须等于该 MF/安全目标组合在 HARA 中的最小 FTTI。
- 除 `操作模式` 外，其他列由工具派生，不由模型改写。
- `操作模式` 必须是具体模式名，不能是 `nan`、空值、`待Stage4模型填写`、`待填写`、`待补充` 或 `待生成`。
