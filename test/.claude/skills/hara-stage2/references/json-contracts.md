# HARA JSON 契约 - Stage 2

所有阶段文件必须是 UTF-8 JSON object。不要输出 Markdown 表格、代码围栏、额外说明文本或数组作为顶层结构。

## 完整输出 Schema（严格遵循）

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "stage": "stage2",
    "generated_at": "ISO时间戳",
    "source_files": [
      "output/<RUN_ID>_stage0_function_mapping.json",
      "output/<RUN_ID>_stage1_derive_mf.json"
    ],
    "knowledge_files_used": []
  },
  "mf_vehicle_hazards": [
    {
      "No.": 1,
      "Milf_ID": "MF001",
      "Function_ID": "F001",
      "source_function_name": "<Stage0/Stage1功能名称>",
      "Stage1_Row": 1,
      "Fault_Field": "功能丧失",
      "Stage1_Fault_Text": "<Stage1中对应故障字段原文>",
      "故障描述": "MF001：<功能名>在<条件>下<故障行为>",
      "整车级危害": "<vehicle_hazards.json中的允许值>",
      "备注": ""
    }
  ],
  "hazard_reasoning": [
    {
      "row": 1,
      "Milf_ID": "MF001",
      "推理": {
        "功能影响": "<故障后功能输出如何变化>",
        "车辆级后果": "<车辆运动/状态层面的后果>",
        "关键判断": "<区分相似危害的关键判断>",
        "选择的危害": "<与整车级危害完全一致>",
        "选择理由": "<为什么选择该危害>"
      }
    }
  ],
  "knowledge_evidence": [
    {
      "source": "<实际读取的知识库或参考文件>",
      "used_for": "<使用目的>"
    }
  ],
  "review_log": []
}
```

## 本阶段文件

文件：`output/<run_id>_stage2_mf_vehicle_hazards.json`

只允许顶层 key：`meta`、`mf_vehicle_hazards`、`review_log`、`knowledge_evidence`、`hazard_reasoning`。

### mf_vehicle_hazards 固定列

- `No.`
- `Milf_ID`
- `Function_ID`
- `source_function_name`
- `Stage1_Row`
- `Fault_Field`
- `Stage1_Fault_Text`
- `故障描述`
- `整车级危害`
- `备注`

`整车级危害` 必须逐字来自 `knowledge-base/automotive/hara/common/vehicle_hazards.json`。

### Stage3 追溯字段（必须包含）

这些字段不一定导出到 Excel，但必须保留在 Stage2 JSON 中，用于 `prepare_stage3_context.py` 精确提取 Stage0 的 `detail_text`：

- `Function_ID`：来自 Stage0/Stage1 的功能编号，例如 `F001`
- `source_function_name`：Stage1 `子功能`，应与 Stage0 功能名称一致或可追溯
- `Stage1_Row`：该故障来自 Stage1 `derive_mf` 的第几行
- `Fault_Field`：该故障来自哪个字段，例如 `功能丧失`、`过小`、`非预期激活`
- `Stage1_Fault_Text`：Stage1 对应该故障字段的原始文本

`故障描述` 可以面向人工阅读，但 Stage3 上下文提取必须优先依赖上述结构化字段。

当 Stage1 与 Stage0 行数一一对应时，`Function_ID` 按 `Stage1_Row` 回查 Stage0 `function_mapping` 中同序号功能；不要让模型凭功能名猜测。

### hazard_reasoning 结构（必须包含）

用于记录每个 MF 的整车危害映射推理过程，推理在选择危害之前生成。

```json
{
  "hazard_reasoning": [
    {
      "row": 1,
      "Milf_ID": "MF001",
      "推理": {
        "功能影响": "静态开关拉起功能丧失，无法实现驻车锁定",
        "车辆级后果": "车辆在坡道上无法保持静止，发生溜车",
        "关键判断": "车辆是'自己动了'（非预期位移），而非'想动动不了'",
        "选择的危害": "非预期的纵向移动",
        "选择理由": "驻车失效的后果是车辆因重力发生溜车，符合'非预期的纵向移动'定义（车辆在无运动请求时发生移动）"
      }
    }
  ]
}
```

**字段说明**：
- `功能影响`：描述功能原本要实现什么，故障后发生了什么
- `车辆级后果`：描述故障导致车辆在运动层面发生的具体异常
- `关键判断`：明确区分关键对立面（如"自己动了"vs"想动动不了"）
- `选择的危害`：最终选择的整车危害名称（必须与 `整车级危害` 字段一致）
- `选择理由`：说明为什么选择该危害而非其他相似危害

**一致性约束**：
- `推理.选择的危害` 必须与 `mf_vehicle_hazards` 中对应行的 `整车级危害` 完全一致
- 评审时必须检查推理记录是否与最终选择一致
