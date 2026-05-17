---
name: hara-stage2r
description: Stage 2R 整车危害语义评审。用于在 Stage 2 单功能片段机器校验通过后，按 Function_ID 独立复核 output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json 的危害映射、hazard_reasoning、追溯字段和故障描述边界。最终 Stage2 合并必须在所有 Stage2R 单片评审通过后执行。
---

# Stage 2R：整车危害语义评审

## 文档分工

- 本文件：定义 Stage2R 的职责、上下文边界、执行流程和合并门禁。
- `references/stage2-review.md`：定义危害映射评审方法和 review 留痕建议。
- Review JSON 只做人工留痕，不作为 Stage3 结构化输入，不做严格 schema 校验。

## 职责边界

Stage2R 只评审当前 `Function_ID` 的 Stage2 单功能片段，重点是危害映射是否准确、`hazard_reasoning` 是否可信、`故障描述` 是否可供 Stage3 使用。

不要读取最终 Stage2 合并文件，不生成 Stage3 场景，不做 SEC/ASIL/安全目标。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`
  - `output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json`
  - 可选：`output/<RUN_ID>_stage1_context_<Function_ID>.json`
- 单功能 review：`output/<RUN_ID>_stage2_<Function_ID>_review.json`
- 如需修正，直接更新对应 Stage2 单功能片段。
- 总 review：由 `tools/hara/merge_stage2_review.py --stage0 <stage0_json>` 合并为 `output/<RUN_ID>_stage2_review.json`。

## 执行流程

1. 确认当前 Stage2 片段已通过机器校验：

```text
python tools/hara/check_stage_json.py --stage stage2_slice --json output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json --stage1 output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json --function-id <Function_ID> --fix
```

2. 按 `references/stage2-review.md` 复核危害映射、推理链、原子性和 Stage3 可用性。
3. 只修正证据充分的语义问题；机械问题回到 `stage2_slice --fix`。
4. 修改 Stage2 单功能片段后，重新运行 `stage2_slice --fix`。
5. 写入 review 留痕 JSON，至少能让合并脚本识别当前 `Function_ID`。

## 合并门禁

所有 Function_ID 的 Stage2R 通过后，才执行：

```text
python tools/hara/merge_stage2.py --stage0 output/<RUN_ID>_stage0_function_mapping.json --input-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage2_mf_vehicle_hazards.json
python tools/hara/check_stage_json.py --stage stage2 --json output/<RUN_ID>_stage2_mf_vehicle_hazards.json --stage1 output/<RUN_ID>_stage1_derive_mf.json --fix
python tools/hara/merge_stage2_review.py --input-dir output --stage0 output/<RUN_ID>_stage0_function_mapping.json --prefix <RUN_ID> --out output/<RUN_ID>_stage2_review.json
```

## 返回

返回 `passed` 或 `failed`、`Function_ID`、修正摘要、review 文件路径，以及该功能片段是否允许进入最终合并。
