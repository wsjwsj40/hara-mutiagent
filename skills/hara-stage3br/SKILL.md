---
name: hara-stage3br
description: Stage 3BR SEC 评审。用于在 Stage3B 生成后、Stage3A/3B 合并前评审单个 output/<RUN_ID>_stage3b_<MF_ID>_sec.json，检查 S/E/C 语义评级、sec_reasoning、FTTI、安全目标和安全状态。不要重新评审 Stage3A 场景生成质量。
---

# Stage 3BR：SEC 评审

## 文档分工

- 本文件：定义 Stage3BR 职责、上下文边界、流程和门禁。
- `references/stage3b-review.md`：评审结构和检查点。
- `references/review-batch-prompt.md`：批次子任务提示词。
- `skills/hara-stage3ar/references/stage3-risk-judgment-rules.md`：仅在 S/E/C 边界或运动风险判断有争议时读取。

## 职责边界

Stage3BR 只评审 Stage3B 的 SEC、FTTI、`safety_goal` 和 `safe_state`。不要重新评审 Stage3A 场景质量；如发现场景本身不成立，退回 Stage3AR/Stage3A。

## 输入输出

- 输入：`output/<RUN_ID>_stage3_context_<MF_ID>.json`
- 输入：`output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json`
- 输入：`output/<RUN_ID>_stage3b_<MF_ID>_sec.json`
- 批次上下文：`output/<RUN_ID>_stage3br_<MF_ID>_batchXX_context.json`
- 输出：`output/<RUN_ID>_stage3b_<MF_ID>_review.json`

Review 文件作为人工审查留痕，不运行严格 schema check。机器门禁使用 `check_stage_json.py --stage stage3b`。

## 执行流程

1. 先运行 Stage3B 机器校验，确认 Stage3A 对齐、S/E/C 一致性、ASIL、FTTI 和 safety 基础结构通过。
2. 生成 Stage3BR 批次上下文，每批最多 5 条 Stage3A 场景与 Stage3B SEC 配对记录。
3. 对每个 batch 启动独立评审 worker，只读取本批 context 和 `references/review-batch-prompt.md`。
4. 合并批次 review 数组，写入 `stage3b_<MF_ID>_review.json`。
5. 如发现 S/E/C 错误，优先重跑对应 Stage3B 维度 batch，再重新 `merge_sec_batches.py` 和 `--stage stage3b`。

## 命令

```text
python tools/hara/check_stage_json.py --stage stage3b --json output/<RUN_ID>_stage3b_<MF_ID>_sec.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --min-scenarios 10 --max-scenarios 20

python tools/hara/prepare_stage3_context.py stage3b-review-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage3b output/<RUN_ID>_stage3b_<MF_ID>_sec.json --mf-id <MF_ID> --prefix <RUN_ID> --out-dir output --batch-size 5
```

## 返回

返回 `passed/failed`、`MF_ID`、场景数量、最高 ASIL、问题数量、修正内容、是否允许 Stage3A/3B 合并。
