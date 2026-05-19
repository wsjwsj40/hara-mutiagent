---
name: hara-stage2
description: Stage 2 整车危害生成。用于将 Stage 1 单功能片段中非 nan 且 field_reasoning.推理.是否有安全风险=是 的功能故障转换为整车级危害，按 Function_ID 生成 output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json。最终 Stage2 合并必须在 Stage2R 单片语义评审通过后执行。不要用于场景生成、SEC 评级、ASIL 计算或安全目标。
---

# Stage 2：整车危害生成

## 文档分工

- 本文件：定义 Stage2 的职责、上下文边界、执行流程和门禁。
- `references/json-contracts.md`：唯一输出结构契约，包含最终文件和 `stage2_slice` 片段结构。
- `references/stage2-hazard.md`：危害映射语义方法，不定义 JSON schema。

## 职责边界

Stage2 只把当前 `Function_ID` 的功能故障转换为整车级危害。不要生成场景、SEC 评级、ASIL 或安全目标。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`
  - 可选：`output/<RUN_ID>_stage1_context_<Function_ID>.json`
- 单功能输出：`output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json`
- 最终输出：`output/<RUN_ID>_stage2_mf_vehicle_hazards.json`，由 Stage2R 修正并复检所有片段后通过 `tools/hara/merge_stage2.py` 合并。

## 上下文加载

1. 只读取当前 Stage1 单功能片段；不要读取完整 Stage1 合并文件。
2. 只读取当前功能的 Stage0 `detail_text` 或 Stage1 context。
3. 读取 `references/json-contracts.md` 确认输出结构。
4. 读取 `references/stage2-hazard.md` 确认危害映射方法。
5. 危害库不清楚时，再加载 `knowledge-base/automotive/hara/common/03-hazard.md` 和 `knowledge-base/automotive/hara/common/vehicle_hazards.json`。

## 执行流程

1. 枚举当前 Stage1 单功能片段中非 `nan` 且对应 `field_reasoning.推理.是否有安全风险=是` 的故障字段。
2. 每个安全相关故障生成一条 `mf_vehicle_hazards`；非 `nan` 但 `是否有安全风险=否` 的故障只保留在 Stage1，不生成 Stage2 表格行。
3. 基于功能影响推导车辆级后果，选择 `vehicle_hazards.json` 中最贴近的危害。
4. 为每条 MF 写入 `hazard_reasoning`。
5. 写入 Stage2 单功能片段。
6. 运行 `stage2_slice --fix`；失败时修正当前片段。
7. 所有 Stage2 片段通过后进入 Stage2R；不要在 Stage2R 前合并最终 Stage2 文件。

## 验证

```text
python tools/hara/check_stage_json.py --stage stage2_slice --json output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json --stage1 output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json --function-id <Function_ID> --fix
# Stage2R 逐 Function_ID 评审并修正单功能片段后，再执行最终合并：
python tools/hara/merge_stage2.py --stage0 output/<RUN_ID>_stage0_function_mapping.json --input-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage2_mf_vehicle_hazards.json
python tools/hara/check_stage_json.py --stage stage2 --json output/<RUN_ID>_stage2_mf_vehicle_hazards.json --stage1 output/<RUN_ID>_stage1_derive_mf.json --fix
```

## 返回

返回 `status`、`Function_ID`、本片段 `total_mf`、危害类别摘要、片段输出文件，并说明是否允许进入 Stage2R。
