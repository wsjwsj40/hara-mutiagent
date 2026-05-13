---
name: hara-stage2
description: Stage 2 整车危害生成。用于将 Stage 1 中每个非 nan 功能故障转换为整车级危害，生成 output/<RUN_ID>_stage2_mf_vehicle_hazards.json，包括 Milf_ID 分配和 hazard_reasoning。不要用于场景生成、SEC 评级、ASIL 计算或安全目标。
---

# Stage 2：整车危害生成

## 职责边界

将功能层面的故障转换为整车层面的危害。不要生成驾驶场景或 SEC 评级。关注车辆实际发生了什么或无法做到什么，而不是组件症状本身。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage0_function_mapping.json`
  - `output/<RUN_ID>_stage1_derive_mf.json`
- 输出：`output/<RUN_ID>_stage2_mf_vehicle_hazards.json`。
- 必读契约：`references/json-contracts.md`、`references/stage2-hazard.md`。

## 上下文加载

1. 读取 Stage 1 JSON，枚举所有非 `nan` 故障单元格。
2. 只读取当前故障对应功能的 Stage 0 `detail_text`。
3. 读取 `references/json-contracts.md`，确认输出结构。
4. 读取 `references/stage2-hazard.md`，确认危害映射规则。
5. 仅在需要时加载知识库：
   - `knowledge-base/automotive/hara/common/03-hazard.md`
   - `knowledge-base/automotive/hara/common/vehicle_hazards.json`
   - 系统行为不明确时，读取 `knowledge-base/automotive/hara/systems/<system>/01-basic_information.md`。

## 规则

- `mf_vehicle_hazards` 行数必须等于 Stage 1 非 `nan` 故障单元格数量。
- 沿用现有字段名 `Milf_ID`；按 Stage 1 故障顺序连续分配 `MF001`、`MF002`。
- 每个故障生成一条整车危害记录。
- `故障描述` 必须包含 `Milf_ID`、功能名、故障类型和关键适用条件。
- 每条 MF 必须保留结构化追溯字段：`Function_ID`、`source_function_name`、`Stage1_Row`、`Fault_Field`、`Stage1_Fault_Text`。这些字段用于 Stage3 精确提取 Stage0 `detail_text`，不要只依赖 `故障描述` 文本。
- `Function_ID` 从 Stage0 对应行复制；Stage1 行与 Stage0 行一一对应时，用 `Stage1_Row`/行序号回查 Stage0。
- `整车级危害` 必须逐字来自 `vehicle_hazards.json`。
- 每个 MF 生成一条 `hazard_reasoning`，包含 `功能影响`、`车辆级后果`、`关键判断`、`选择的危害`、`选择理由`。
- 驻车/保持失效导致车辆溜车时，不要映射为“无法纵向移动”；应选择对应的非预期移动类危害。
- 除非车辆驱动方向确实反转，不要把功能方向错误误写成车辆行驶方向相反。

## 执行流程

1. 从 Stage 1 非 `nan` 字段构建 MF 列表，并记录源行号、源功能名和故障字段名。
2. 将每个 MF 追溯到 Stage 0 `Function_ID` 和 `detail_text`。
3. 从功能故障推理到车辆实际运动或状态后果。
4. 选择最接近的允许危害，并记录选择理由。
5. 只写 UTF-8 JSON，不输出 Markdown 包裹。
6. 返回前运行验证并修正结构/数量问题。

## 验证

```text
python tools/hara/check_stage_json.py --stage stage2 --json output/<RUN_ID>_stage2_mf_vehicle_hazards.json --stage1 output/<RUN_ID>_stage1_derive_mf.json --fix
```

## 返回

返回 `status`、`total_mf`、危害类别摘要、`output_file`，并说明下一步是否进入 Stage 2R。
