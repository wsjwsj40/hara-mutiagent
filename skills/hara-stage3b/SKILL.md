---
name: hara-stage3b
description: Stage 3B SEC 评级。用于对 Stage 3A 场景进行 S/E/C 分维度评级，并写入 output/<RUN_ID>_stage3b_<MF_ID>_sec.json，包括 sec_records、sec_reasoning、safety_goal 和 safe_state。只生成 SEC 增量字段供后续合并；不要重新生成场景或修改 Stage 3A 内容。
---

# Stage 3B：SEC 评级

## 职责边界

**Stage3B 总控职责：**
- 调度并协调 S/E/C 子任务
- 准备批次上下文
- 收集子任务结果
- 调用 `merge_sec_batches.py` 合并 SEC 记录（ASIL 由脚本自动计算）
- 组装 `sec_reasoning`、`safety_goal`、`safe_state`

**Stage3B 总控不做：**
- ❌ 不执行具体的 S/E/C 评级（由子 agent 完成）
- ❌ 不读取 S/E/C 评级规则文件（`04-risk_assessment-s/e/c.md`）
- ❌ 不手动计算 ASIL（由 `merge_sec_batches.py` 根据后缀求和规则自动计算）
- ❌ 不修改 Stage 3A 的场景字段、`scenario_reasoning` 或 `max_asil_planning`

**输出：** `output/<RUN_ID>_stage3b_<MF_ID>_sec.json`（Stage3B 增量文件；完整 HARA 文件由 `merge_stage3.py` 生成）

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage3_context_<MF_ID>.json`
  - `output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json`
  - 可选批次上下文：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_context.json`
- 输出：`output/<RUN_ID>_stage3b_<MF_ID>_sec.json`。
- 结构契约：`references/json-contracts.md`。
- 总控导航：`references/stage3b-sec-rating.md`。

## 上下文加载

**总控 agent 只加载以下文件，不要读取 SEC 评级知识库：**

1. 当前 MF 的 Stage3 context。
2. 当前 MF 的 Stage 3A JSON；不要读取其他 MF。
3. `references/json-contracts.md`（输出结构契约）。
4. `references/stage3b-sec-rating.md`（本 stage 总控流程）。
5. `references/sec-merge-safety.md`（合并规则说明）。

**总控不要读取以下文件，这些只由子 agent 读取：**
- ❌ `04-risk_assessment-s.md`（S 评级规则）
- ❌ `04-risk_assessment-e.md`（E 评级规则）
- ❌ `04-risk_assessment-c.md`（C 评级规则）
- ❌ `04-risk_assessment-asil.md`（ASIL 计算由 `merge_sec_batches.py` 自动完成）
- ❌ `sec-s-batch-prompt.md`、`sec-e-batch-prompt.md`、`sec-c-batch-prompt.md`（批次提示词）

**子任务加载范围（每个子 agent 独立加载）：**
- S 子任务：批次上下文 + `references/sec-s-batch-prompt.md` + `knowledge-base/automotive/hara/common/04-risk_assessment-s.md`
- E 子任务：批次上下文 + `references/sec-e-batch-prompt.md` + `knowledge-base/automotive/hara/common/04-risk_assessment-e.md`
- C 子任务：批次上下文 + `references/sec-c-batch-prompt.md` + `knowledge-base/automotive/hara/common/04-risk_assessment-c.md`
- FTTI 子任务：批次上下文 + `knowledge-base/automotive/hara/common/06-ftti.md`

## 子 Agent 边界

- 本 skill 由编排器作为独立子 agent 调用，负责当前 MF 的 Stage3B 总控。
- 当前 MF 内，每个 `stage3b_<MF_ID>_batchXX_context.json` 拆成四个独立子任务：
  - S 子任务只判断严重度，不判断 E/C，不计算 ASIL。
  - E 子任务只判断暴露度，不判断 S/C，不计算 ASIL。
  - C 子任务只判断可控性，不判断 S/E，不计算 ASIL。
  - FTTI 子任务只计算本批次的 FTTI，不涉及 SEC 评级。
- S/E/C/FTTI 子任务互相不共享推理上下文，只通过 `List_No` 对齐结果。
- Stage3B 总控 agent 收集 S/E/C/FTTI 结果，调用 `merge_sec_batches.py` 合并 SEC 记录和 FTTI，按 `List_No` 排序写入一个完整 `stage3b_<MF_ID>_sec.json`。

## 规则

- `sec_records` 数量必须等于 Stage 3A `scenarios` 数量。
- 按 `List_No` 与场景一一对应，并保持同一顺序。
- 每条记录必填：`List_No`、`E-解释`、`暴露频率'E'`、`有风险的人员`、`可能的后果('S'的理由)`、`Severity 'S'`、`C-解释`、`控制能力 'C'`、`结果ASIL`、`sec_reasoning`；`FTTI(ms)` 和 `备注` 可选。
- `sec_reasoning` 必须由三个子任务的推理合成，包含 `S评级推理`、`E评级推理`、`C评级推理`。
- 评级字段必须和推理字段一致：
  - `Severity 'S'` 等于 `sec_reasoning.S评级推理.S等级`
  - `暴露频率'E'` 等于 `sec_reasoning.E评级推理.E等级`
  - `控制能力 'C'` 等于 `sec_reasoning.C评级推理.C等级`
- `结果ASIL` 由 `sec-merge-safety.md` 的后缀求和规则计算；不要为了得到更高 ASIL 而夸大 S/E/C。
- 为该 MF 生成一个 `safety_goal` 和一个 `safe_state`，基于可信最高风险路径。

## 子 Agent 调用指示

**重要：Stage3B 总控必须使用 `Agent` 工具为每个批次和每个 SEC 维度启动独立 worker 子 agent。不要在当前上下文执行 S/E/C、Safety 或 FTTI 子任务；如果当前环境没有 `Agent` 工具，停止并报告无法满足真正子 agent 隔离要求。**

**重要路径说明：子 agent 运行在临时 worktree 中，必须使用绝对路径。**

项目根目录：通过 `bash pwd` 获取真实项目根目录（例如 `/home/test/projects/hara/hara-new/hara-mutiagent`）。

在构建子 agent prompt 时，必须：
1. 先运行 `bash pwd` 获取项目根目录 `PROJECT_ROOT`
2. 所有路径使用绝对路径：`$PROJECT_ROOT/output/...`、`$PROJECT_ROOT/skills/...`、`$PROJECT_ROOT/knowledge-base/...`
3. 不要使用相对路径 `output/`，否则会写入 worktree 目录

示例 prompt 格式：
```
prompt="项目根目录：$PROJECT_ROOT。执行 Stage3B-S 评级任务。批次上下文：$PROJECT_ROOT/output/<RUN_ID>_stage3b_<MF_ID>_batch01_context.json。读取 $PROJECT_ROOT/skills/hara-stage3b/references/sec-s-batch-prompt.md 和 $PROJECT_ROOT/knowledge-base/automotive/hara/common/04-risk_assessment-s.md。必须使用 Write 工具写入输出文件：$PROJECT_ROOT/output/<RUN_ID>_stage3b_<MF_ID>_batch01_s.json..."
```

**权限说明：子 agent 需要写入 output 目录的权限。在启动子 agent 前，请确保已批准写入权限。如果子 agent 报告权限被拒绝，请检查 `.claude/settings.json` 中是否设置了 `"allowAllWrite": true`。**

### 执行流程

```text
# === Step 1: 准备批次上下文 ===
# SEC 评级批次和 FTTI 批次使用相同的批次上下文
bash: python tools/hara/prepare_stage3_context.py sec-batches \
  --context output/<RUN_ID>_stage3_context_<MF_ID>.json \
  --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json \
  --out-dir output --batch-size 5

# === Step 2: 对每个批次，并行启动 S/E/C 三个独立子 agent ===
# 假设生成了 batch01, batch02 两个批次

# Batch 01: 并行启动 S/E/C 三个 worker 子任务
# 注意：子 agent 需要 Write 工具权限，请在执行时批准
Agent(
  subagent_type="claude",
  description="Stage3B-S 评级 batch01",
  prompt="执行 Stage3B-S 评级任务。你需要使用 Write 工具写入 output 目录。批次上下文：output/<RUN_ID>_stage3b_<MF_ID>_batch01_context.json。读取 skills/hara-stage3b/references/sec-s-batch-prompt.md 和 knowledge-base/automotive/hara/common/04-risk_assessment-s.md。必须使用 Write 工具写入输出文件：output/<RUN_ID>_stage3b_<MF_ID>_batch01_s.json（JSON 数组，UTF-8 无 BOM）。每项必须包含：List_No、有风险的人员、可能的后果('S'的理由)、Severity 'S'、S评级推理。如果 Write 权限被拒绝，请停止并请求用户批准。写入成功后返回文件路径。",
  run_in_background=true
)
Agent(
  subagent_type="claude",
  description="Stage3B-E 评级 batch01",
  prompt="执行 Stage3B-E 评级任务。你需要使用 Write 工具写入 output 目录。批次上下文：output/<RUN_ID>_stage3b_<MF_ID>_batch01_context.json。读取 skills/hara-stage3b/references/sec-e-batch-prompt.md 和 knowledge-base/automotive/hara/common/04-risk_assessment-e.md。必须使用 Write 工具写入输出文件：output/<RUN_ID>_stage3b_<MF_ID>_batch01_e.json（JSON 数组，UTF-8 无 BOM）。每项必须包含：List_No、E-解释、暴露频率'E'、E评级推理。如果 Write 权限被拒绝，请停止并请求用户批准。写入成功后返回文件路径。",
  run_in_background=true
)
Agent(
  subagent_type="claude",
  description="Stage3B-C 评级 batch01",
  prompt="执行 Stage3B-C 评级任务。你需要使用 Write 工具写入 output 目录。批次上下文：output/<RUN_ID>_stage3b_<MF_ID>_batch01_context.json。读取 skills/hara-stage3b/references/sec-c-batch-prompt.md 和 knowledge-base/automotive/hara/common/04-risk_assessment-c.md。必须使用 Write 工具写入输出文件：output/<RUN_ID>_stage3b_<MF_ID>_batch01_c.json（JSON 数组，UTF-8 无 BOM）。每项必须包含：List_No、C-解释、控制能力 'C'、C评级推理。如果 Write 权限被拒绝，请停止并请求用户批准。写入成功后返回文件路径。",
  run_in_background=true
)

# Batch 02: 同样并行启动 S/E/C 三个子任务
Agent(subagent_type="claude", description="Stage3B-S 评级 batch02", prompt="...", run_in_background=true) # S 评级 batch02 → output/<RUN_ID>_stage3b_<MF_ID>_batch02_s.json
Agent(subagent_type="claude", description="Stage3B-E 评级 batch02", prompt="...", run_in_background=true) # E 评级 batch02 → output/<RUN_ID>_stage3b_<MF_ID>_batch02_e.json
Agent(subagent_type="claude", description="Stage3B-C 评级 batch02", prompt="...", run_in_background=true) # C 评级 batch02 → output/<RUN_ID>_stage3b_<MF_ID>_batch02_c.json

# === Step 3: 启动 Safety 子 agent ===
# 注意：子 agent 需要 Write 工具权限，请在执行时批准
Agent(
  subagent_type="claude",
  description="Safety 生成",
  prompt="执行 Safety 生成任务。你需要使用 Write 工具写入 output 目录。输入：output/<RUN_ID>_stage3_context_<MF_ID>.json。读取 knowledge-base/automotive/hara/common/05-safety_goal.md。生成 safety_goal 和 safe_state。必须使用 Write 工具写入输出文件：output/<RUN_ID>_stage3b_<MF_ID>_safety.json。格式：{\"safety_goal\":\"...\",\"safe_state\":\"...\"}。如果 Write 权限被拒绝，请停止并请求用户批准。写入成功后返回文件路径。",
  run_in_background=true
)

# === Step 4: 启动 FTTI 子 agent（分批次并行） ===
# 对每个批次启动 FTTI 计算子任务
# 注意：子 agent 需要 Write 工具权限，请在执行时批准
Agent(
  subagent_type="claude",
  description="FTTI 计算 batch01",
  prompt="执行 FTTI 计算任务。你需要使用 Write 工具写入 output 目录。批次上下文：output/<RUN_ID>_stage3b_<MF_ID>_batch01_context.json。读取 knowledge-base/automotive/hara/common/06-ftti.md。对批次中每个场景计算 FTTI。必须使用 Write 工具写入输出文件：output/<RUN_ID>_stage3b_<MF_ID>_batch01_ftti.json（JSON 数组，UTF-8 无 BOM）。每项必须包含：List_No、FTTI(ms)、FTTI理由。如果 Write 权限被拒绝，请停止并请求用户批准。写入成功后返回文件路径。",
  run_in_background=true
)
Agent(
  subagent_type="claude",
  description="FTTI 计算 batch02",
  prompt="执行 FTTI 计算任务。你需要使用 Write 工具写入 output 目录。批次上下文：output/<RUN_ID>_stage3b_<MF_ID>_batch02_context.json。读取 knowledge-base/automotive/hara/common/06-ftti.md。对批次中每个场景计算 FTTI。必须使用 Write 工具写入输出文件：output/<RUN_ID>_stage3b_<MF_ID>_batch02_ftti.json（JSON 数组，UTF-8 无 BOM）。每项必须包含：List_No、FTTI(ms)、FTTI理由。如果 Write 权限被拒绝，请停止并请求用户批准。写入成功后返回文件路径。",
  run_in_background=true
)
# ... 其他批次类似

# === Step 5: 统一拼接所有文件 ===
bash: python tools/hara/merge_sec_batches.py \
  --s-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_s.json \
  --e-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_e.json \
  --c-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_c.json \
  --ftti-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_ftti.json \
  --safety output/<RUN_ID>_stage3b_<MF_ID>_safety.json \
  --output output/<RUN_ID>_stage3b_<MF_ID>_sec.json \
  --meta-mf-id <MF_ID> --meta-run-id <RUN_ID> \
  --cleanup

# === Step 6: 验证与合并 ===
bash: python tools/hara/check_stage_json.py --stage stage3b_raw --json output/<RUN_ID>_stage3b_<MF_ID>_sec.json
bash: python tools/hara/merge_stage3.py --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage3b output/<RUN_ID>_stage3b_<MF_ID>_sec.json --output output/<RUN_ID>_stage3_<MF_ID>_hara.json
```

### SEC 子任务输入输出规范

**重要：每个子任务必须将结果写入独立文件，返回文件路径，不在上下文中返回 JSON 数组。**

**S 子任务：**
- 输入：批次上下文 JSON + `sec-s-batch-prompt.md` + `04-risk_assessment-s.md`
- 输出文件：`output/<RUN_ID>_stage3b_<MF_ID>_<BATCH>_s.json`
- 文件内容：JSON 数组（UTF-8 编码，无 BOM）
- 每项包含：`List_No`、`有风险的人员`、`可能的后果('S'的理由)`、`Severity 'S'`、`S评级推理`
- **`有风险的人员`**：列出本场景中所有可能受影响的人员类别（如：驾驶员、乘客、行人、其他道路使用者等）
- **`可能的后果('S'的理由)` 格式要求**：
  1. **分别分析**：对 `有风险的人员` 中的每一类，分别说明其可能受到的伤害及其 S 等级判定
  2. **取最高等级**：基于上述分析，最终 `Severity 'S'` 取所有人员中的最高 S 等级
  3. **每个人员的分析格式**：
     - 人员类别 + 伤害描述 + S 等级定义解释 + 场景结合说明
  4. **最终结论**：明确说明"综合所有风险人员，最高 S 等级为 Sx"
- **`S评级推理` 格式**：对象包含 `S等级`、`S等级定义`、`本场景伤害分析`

**E 子任务：**
- 输入：批次上下文 JSON + `sec-e-batch-prompt.md` + `04-risk_assessment-e.md`
- 输出文件：`output/<RUN_ID>_stage3b_<MF_ID>_<BATCH>_e.json`
- 文件内容：JSON 数组（UTF-8 编码，无 BOM）
- 每项包含：`List_No`、`E-解释`、`暴露频率'E'`、`E评级推理`
- **`E-解释` 格式要求**：
  1. **定义解释**：引用 E0/E1/E2/E3/E4 的定义，说明所选等级的判定依据
  2. **场景结合**：结合本场景的暴露频率（道路类型、驾驶场景、工况条件），说明为何在该场景下适用此等级
- **`E评级推理` 格式**：对象包含 `E等级`、`E等级定义`、`本场景暴露分析`

**C 子任务：**
- 输入：批次上下文 JSON + `sec-c-batch-prompt.md` + `04-risk_assessment-c.md`
- 输出文件：`output/<RUN_ID>_stage3b_<MF_ID>_<BATCH>_c.json`
- 文件内容：JSON 数组（UTF-8 编码，无 BOM）
- 每项包含：`List_No`、`C-解释`、`控制能力 'C'`、`C评级推理`
- **`C-解释` 格式要求**：
  1. **定义解释**：引用 C0/C1/C2/C3 的定义，说明所选等级的判定依据
  2. **场景结合**：结合本场景的可控性因素（驾驶员状态、警告时间、操作空间等），说明为何在该场景下适用此等级
- **`C评级推理` 格式**：对象包含 `C等级`、`C等级定义`、`本场景可控性分析`

**FTTI 子任务：**
- 输入：批次上下文 JSON + `knowledge-base/automotive/hara/common/06-ftti.md`
- 输出文件：`output/<RUN_ID>_stage3b_<MF_ID>_<BATCH>_ftti.json`
- 文件内容：JSON 数组（UTF-8 编码，无 BOM）
- 每项包含：`List_No`、`FTTI(ms)`、`FTTI理由`
- **`FTTI(ms)` 格式要求**：数值字符串，单位毫秒
- **`FTTI理由` 格式要求**：说明 FTTI 计算依据（如危害发展时间、驾驶员反应时间等）

### 输出文件示例

**`batch01_s.json` 示例：**
```json
[
  {
    "List_No": 1,
    "有风险的人员": "驾驶员、乘客、后方车辆乘客",
    "可能的后果('S'的理由)": "1. 驾驶员：车辆高速碰撞可能导致胸部损伤和骨折，符合 S2 定义（可能造成严重伤害，需医疗处理但无生命危险）。2. 乘客：后排乘客未系安全带，撞击时可能造成头部重伤，符合 S3 定义（可能造成致命伤害）。3. 后方车辆乘客：追尾碰撞可能造成致命伤害，符合 S3 定义。综合所有风险人员，最高 S 等级为 S3。",
    "Severity 'S'": "S3",
    "S评级推理": {
      "S等级": "S3",
      "S等级定义": "可能造成致命伤害（有生命危险）",
      "本场景伤害分析": "高速状态下制动失效，导致追尾碰撞，驾驶员和乘客可能遭受致命伤害"
    }
  }
]
```

### 总控合并规则

**总控 agent 不手动合并 SEC 记录，统一使用 `merge_sec_batches.py` 脚本：**

1. 等待所有批次的 S/E/C 子任务全部完成，每个子任务返回文件路径
2. 调用 `merge_sec_batches.py` 脚本：
   - 传入所有批次文件路径
   - 脚本自动按 `List_No` 对齐 S/E/C 记录
   - 脚本自动计算 `结果ASIL`（S+E+C 后缀求和规则）
   - 脚本自动组装 `sec_reasoning`
   - `--cleanup` 参数自动删除分散的 batch 文件
3. 基于合并后的结果，生成 `safety_goal` 和 `safe_state`
4. 将 `safety_goal` 和 `safe_state` 添加到合并后的文件中
5. 最终输出必须严格符合 `references/json-contracts.md` 顶部的“完整输出 Schema（严格遵循）”。

### 重要约束

- **S/E/C 子任务必须完全独立**，不共享上下文，不互相参考
- **批次之间必须独立**，Batch 01 的 S 评级不影响 Batch 02
- **子任务必须输出文件**，不要在响应中返回 JSON 数组，只返回文件路径
- **总控只保留文件路径**，等待所有批次完成后用脚本合并
- **不要在当前上下文执行 SEC 评级或手动合并**，必须启动独立子 agent + 脚本合并
- **使用 `run_in_background=true` 并行启动多个子任务**，等待所有子任务完成后再合并
- **合并后自动删除分散文件**，保持 output 目录干净

## 验证

```text
python tools/hara/check_stage_json.py --stage stage3b_raw --json output/<RUN_ID>_stage3b_<MF_ID>_sec.json --mf-id <MF_ID> --min-scenarios 10 --max-scenarios 20
python tools/hara/merge_stage3.py --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage3b output/<RUN_ID>_stage3b_<MF_ID>_sec.json --output output/<RUN_ID>_stage3_<MF_ID>_hara.json
python tools/hara/check_stage_json.py --stage stage3 --json output/<RUN_ID>_stage3_<MF_ID>_hara.json --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --mf-id <MF_ID> --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
```

## 返回

返回 `status`、已处理的 `MF_ID`、场景数量、该 MF 最高 ASIL、输出文件，并说明下一步是否进入 Stage 3R。
