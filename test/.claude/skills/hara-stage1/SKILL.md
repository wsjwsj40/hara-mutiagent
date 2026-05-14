---
name: hara-stage1
description: Stage 1 功能故障生成。用于基于 Stage 0 功能生成 output/<RUN_ID>_stage1_derive_mf.json，包括故障字段、nan 判断和 field_reasoning。只适用于功能故障推导，不用于整车危害、场景、SEC 评级、ASIL 同步或安全目标。
---

# Stage 1：功能故障生成

## 职责边界

为 Stage 0 中的每个功能生成候选功能故障。不要生成整车危害或 SEC 评级。每个判断都必须能够追溯到功能的 `detail_text`。

## 输入输出

- 输入：`output/<RUN_ID>_stage0_function_mapping.json`。
- 输出：`output/<RUN_ID>_stage1_derive_mf.json`。
- 必读契约：`references/json-contracts.md`、`references/stage1-malfunction.md`。

## 上下文加载

1. 读取 Stage 0 JSON，提取 `Function_ID`、功能名称、`detail_text`、类别和备注。
2. 读取 `references/json-contracts.md`，确认输出结构。
3. 读取 `references/stage1-malfunction.md`，确认故障类型细则。
4. 仅在需要时加载知识库：
   - 故障类型定义不清时，读取 `knowledge-base/automotive/hara/common/02-malfuntioning_behavior.md`。
   - Stage 0 的系统线索会影响失效行为时，读取 `knowledge-base/automotive/hara/systems/<system>/01-basic_information.md`。
5. 本阶段不要加载风险评估、场景或安全目标知识库。

## 规则

- `derive_mf` 行数必须等于 Stage 0 `function_mapping` 行数。
- 每个功能生成一行。
- 必须逐项判断：`功能丧失`、`过大`、`过早`、`过小`、`过晚`、`非预期激活`、`卡滞`、`方向错误`。
- 只有对应 `field_reasoning.推理.是否有安全风险` 为 `否`，且推理说明为什么不适用时，才能填写 `nan`。
- 如果 `是否有安全风险` 为 `是`，可见故障字段必须填写具体故障描述，不能写 `nan`。
- 故障描述必须是功能边界内的具体异常行为，不能只是功能名加通用引导词。
- 对保持、约束、保护、制动、力、压力、扭矩类功能，重点复核 `过小`；这类通常有安全相关性。

## 执行流程

1. 从 Stage 0 行构建工作列表，并保留每个功能的 `detail_text`。
2. 对每个功能识别实际输出：力、扭矩、状态、命令、信息、时机或方向。
3. 判断每种故障类型，并为每个字段记录 `field_reasoning`，包括 `nan` 字段。
4. 先读取 `references/json-contracts.md` 顶部的“完整输出 Schema（严格遵循）”。
5. 严格按 Schema 构建 `meta`、`derive_mf`、`field_reasoning`、`knowledge_evidence`、`review_log`；字段名、顶层 key、数组/对象结构不要改名或增包一层。
6. 只写 UTF-8 JSON，不输出 Markdown 包裹。
7. 返回前运行验证并修正结构/数量问题；验证失败时修 JSON 文件，不用解释代替修复。

## 验证

```text
python tools/hara/check_stage_json.py --stage stage1 --json output/<RUN_ID>_stage1_derive_mf.json --stage0 output/<RUN_ID>_stage0_function_mapping.json --fix
```

## 返回

返回 `status`、`function_count`、`total_faults`、`output_file`，并说明下一步是否进入 Stage 1R。
