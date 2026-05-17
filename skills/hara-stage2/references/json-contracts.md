# HARA JSON 契约 - Stage 2

本文件只定义 Stage2 JSON 结构，不定义危害映射方法或执行流程。危害选择规则见 `stage2-hazard.md`，流程见 `SKILL.md`。

所有产物必须是 UTF-8 JSON object。不要输出 Markdown、代码围栏、表格或额外说明文本。

## 顶层结构

只允许顶层 key：

- `meta`
- `mf_vehicle_hazards`
- `hazard_reasoning`
- `knowledge_evidence`
- `review_log`

## 完整输出 Schema（严格遵循）

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "stage": "stage2",
    "generated_at": "ISO时间戳",
    "source_files": [],
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
      "Stage1_Fault_Text": "<Stage1故障字段原文>",
      "故障描述": "MF001：<功能名><故障行为>",
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
  "knowledge_evidence": [],
  "review_log": []
}
```

## 单功能片段

文件：`output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json`

片段约束：

- `meta.stage` 为 `stage2_slice`。
- `meta.function_id` 为当前 `Function_ID`。
- `mf_vehicle_hazards` 行数等于当前 Stage1 单功能片段中非 `nan` 故障单元格数量。
- 当前功能没有非 `nan` 故障时，`mf_vehicle_hazards` 和 `hazard_reasoning` 可以为空数组。
- 片段内 `No.` 从 1 开始连续。
- 片段内 `Milf_ID` 可以本地连续；最终全局编号由 `merge_stage2.py` 重排。
- 片段内 `Stage1_Row` 可以填 `1`；最终合并时会更新为该功能在最终 Stage1 中的全局行号。

## 最终文件

文件：`output/<RUN_ID>_stage2_mf_vehicle_hazards.json`

最终文件只能由 Stage2R 语义评审后的单功能片段合并得到。`merge_stage2.py` 会按 Stage0 功能顺序和片段内 MF 顺序重排：

- `No.`
- `Milf_ID`
- `hazard_reasoning.row`
- `hazard_reasoning.Milf_ID`
- `故障描述` 中的 MF 编号前缀

## 行字段约束

`mf_vehicle_hazards` 固定列：

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

追溯字段 `Function_ID`、`source_function_name`、`Stage1_Row`、`Fault_Field`、`Stage1_Fault_Text` 必须保留，用于 Stage3 精确提取 Stage0 `detail_text`。

## 推理约束

- 每条 MF 必须有一条 `hazard_reasoning`。
- `hazard_reasoning.row` 指向对应 `mf_vehicle_hazards` 行号。
- `hazard_reasoning.Milf_ID` 与对应行 `Milf_ID` 一致。
- `推理.选择的危害` 必须与对应行 `整车级危害` 完全一致。
- `整车级危害` 必须逐字来自 `knowledge-base/automotive/hara/common/vehicle_hazards.json`。
