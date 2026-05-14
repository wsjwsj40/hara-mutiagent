# Stage 4R: SG_Sum 评审

目标：单独评审安全目标汇总是否与 ASIL 校验后的 HARA 数据一致。

## 输入

- Stage 4 JSON：`output/<run_id>_stage4_sg_sum.json`
- 合并后的 HARA 数据或所有 Stage 3 HARA 文件
- `05-safety_goal.md`

## 输出

- Review JSON：`output/<run_id>_stage4_review.json`
- 修正后的 Stage 4 JSON：仍写回 `output/<run_id>_stage4_sg_sum.json`

## 输出 Schema（严格遵循）

```json
{
  "meta": {
    "run_id": "<run_id>",
    "stage": "stage4_review",
    "target_file": "output/<run_id>_stage4_sg_sum.json",
    "generated_at": "ISO时间戳"
  },
  "overall_result": "pass/failed",
  "issues": [
    {
      "id": "ST4R-001",
      "severity": "error/warning",
      "target": "<SG_No或MF_ID>",
      "description": "<问题描述>",
      "evidence": "<Stage3/Stage4证据>"
    }
  ],
  "fixes": [
    {
      "target_file": "output/<run_id>_stage4_sg_sum.json",
      "target": "<SG_No或字段>",
      "change": "<修正内容>",
      "reason": "<修正原因>"
    }
  ],
  "review_log": [
    {
      "stage": "stage4_review",
      "target": "stage4",
      "result": "pass/failed",
      "issues": [],
      "fixes": [],
      "notes": ""
    }
  ]
}
```

## 检查点

1. 所有最高 ASIL 为 `A/B/C/D` 的 MF 都必须有 SG_Sum 条目。
2. 所有最高 ASIL 为 `QM` 的 MF 都不得有 SG_Sum 条目。
3. `ASIL Level` 不得为 `QM`，且必须与 ASIL 工具校验后的 HARA 最高 ASIL 完全一致。
4. `MF_ID` 必须能追溯到 HARA 中的真实 MF。
5. 安全目标必须与对应 MF 的故障内容和整车危害一致。
6. 安全状态必须能达成安全目标，不能与安全目标或故障类型冲突。
7. 不要在 review 中自行重新计算 ASIL；如需说明 S/E/C 组合，必须使用 `score = S后缀 + E后缀 + C后缀`，例如 `S3+E1+C3 = 7 => A`。
8. 如果自动校验会删除、补齐或重排 SG_Sum，应在 review JSON 中记录。

最终导出前，`validate_hara_json.py --mode basic` 会基于修正后的 HARA 最高 ASIL 自动重建/修正 SG_Sum：删除 QM-only MF 条目、删除未知 MF 条目、去重、补齐缺失的非 QM MF 条目并重排 `SG_No`。最终 Excel 以自动修正后的 SG_Sum 为准。
