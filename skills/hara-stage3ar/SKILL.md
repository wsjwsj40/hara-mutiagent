---
name: hara-stage3ar
description: Stage 3AR 场景评审。用于在 Stage3A 生成后、Stage3B 评级前评审单个 output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json，检查 max_asil_planning、场景真实性/独立性、运行域一致性、危害事件逻辑和 scenario_reasoning。不要判断 S/E/C、ASIL、FTTI、安全目标或安全状态。
---

# Stage 3AR：场景评审

## 文档分工

- 本文件：定义 Stage3AR 职责、上下文边界、流程和门禁。
- `references/stage3a-review.md`：评审结构和检查点。
- `references/review-batch-prompt.md`：批次子任务提示词。
- `references/stage3-risk-judgment-rules.md`：仅在运动逻辑、风险对象或场景独立性有争议时读取。

## 职责边界

Stage3AR 只评审 Stage3A 的场景和危害事件。不要评价 S/E/C、ASIL、FTTI、安全目标或安全状态。发现问题时修正 Stage3A 文件或退回 Stage3A worker 重做；通过后才允许进入 Stage3B。

## 输入输出

- 输入：`output/<RUN_ID>_stage3_context_<MF_ID>.json`
- 输入：`output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json`
- 批次上下文：`output/<RUN_ID>_stage3ar_<MF_ID>_batchXX_context.json`
- 输出：`output/<RUN_ID>_stage3a_<MF_ID>_review.json`

Review 文件作为人工审查留痕，不运行严格 schema check。机器门禁使用 `check_stage_json.py --stage stage3a`。

## 执行流程

1. 先运行 Stage3A 机器校验。
2. 生成 Stage3AR 批次上下文，每批最多 5 条场景。
3. 对每个 batch 启动独立评审 worker，只读取本批 context 和 `references/review-batch-prompt.md`。
4. 合并批次 review 数组，写入 `stage3a_<MF_ID>_review.json`。
5. 如修正 Stage3A 文件，重新运行 `--stage stage3a`，再重做相关 Stage3AR 批次。

## 命令

```text
python tools/hara/check_stage_json.py --stage stage3a --json output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --mf-id <MF_ID> --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix

python tools/hara/prepare_stage3_context.py stage3a-review-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --prefix <RUN_ID> --out-dir output --batch-size 5
```

## 返回

返回 `passed/failed`、`MF_ID`、场景数量、问题数量、修正内容、是否允许进入 Stage3B。
