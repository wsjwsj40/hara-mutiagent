---
name: hara-stage3a
description: Stage 3A 场景与危害事件生成。用于为一个或多个 Stage 2 MF 生成 output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json，包括场景字段、危害事件、scenario_reasoning 和 max_asil_planning。不要生成 SEC 评级、ASIL、安全目标或安全状态。
---

# Stage 3A：场景与危害事件生成

## 职责边界

只生成运行场景和危害事件。Stage 3A 不填写 S/E/C、ASIL、安全目标或安全状态。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage3_context_<MF_ID>.json`
- 输出：每个 MF 一个 `output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json`。
- 必读契约：`references/json-contracts.md`、`references/stage3a-scenario-generation.md`。

## 上下文加载

1. 只读取当前 MF 的 `output/<RUN_ID>_stage3_context_<MF_ID>.json`。
2. 从 context 中提取 `mf`、`hazard_reasoning`、`matched_functions.detail_text` 和 `operating_domain_hints`。
3. 读取 `references/json-contracts.md`，确认 JSON 结构和枚举约束。
4. 读取 `references/stage3a-scenario-generation.md`，确认详细场景规则。
5. 读取 `knowledge-base/automotive/hara/common/operation_scenarios.json`，每个枚举值只能放入对应字段。
6. 不要读取完整 Stage 0、完整 Stage 2、`04-risk_assessment.md` 或 `05-safety_goal.md`。

## 子 Agent 边界

- 本 skill 每次只处理一个 `MF_ID`，应由编排器在独立子 agent 中调用。
- 子 agent 只接收 Stage3 context 路径、输出路径和 `RUN_ID`。
- 子 agent 不读取其他 MF 的上下文，不保留前一个 MF 的推理。

## 规则

- 每个输出文件只处理一个 `MF_ID`。
- 每个 MF 生成 10-20 条真实可信的场景。
- 必须包含 `max_asil_planning`，说明如何搜索高风险路径。
- 必填场景字段：`List_No`、`MF_ID`、`故障描述`、`整车危害`、六大场景条件、`附加条件`、`驾驶员是否在车上`、`危害事件`、`scenario_reasoning`。
- 六大场景字段必须只使用 `operation_scenarios.json` 对应键下的值。
- 库外细节写入 `附加条件`，不要塞进枚举字段。
- 允许的通用值：`不涉及`、`ALL`。
- 写 `危害事件` 前，必须检查车辆运动方向、风险对象位置、道路条件和驾驶员是否在车上。
- 在 `scenario_reasoning.场景条件相关性检查` 中，将无关条件标记为 `不涉及，理由`；验证工具可据此把字段规范化为 `不涉及`。

## 执行流程

1. 读取当前 MF 的 Stage3 context。
2. 围绕可信最大 ASIL 规划场景，而不是机械组合条件。
3. 在功能运行域内生成多样但不重复的场景。
4. 记录危害事件推理和场景条件相关性判断。
5. 只写 UTF-8 JSON，不输出 Markdown 包裹。
6. 使用 operation-scenario 枚举检查和 `--fix` 进行验证。

## 验证

```text
python tools/hara/prepare_stage3_context.py mf-context --stage0 output/<RUN_ID>_stage0_function_mapping.json --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --mf-id <MF_ID> --prefix <RUN_ID> --out output/<RUN_ID>_stage3_context_<MF_ID>.json
python tools/hara/check_stage_json.py --stage stage3a --json output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
```

## 返回

返回 `status`、已处理的 `MF_ID`、场景数量、输出文件，并说明下一步是否进入 Stage 3B。
