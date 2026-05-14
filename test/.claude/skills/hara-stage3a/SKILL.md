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
- 必读契约：`references/json-contracts.md`、`references/stage3a-scenario-generation.md`、`references/vehicle-dynamics-rules.md`。

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

### 枚举字段约束（核心规则）

**六大场景字段（道路类型、车辆运动状态、车速档位范围、外部环境条件、驾驶场景/工况、风险对象）必须严格使用 `operation_scenarios.json` 对应键下的枚举值。**

- ✅ 允许填入六大场景字段的内容：
  - `operation_scenarios.json` 中该键下的枚举值
  - 通用值：`不涉及`、`ALL`

- ❌ 禁止填入六大场景字段的内容：
  - 任何不在 `operation_scenarios.json` 枚举列表中的文字
  - 自定义描述、组合值、模糊表述

- ✅ 枚举值之外的所有细节必须写入 `附加条件` 字段

**示例：**

| 场景字段 | operation_scenarios.json 枚举值 | 正确写法 | 错误写法 |
|---------|-------------------------------|---------|---------|
| 道路类型 | `["高速公路", "城市道路", "乡村道路", ...]` | `高速公路` | `高速路`、`快速路` |
| 车辆运动状态 | `["直线行驶", "转弯", "变道", ...]` | `直线行驶` | `直线匀速行驶`、`正在直线开` |
| 风险对象 | `["本车乘客", "对向车辆", "行人", ...]` | `对向车辆` | `对面来车`、`前方车辆` |

当场景需要更具体描述时（如"高速公路、雨天、夜间"），场景字段填 `高速公路`，具体细节写入 `附加条件`：`雨天、夜间、能见度约50米`。

### 其他规则

- 写 `危害事件` 前，必须检查车辆运动方向、风险对象位置、道路条件和驾驶员是否在车上。
- 在 `scenario_reasoning.场景条件相关性检查` 中，将无关条件标记为 `不涉及，理由`；验证工具可据此把字段规范化为 `不涉及`。

## 执行流程

1. **读取完整 Schema**：先读取 `references/json-contracts.md` 顶部的完整输出 Schema
2. 读取当前 MF 的 Stage3 context。
3. 围绕可信最大 ASIL 规划场景，而不是机械组合条件。
4. 在功能运行域内生成多样但不重复的场景。
5. **严格按 Schema 输出**：完全按照 `json-contracts.md` 中的 Schema 格式输出，不要改变字段顺序或结构
6. 只写 UTF-8 JSON，不输出 Markdown 包裹。
7. 使用 operation-scenario 枚举检查和 `--fix` 进行验证。

**重要：输出格式必须严格遵循 Schema，确保每次输出格式一致。**

## 验证错误处理

当验证脚本报错时（如枚举值错误）：

1. **先重新读取文件**：在尝试修复前，先读取当前文件内容，检查是否已修复
2. **如果已正确**：跳过修复，直接重新运行验证确认
3. **如果仍有错误**：只修复不同的部分，避免 "old_string and new_string are exactly the same" 错误
4. **重新验证**：修复后重新运行验证脚本确认

**重要**：不要在收到验证错误后盲目重新生成整个文件。先检查当前状态，只修复必要的字段。

## 验证

```text
python tools/hara/prepare_stage3_context.py mf-context --stage0 output/<RUN_ID>_stage0_function_mapping.json --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --mf-id <MF_ID> --prefix <RUN_ID> --out output/<RUN_ID>_stage3_context_<MF_ID>.json
python tools/hara/check_stage_json.py --stage stage3a --json output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
```

## 返回

返回 `status`、已处理的 `MF_ID`、场景数量、输出文件，并说明下一步是否进入 Stage 3B。
