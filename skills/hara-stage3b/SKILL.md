---
name: hara-stage3b
description: Stage 3B SEC 评级。用于对 Stage 3A 场景进行 S/E/C 分维度评级，并写入 output/<RUN_ID>_stage3b_<MF_ID>_sec.json，包括 sec_records、sec_reasoning、safety_goal 和 safe_state。只生成 SEC 增量字段供后续合并；不要重新生成场景或修改 Stage 3A 内容。
---

# Stage 3B：SEC 评级

## 职责边界

对当前 MF 的 Stage 3A 场景进行 S/E/C 评级。不要修改 Stage 3A 的场景字段、`scenario_reasoning` 或 `max_asil_planning`。只输出 Stage 3B 增量文件；完整 HARA 文件由 `merge_stage3.py` 生成。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage3_context_<MF_ID>.json`
  - `output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json`
  - 可选批次上下文：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_context.json`
- 输出：`output/<RUN_ID>_stage3b_<MF_ID>_sec.json`。
- 结构契约：`references/json-contracts.md`。
- 总控导航：`references/stage3b-sec-rating.md`。

## 上下文加载

总控 agent 只加载：

1. 当前 MF 的 Stage3 context。
2. 当前 MF 的 Stage 3A JSON；不要读取其他 MF。
3. `references/json-contracts.md`。
4. `references/stage3b-sec-rating.md`。
5. `references/sec-batch-prompt.md`。
6. `references/sec-merge-safety.md`。
7. ASIL 计算知识库：`knowledge-base/automotive/hara/common/04-risk_assessment-asil.md`。

S/E/C 子任务只加载自己的批次提示词和自己的知识库：

- S 子任务：`sec-s-batch-prompt.md` + `04-risk_assessment-s.md`
- E 子任务：`sec-e-batch-prompt.md` + `04-risk_assessment-e.md`
- C 子任务：`sec-c-batch-prompt.md` + `04-risk_assessment-c.md`

不要把 `04-risk_assessment.md` 索引当作规则正文放进上下文；按维度读取拆分后的知识库文件。

## 子 Agent 边界

- 本 skill 由编排器作为独立子 agent 调用，负责当前 MF 的 Stage3B 总控。
- 当前 MF 内，每个 `stage3b_<MF_ID>_batchXX_context.json` 拆成三个独立子任务：
  - S 子任务只判断严重度，不判断 E/C，不计算 ASIL。
  - E 子任务只判断暴露度，不判断 S/C，不计算 ASIL。
  - C 子任务只判断可控性，不判断 S/E，不计算 ASIL。
- S/E/C 子任务互相不共享推理上下文，只通过 `List_No` 对齐结果。
- Stage3B 总控 agent 收集 S/E/C 三类结果，计算 `结果ASIL`，组装 `sec_reasoning`，按 `List_No` 排序写入一个完整 `stage3b_<MF_ID>_sec.json`。

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

## 执行流程

1. 读取 Stage3 context 和 Stage3A，确认场景数量为 10-20。
2. 生成批次上下文，每批最多 5 条场景：

```text
python tools/hara/prepare_stage3_context.py sec-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --out-dir output --batch-size 5
```

3. 对每个批次分别启动 S/E/C 三个独立子任务。
4. 每批完成后立即按 `List_No` 合并三类 JSON 数组，计算 `结果ASIL`，形成本批 `sec_records`。
5. 不要把批次子任务的完整推理草稿保留在总控上下文；只保留合成后的结构化结果。
6. 所有批次完成后，基于该 MF 的最高可信风险路径补充 `safety_goal` 和 `safe_state`。
7. 只写 UTF-8 JSON，不输出 Markdown 包裹。
8. 使用 `stage3b_raw` 验证，再与 Stage 3A 合并并验证完整 Stage 3。

## 验证

```text
python tools/hara/check_stage_json.py --stage stage3b_raw --json output/<RUN_ID>_stage3b_<MF_ID>_sec.json --mf-id <MF_ID> --min-scenarios 10 --max-scenarios 20
python tools/hara/merge_stage3.py --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage3b output/<RUN_ID>_stage3b_<MF_ID>_sec.json --output output/<RUN_ID>_stage3_<MF_ID>_hara.json
python tools/hara/check_stage_json.py --stage stage3 --json output/<RUN_ID>_stage3_<MF_ID>_hara.json --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --mf-id <MF_ID> --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
```

## 返回

返回 `status`、已处理的 `MF_ID`、场景数量、该 MF 最高 ASIL、输出文件，并说明下一步是否进入 Stage 3R。
