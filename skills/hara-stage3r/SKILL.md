---
name: hara-stage3r
description: Stage 3R HARA 场景评审。用于评审单个合并后的 output/<RUN_ID>_stage3_<MF_ID>_hara.json，检查场景质量、scenario_reasoning、SEC 评级正确性、max_asil_planning 覆盖、安全目标/安全状态质量，以及 ASIL 同步前的逐场景评审记录。
---

# Stage 3R：HARA 场景评审

## 职责边界

评审单个 `MF_ID` 的合并 Stage 3 HARA 文件。不要用汇总评审替代逐场景评审。除非修正必须重新生成，否则不要重跑 Stage 3A 或 Stage 3B。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage3_context_<MF_ID>.json`
  - `output/<RUN_ID>_stage3_<MF_ID>_hara.json`
  - 可选批次上下文：`output/<RUN_ID>_stage3r_<MF_ID>_batchXX_context.json`
- 输出：`output/<RUN_ID>_stage3_<MF_ID>_review.json`；如需修正，同时更新 HARA JSON。

## 上下文加载

1. 读取当前 MF 的 `output/<RUN_ID>_stage3_context_<MF_ID>.json`。
2. 读取单个 `MF_ID` 的合并 Stage 3 HARA JSON。
3. 调用 `prepare_stage3_context.py review-batches` 生成每批最多 5 条 HARA 记录的评审批次上下文。
4. 读取 `references/stage3-review.md`，确认必需 review 结构。
5. 只有在运动方向、风险对象、S/E/C 边界或场景合理性存在争议时，才读取 `references/stage3-risk-judgment-rules.md`。
6. 只按争议类型读取拆分后的风险知识库：S 争议读 `04-risk_assessment-s.md`，E 争议读 `04-risk_assessment-e.md`，C 争议读 `04-risk_assessment-c.md`，ASIL 算术争议读 `04-risk_assessment-asil.md`；安全目标争议再读 `05-safety_goal.md`。
7. 默认不要读取 Stage 2；Stage3 context 与合并 HARA 已包含必要追溯信息。只有可追溯性存疑时才读取 Stage 2。

## 子 Agent 边界

- 本 skill 由编排器作为独立子 agent 调用，负责当前 MF 的 Stage3R 总控。
- 当前 MF 内再为每个 `stage3r_<MF_ID>_batchXX_context.json` 创建独立评审子任务。
- 批次子任务提示词使用 `references/review-batch-prompt.md`，并把对应批次上下文作为唯一 HARA 输入。
- 批次子任务只输出本批 `per_scenario_reviews` JSON 数组；总控 agent 合并所有批次后写 review JSON。

## 检查项

- 场景数量为 10-20。
- `max_asil_planning` 存在，并覆盖可信高风险路径。
- 场景枚举字段符合 `operation_scenarios.json`。
- 场景真实、不重复，并位于功能运行域内。
- `scenario_reasoning` 支持危害事件和条件相关性判断。
- S/E/C 评级引用合适规则，并与 `sec_reasoning` 一致。
- `结果ASIL` 计算正确。
- 运动方向、道路条件、风险对象位置和驾驶员是否在车上保持逻辑一致。
- `safety_goal` 对应该 MF 危害和最高风险场景；`safe_state` 能支持实现安全目标。

## 执行流程

1. 先验证合并后的 Stage 3。
2. 读取 Stage3 context，评审 `max_asil_planning` 的总体覆盖方向。
3. 生成评审批次上下文，每批最多 5 条 HARA 记录。
4. 对每个批次启动独立评审子任务，输出本批 `per_scenario_reviews`。
5. 合并所有批次结论，修正明确的结构、ASIL 算术、枚举或推理一致性问题。
6. 写入包含 `overall_result`、`issues`、`fixes` 和逐场景结论的 review JSON。

## 验证

```text
python tools/hara/prepare_stage3_context.py review-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3 output/<RUN_ID>_stage3_<MF_ID>_hara.json --out-dir output --batch-size 5
python tools/hara/check_stage_json.py --stage stage3 --json output/<RUN_ID>_stage3_<MF_ID>_hara.json --mf-id <MF_ID> --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
python tools/hara/check_stage_json.py --stage stage3_review --json output/<RUN_ID>_stage3_<MF_ID>_review.json --hara output/<RUN_ID>_stage3_<MF_ID>_hara.json --mf-id <MF_ID>
```

## 返回

返回 `passed` 或 `failed`、`MF_ID`、场景数量、最高 ASIL、问题数量、修正内容，以及是否允许 ASIL 同步。
