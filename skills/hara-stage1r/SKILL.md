---
name: hara-stage1r
description: Stage 1R 功能故障语义评审。用于在 Stage 1 单功能片段机器校验通过后，按 Function_ID 独立复核 output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json 的故障适用性、nan 判断、遗漏的安全相关故障类型和故障描述边界。review 文件只作为人工审查依据，不作为后续结构化输入。
---

# Stage 1R：功能故障语义评审

## 文档分工

- 本文件：定义 Stage1R 的职责边界、输入输出、执行流程和门禁。
- `references/stage1-review.md`：定义语义评审方法、重点复核项和 review 留痕建议。
- 不再为 Stage1R review 文件维护单独 schema；它不是 Stage2 的结构化输入，不运行 `check_stage_json.py --stage stage1_review`。

## 职责边界

Stage1R 只做单功能语义评审：判断 Stage1 对当前 `Function_ID` 的故障适用性、`nan` 结论、故障描述边界和遗漏风险是否合理。

不要做这些事：

- 不读取完整 Stage1 合并文件。
- 不生成 Stage2 整车危害。
- 不重复做 schema、行数、字段完整性等机械校验。
- 不把 review JSON 当作硬 schema 产物。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage0_function_mapping.json`
  - `output/<RUN_ID>_stage1_context_<Function_ID>.json`
  - `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`
- 单功能 review 留痕：`output/<RUN_ID>_stage1_<Function_ID>_review.json`
- 如需修正，直接更新对应 Stage1 单功能片段。
- 总 review：由 `tools/hara/merge_stage1_review.py --stage0 <stage0_json>` 合并为 `output/<RUN_ID>_stage1_review.json`。合并脚本只检查 review 文件可解析、可识别 `Function_ID`、覆盖 Stage0 全部功能。

## 上下文加载

1. 读取当前 Stage1 context 和当前 Stage1 单功能片段。
2. 只使用当前功能对应的 Stage0 `detail_text`。
3. 读取 `references/stage1-review.md` 获取语义评审方法。
4. 只有在故障类型定义不清时，才加载 `knowledge-base/automotive/hara/common/02-malfuntioning_behavior.md`。

## 执行流程

1. 确认当前片段已通过：

```text
python tools/hara/check_stage_json.py --stage stage1_slice --json output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json --stage0 output/<RUN_ID>_stage0_function_mapping.json --function-id <Function_ID> --fix
```

2. 按 `references/stage1-review.md` 复核 `nan`、`过小`、`方向错误`、边界混入、内部原因和整车危害前置等问题。
3. 只修正证据充分的语义问题；机械一致性问题交给 `check_stage_json.py --fix`。
4. 如修改 Stage1 单功能片段，重新运行 `stage1_slice --fix`。
5. 写入 review 留痕 JSON，至少能让合并脚本识别当前 `Function_ID`。
6. 全部 Function_ID 评审完成后，由编排器合并最终 Stage1 和 Stage1R review。

## 合并门禁

```text
python tools/hara/merge_stage1.py --stage0 output/<RUN_ID>_stage0_function_mapping.json --input-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage1_derive_mf.json
python tools/hara/check_stage_json.py --stage stage1 --json output/<RUN_ID>_stage1_derive_mf.json --stage0 output/<RUN_ID>_stage0_function_mapping.json --fix
python tools/hara/merge_stage1_review.py --input-dir output --stage0 output/<RUN_ID>_stage0_function_mapping.json --prefix <RUN_ID> --out output/<RUN_ID>_stage1_review.json
```

## 返回

返回 `passed` 或 `failed`、`Function_ID`、修正摘要、review 文件路径，以及该功能片段是否允许进入最终合并。
