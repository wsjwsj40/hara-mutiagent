---
name: hara-stage3b
description: Stage 3B SEC 评级。用于基于一个 MF 的 Stage3A 场景生成 output/<RUN_ID>_stage3b_<MF_ID>_sec.json，包括 sec_records、safety_goal 和 safe_state。S/E/C/FTTI 应按批次拆分为隔离子任务；不要重新生成场景或修改 Stage3A 内容。
---

# Stage 3B：SEC 评级

## 文档分工

- 本文件：定义 Stage3B 的职责边界、上下文边界、执行流程和验证门禁。
- `references/json-contracts.md`：唯一输出结构契约，含最终文件和 S/E/C/FTTI 中间文件字段。
- `references/stage3b-sec-rating.md`：总控编排、批次拆分、子任务隔离策略。
- `references/sec-batch-prompt.md`：S/E/C/FTTI 子任务通用约束。
- `references/sec-s-batch-prompt.md`：S 严重度子任务提示词。
- `references/sec-e-batch-prompt.md`：E 暴露度子任务提示词。
- `references/sec-c-batch-prompt.md`：C 可控性子任务提示词。
- `references/sec-ftti-batch-prompt.md`：FTTI 子任务提示词。
- `references/sec-merge-safety.md`：S/E/C/FTTI 合并、ASIL 展示、安全目标和安全状态规则。

## 职责边界

Stage3B 只为一个 `MF_ID` 生成 SEC 增量文件。它不生成 Stage3A 场景，不修改 `scenario_reasoning` 或 `max_asil_planning`，不生成 Stage3 完整 HARA；完整 HARA 由 `merge_stage3.py` 合成。

## 输入输出

- 输入：`output/<RUN_ID>_stage3_context_<MF_ID>.json`
- 输入：`output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json`
- 中间输出：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_{s,e,c,ftti}.json`
- 中间输出：`output/<RUN_ID>_stage3b_<MF_ID>_safety.json`
- 最终输出：`output/<RUN_ID>_stage3b_<MF_ID>_sec.json`

每个 Stage3B worker 只处理一个 `MF_ID`。S/E/C/FTTI 子任务只处理一个 batch，batch 默认最多 5 条场景。

## 上下文边界

总控只读取当前 MF 的 Stage3 context、当前 MF 的 Stage3A 文件、本 skill 的契约/编排/合并文档，以及 ASIL、安全目标、FTTI 必要知识库。

S/E/C 子任务只读取自己的 batch context、对应 prompt 和对应风险评级知识库。不要让任何子任务同时读取 S/E/C 三类知识库，也不要让子任务计算 ASIL 或生成安全目标。

## 执行流程

1. 读取 `references/json-contracts.md`、`references/stage3b-sec-rating.md`、`references/sec-merge-safety.md`。
2. 切分 Stage3A 场景为 Stage3B batch context。
3. 对每个 batch 分别启动 S、E、C、FTTI 子任务；每个子任务写自己的 JSON 数组文件。
4. 单独生成 `safety_goal` 与 `safe_state` 到 safety 文件。
5. 使用 `merge_sec_batches.py` 合并所有中间文件；脚本只做拼接和确定性 `结果ASIL` 派生，不做质量校验。
6. 使用 `check_stage_json.py --stage stage3b --stage3a ...` 校验 Stage3A 对齐、S/E/C 一致性、ASIL、FTTI 和 safety。通过后进入 Stage3BR；Stage3A/3B 合并由 Stage3BR 通过后的编排器执行。

## 命令

```text
python tools/hara/prepare_stage3_context.py sec-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --prefix <RUN_ID> --out-dir output --batch-size 5

python tools/hara/merge_sec_batches.py --s-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_s.json --e-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_e.json --c-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_c.json --ftti-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_ftti.json --safety output/<RUN_ID>_stage3b_<MF_ID>_safety.json --output output/<RUN_ID>_stage3b_<MF_ID>_sec.json --meta-mf-id <MF_ID> --meta-run-id <RUN_ID>

python tools/hara/check_stage_json.py --stage stage3b --json output/<RUN_ID>_stage3b_<MF_ID>_sec.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --min-scenarios 10 --max-scenarios 20
```

## 返回

返回 `status`、`MF_ID`、场景数量、该 MF 最高 ASIL、Stage3B 输出文件，并说明是否进入 Stage3BR。
