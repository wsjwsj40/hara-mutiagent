# HARA JSON 契约 - Stage 3A

本文件只定义 Stage3A 输出结构和机器可校验字段约束。场景生成方法、风险路径规划和危害事件规则见 `stage3a-scenario-generation.md` 与 `vehicle-dynamics-rules.md`。

所有产物必须是 UTF-8 JSON object。不要输出 Markdown、代码围栏、表格或额外说明文本。

## 顶层结构

文件：`output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json`

只允许顶层 key：

- `meta`
- `max_asil_planning`
- `scenarios`
- `review_log`

## 完整输出 Schema（严格遵循）

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "mf_id": "<MF_ID>",
    "stage": "stage3a",
    "generated_at": "ISO时间戳"
  },
  "max_asil_planning": {
    "高风险因素分析": [],
    "规划的场景原型": [],
    "预期最大_ASIL": "QM/A/B/C/D 或 待Stage3B确认",
    "规划理由": "<规划理由>"
  },
  "scenarios": [
    {
      "List_No": 1,
      "MF_ID": "<MF_ID>",
      "故障描述": "<必须与 Stage2 当前 MF 一致>",
      "整车危害": "<必须与 Stage2 当前 MF 一致>",
      "道路类型": "<operation_scenarios.json 枚举值>",
      "道路条件": "<operation_scenarios.json 枚举值>",
      "环境条件": "<operation_scenarios.json 枚举值>",
      "车辆状态": "<operation_scenarios.json 枚举值>",
      "车速(km/h)": "<operation_scenarios.json 枚举值>",
      "特殊要素": "<operation_scenarios.json 枚举值>",
      "附加条件": "<库外细节>",
      "驾驶员是否在车上": "是/否/不涉及",
      "危害事件": "<危害事件>",
      "scenario_reasoning": {
        "场景规划理由": "<为什么选择这个场景>",
        "危害事件推理": "<如何推出危害事件>",
        "场景条件相关性检查": {
          "道路类型": "相关/不涉及，理由",
          "道路条件": "相关/不涉及，理由",
          "环境条件": "相关/不涉及，理由",
          "车辆状态": "相关/不涉及，理由",
          "车速": "相关/不涉及，理由",
          "特殊要素": "相关/不涉及，理由"
        }
      }
    }
  ],
  "review_log": []
}
```

## scenarios 固定列

- `List_No`
- `MF_ID`
- `故障描述`
- `整车危害`
- `道路类型`
- `道路条件`
- `环境条件`
- `车辆状态`
- `车速(km/h)`
- `特殊要素`
- `附加条件`
- `驾驶员是否在车上`
- `危害事件`
- `scenario_reasoning`

## max_asil_planning 约束

必须包含：

- `高风险因素分析`
- `规划的场景原型`
- `预期最大_ASIL`
- `规划理由`

`预期最大_ASIL` 是 Stage3A 的规划假设，不是最终评级。

## scenario_reasoning 约束

每条场景必须包含：

- `场景规划理由`
- `危害事件推理`
- `场景条件相关性检查`

`场景条件相关性检查` 必须覆盖六大场景字段：

- `道路类型`
- `道路条件`
- `环境条件`
- `车辆状态`
- `车速`
- `特殊要素`

## 场景枚举约束

六大场景字段必须逐字来自 `knowledge-base/automotive/hara/common/operation_scenarios.json` 对应键下的枚举值：

- `道路类型`
- `道路条件`
- `环境条件`
- `车辆状态`
- `车速(km/h)`
- `特殊要素`

特殊允许值：`不涉及`、`ALL`。

库外细节只能写入 `附加条件`。不要把道路条件、环境条件、特殊要素等跨字段填写。

## 自动修正规则

`check_stage_json.py --stage stage3a --stage2 <Stage2文件> --fix` 会：

- 校验 `meta.mf_id`、场景 `MF_ID`、`故障描述`、`整车危害` 与 Stage2 当前 MF 一致。
- 校验 `List_No` 连续、顶层 key 固定、`max_asil_planning` 非空。
- 根据 `scenario_reasoning.场景条件相关性检查` 将无关场景字段规范化为 `不涉及`。

写法要求：

- 不相关：`不涉及，<理由>`
- 相关：`相关，<理由>`

## 数量约束

每个 `MF_ID` 的 `scenarios` 数量默认应为 10-20 条，具体由验证命令的 `--min-scenarios` 和 `--max-scenarios` 控制。
