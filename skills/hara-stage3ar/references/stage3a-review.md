# Stage 3AR 场景评审

本文件只定义 Stage3A 场景评审。SEC 评级评审见 `hara-stage3br`，Stage3A/3B 合并一致性由 `check_stage_json.py --stage stage3` 校验。

## 输出结构

`output/<RUN_ID>_stage3a_<MF_ID>_review.json`

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "stage": "stage3a_review",
    "mf_id": "<MF_ID>",
    "target_file": "output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json",
    "generated_at": "ISO时间戳"
  },
  "overall_result": "pass/failed",
  "issues": [],
  "fixes": [],
  "per_scenario_reviews": []
}
```

## 检查点

- `max_asil_planning` 是否围绕当前 MF 的可信最高风险路径，不是随机组合场景。
- 每条场景是否真实、独立、不重复。
- 场景是否在功能运行域内。
- 六大场景字段是否与 `scenario_reasoning.场景条件相关性检查` 一致。
- 危害事件是否由 MF、整车危害和场景条件自然推出。
- 运动方向、道路条件、风险对象位置、驾驶员是否在车上是否自洽。

## 修正原则

- 结构、枚举、`不涉及` 一致性优先用 `check_stage_json.py --stage stage3a --fix`。
- 语义问题只修 Stage3A 文件，不修改 Stage3B 或合并 HARA。
- 如果高风险路径覆盖不足，退回 Stage3A 重新生成相关场景。
