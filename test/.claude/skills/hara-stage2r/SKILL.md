---
name: hara-stage2r
description: Stage 2R 整车危害评审。用于在进入 Stage 3A 前，基于 Stage 1 故障评审 output/<RUN_ID>_stage2_mf_vehicle_hazards.json，检查 MF 数量、Milf_ID 连续性、整车危害映射准确性、hazard_reasoning 一致性和常见映射错误。
---

# Stage 2R：整车危害评审

## 职责边界

评审并在必要时修正 Stage 2 整车危害。不要生成场景或 SEC 评级。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage1_derive_mf.json`
  - `output/<RUN_ID>_stage2_mf_vehicle_hazards.json`
- 输出：`output/<RUN_ID>_stage2_review.json`；如需修正，同时更新 Stage 2 JSON。

## 上下文加载

1. 读取 Stage 2 JSON。
2. 只读取 Stage 1 中用于枚举非 `nan` 故障和验证映射的内容。
3. 读取 `references/stage2-review.md`，确认评审标准。
4. 只有在危害选择存疑时，才加载 `knowledge-base/automotive/hara/common/03-hazard.md` 和 `vehicle_hazards.json`。

## 检查项

- 行数等于 Stage 1 非 `nan` 故障数。
- `Milf_ID` 连续：`MF001`、`MF002`。
- 每个 Stage 1 故障恰好映射到一条 Stage 2 记录。
- 每条 Stage 2 记录必须保留 `Function_ID`、`source_function_name`、`Stage1_Row`、`Fault_Field`、`Stage1_Fault_Text`，用于 Stage3 精确追溯 Stage0 `detail_text`。
- `故障描述` 可追溯到 Stage 1，且包含关键适用条件。
- `整车级危害` 是整车层面的危害，不是功能层面的症状，并且来自允许危害列表。
- `hazard_reasoning.选择的危害` 与行内 `整车级危害` 一致。
- 常见错误：
  - 驻车/保持失效导致溜车时，应属于非预期移动，不是无法移动。
  - 除非车辆驱动方向确实反转，否则不要把功能方向错误写成车辆反向运动。

## 执行流程

1. 先验证结构和数量。
2. 建立 Stage 1 非 `nan` 故障索引。
3. 将每条 Stage 2 记录与源故障和允许危害定义对照。
4. 只修正明确的映射或结构不一致。
5. 按 `references/stage2-review.md` 中的“输出 Schema（严格遵循）”写入 review JSON；字段名、顶层 key、数组/对象结构不要改名或增包一层。
6. 如果修正了 Stage 2 JSON，重新运行 Stage 2 验证并确认通过。

## 验证

```text
python tools/hara/check_stage_json.py --stage stage2 --json output/<RUN_ID>_stage2_mf_vehicle_hazards.json --stage1 output/<RUN_ID>_stage1_derive_mf.json --fix
```

## 返回

返回 `passed` 或 `failed`、问题数量、修正内容、评审文件路径，以及是否允许进入 Stage 3A。
