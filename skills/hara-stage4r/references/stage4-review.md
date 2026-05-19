# Stage 4R: 操作模式评审

目标：评审 Stage4 中唯一由模型填写的 `操作模式`，并确认机器校验已通过。

## 输出

`output/<run_id>_stage4_review.json`

```json
{
  "meta": {
    "run_id": "<run_id>",
    "stage": "stage4_review",
    "target_file": "output/<run_id>_stage4_sg_sum.json",
    "generated_at": "ISO时间戳"
  },
  "overall_result": "pass/failed",
  "issues": [],
  "fixes": [],
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

1. Stage4 机器校验已通过；若未通过，先修 Stage4 或上游 HARA。
2. `操作模式` 不得为 `nan`、空值、`待Stage4模型填写`、`待填写`、`待补充`、`待生成`。
3. `操作模式` 应为简洁模式名，例如 `驻车保持模式`、`坡道起步模式`、`低速泊车模式`、`行驶制动控制模式`。
4. `操作模式` 应与 `Comments` 中的来源场景一致。
5. 不评审或改写工具派生字段；如 `ASIL Level`、MF 覆盖或 QM 过滤有问题，回到 `check_stage_json.py --stage stage4` 或 Stage3 修复。

## 修正原则

- 只修正 `操作模式`。
- 如果 `Comments` 证据不足，定向读取对应 MF 的 Stage3 HARA 来源行。
- 修正后重新运行 Stage4 机器校验。
