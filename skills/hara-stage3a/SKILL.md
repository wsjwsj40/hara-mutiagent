---
name: hara-stage3a
description: Stage 3A 场景与危害事件生成。用于基于一个 MF 级 Stage3 context 生成 output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json，包括场景字段、危害事件、scenario_reasoning 和 max_asil_planning。不要生成 SEC 评级、ASIL、安全目标或安全状态。
---

# Stage 3A：场景与危害事件生成

## 文档分工

- 本文件：定义 Stage3A 的职责、上下文边界、执行流程和验证门禁。
- `references/json-contracts.md`：唯一输出结构契约。
- `references/stage3a-scenario-generation.md`：场景生成、最大风险路径规划和危害事件方法。
- `references/vehicle-dynamics-rules.md`：坡道、行人、追尾等车辆动力学专项规则。

## 职责边界

Stage3A 只为一个 `MF_ID` 生成运行场景和危害事件。不要填写 S/E/C、ASIL、安全目标或安全状态。

## 上下文拆分

Stage3A 不再重新拆分 Stage0 功能背景。功能背景复用 Stage1 已生成的：

```text
output/<RUN_ID>_stage1_context_<Function_ID>.json
```

Stage3A 前只需要把最终 Stage2 中的 MF 拆成一 MF 一个文件：

```text
output/<RUN_ID>_stage3_context_<MF_ID>.json
```

`prepare_stage3_context.py` 会按 Stage2 行里的 `Function_ID` 找到对应 Stage1 context，并把当前 MF、危害推理、功能背景和运行域提示合成一个 MF 级 context。不要让 Stage3A worker 读取完整 Stage0 或完整 Stage2。

## 输入输出

- 输入：`output/<RUN_ID>_stage3_context_<MF_ID>.json`
- 输出：`output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json`
- 每个 worker 只处理一个 `MF_ID`。

## 执行流程

1. 读取当前 MF 的 Stage3 context。
2. 从 context 中提取 `mf`、`hazard_reasoning`、`function_context`、`matched_functions` 和 `operating_domain_hints`。
3. 读取 `references/json-contracts.md`、`references/stage3a-scenario-generation.md`、`references/vehicle-dynamics-rules.md`。
4. 读取 `knowledge-base/automotive/hara/common/operation_scenarios.json`，场景枚举字段必须使用库内值。
5. 先写 `max_asil_planning`，规划可信最高风险路径。
6. 生成 10-20 条真实可信且不重复的场景和危害事件。
7. 写入 UTF-8 JSON，运行验证并只修正必要字段。

## 验证

```text
python tools/hara/prepare_stage3_context.py mf-context --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --stage1-context-dir output --mf-id <MF_ID> --prefix <RUN_ID> --out output/<RUN_ID>_stage3_context_<MF_ID>.json
python tools/hara/check_stage_json.py --stage stage3a --json output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --mf-id <MF_ID> --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
```

批量生成 context：

```text
python tools/hara/prepare_stage3_context.py mf-context --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --stage1-context-dir output --all --prefix <RUN_ID> --out-dir output
```

## 返回

返回 `status`、`MF_ID`、场景数量、输出文件，并说明是否进入 Stage3B。
