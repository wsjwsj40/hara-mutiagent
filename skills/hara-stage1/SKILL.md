---
name: hara-stage1
description: Stage 1 功能故障生成。用于基于 Stage 0 功能生成 output/<RUN_ID>_stage1_derive_mf.json，包括故障字段、nan 判断和 field_reasoning。只适用于功能故障推导，不用于整车危害、场景、SEC 评级、ASIL 同步或安全目标。
---

# Stage 1：功能故障生成

## 职责边界

为 Stage 0 中的每个功能生成候选功能故障。不要生成整车危害或 SEC 评级。每个判断都必须能够追溯到功能的 `detail_text`。

## 输入输出

- 输入：`output/<RUN_ID>_stage0_function_mapping.json`。
- 最终输出：`output/<RUN_ID>_stage1_derive_mf.json`，由 Stage1R 语义评审后的单功能片段合并得到。
- 多功能中间输入：`output/<RUN_ID>_stage1_context_<Function_ID>.json`。
- 多功能中间输出：`output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`。
- 必读：`references/json-contracts.md`（唯一输出结构契约）、`references/stage1-malfunction.md`（故障类型判断规则）。

## 上下文加载

1. 读取 Stage 0 JSON，提取 `Function_ID`、功能名称、`detail_text`、类别和备注。
2. 读取 `references/json-contracts.md`，确认输出结构、顶层 key、字段名和一致性约束。
3. 读取 `references/stage1-malfunction.md`，确认故障类型细则；不要从该文件推断或复制输出 Schema。
4. 仅在需要时加载知识库：
   - 故障类型定义不清时，读取 `knowledge-base/automotive/hara/common/02-malfuntioning_behavior.md`。
   - Stage 0 的系统线索会影响失效行为时，读取 `knowledge-base/automotive/hara/systems/<system>/01-basic_information.md`。
5. 本阶段不要加载风险评估、场景或安全目标知识库。

## 规则

- `derive_mf` 行数必须等于 Stage 0 `function_mapping` 行数。
- 每个功能生成一行。
- 当 Stage 0 有多个功能时，编排器必须按功能拆分多个真实子 agent；每个分析 worker 只处理一个 `Function_ID` 的 `detail_text`，避免在同一上下文中生成多个功能的故障。
- Stage0 切片必须由 `tools/hara/prepare_stage1_context.py` 生成。
- 多 worker 输出先作为单功能片段保存；不要在 Stage1 生成后立即合并最终文件，必须先进入 Stage1R 单功能语义评审。
- Stage1R 修正并复检所有单功能片段后，才由 `tools/hara/merge_stage1.py` 按 Stage0 顺序合并、重排 `No.` 和 `field_reasoning.row`，写入唯一的 `output/<RUN_ID>_stage1_derive_mf.json`。
- 输出结构只以 `references/json-contracts.md` 为准；`references/stage1-malfunction.md` 不定义 JSON Schema。
- 必须逐项判断：`功能丧失`、`过大`、`过早`、`过小`、`过晚`、`非预期激活`、`卡滞`、`方向错误`。
- `field_reasoning.推理.是否适用` 决定 Stage1 可见故障字段：`是` 时必须填写具体故障描述，`否` 时必须填写 `nan`。
- `field_reasoning.推理.是否有安全风险` 只用于标记是否进入 Stage2：适用但无安全风险的故障仍保留在 Stage1，不进入 Stage2。
- 只有对应故障类型在当前功能边界内确实不适用，且推理说明为什么不适用时，才能填写 `nan`。
- 故障描述必须是功能边界内的具体异常行为，不能只是功能名加通用引导词。
- 对保持、约束、保护、制动、力、压力、扭矩类功能，重点复核 `过小`；这类通常有安全相关性。

## 执行流程

1. 从 Stage 0 行构建工作列表，并保留每个功能的 `detail_text`。
2. 如果工作列表超过 1 个功能，先运行 `tools/hara/prepare_stage1_context.py`，为每个 `Function_ID` 生成独立上下文文件。
3. 编排器按 `Function_ID` 拆分子 agent；单个 worker 只接收当前 `stage1_context_<Function_ID>.json` 和必要规则文件。
4. 对当前功能识别实际输出：力、扭矩、状态、命令、信息、时机或方向。
5. 判断每种故障类型，并为每个字段记录 `field_reasoning`，包括 `nan` 字段。
6. 单功能 worker 严格按 Stage1 片段契约写 `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`；该文件必须只有一行 `derive_mf` 和一行 `field_reasoning`。
7. 每个单功能片段写入后运行 `check_stage_json.py --stage stage1_slice --fix`；校验器可修正 `field_reasoning` 与可见故障字段的机械一致性，其他失败项交回当前 worker 修正。
8. 所有 Stage1 片段通过后，进入 Stage1R 单功能语义评审；不要在 Stage1R 前合并最终 Stage1 文件。
9. Stage1R 完成并复检所有片段后，编排器运行 `tools/hara/merge_stage1.py` 合并为最终 Stage1 文件。
10. 合并后的最终 Stage1 文件必须运行 `check_stage_json.py --stage stage1` 并修正结构/数量问题；验证失败时修 JSON 文件，不用解释代替修复。

## 验证

```text
python tools/hara/prepare_stage1_context.py --stage0 output/<RUN_ID>_stage0_function_mapping.json --prefix <RUN_ID> --out-dir output
python tools/hara/check_stage_json.py --stage stage1_slice --json output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json --stage0 output/<RUN_ID>_stage0_function_mapping.json --function-id <Function_ID> --fix
# Stage1R 逐 Function_ID 评审并修正单功能片段后，再执行最终合并：
python tools/hara/merge_stage1.py --stage0 output/<RUN_ID>_stage0_function_mapping.json --input-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage1_derive_mf.json
python tools/hara/check_stage_json.py --stage stage1 --json output/<RUN_ID>_stage1_derive_mf.json --stage0 output/<RUN_ID>_stage0_function_mapping.json --fix
```

## 返回

返回 `status`、`function_count`、单功能片段文件列表，并说明下一步进入 Stage 1R 单功能语义评审。
