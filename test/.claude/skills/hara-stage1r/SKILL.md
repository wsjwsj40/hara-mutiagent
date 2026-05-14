---
name: hara-stage1r
description: Stage 1R 功能故障评审。用于在进入 Stage 2 前，基于 Stage 0 detail_text 评审 output/<RUN_ID>_stage1_derive_mf.json，重点检查 nan 判断、field_reasoning 一致性、遗漏的安全相关故障类型、行数和故障描述质量。
---

# Stage 1R：功能故障评审

## 职责边界

评审并在必要时修正 Stage 1 功能故障推导。不要生成 Stage 2 整车危害。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage0_function_mapping.json`
  - `output/<RUN_ID>_stage1_derive_mf.json`
- 输出：`output/<RUN_ID>_stage1_review.json`；如需修正，同时更新 Stage 1 JSON。

## 上下文加载

1. 读取 Stage 1 JSON。
2. 只读取需要复核的 Stage 0 `detail_text` 行。
3. 读取 `references/stage1-review.md`，确认详细检查项。
4. 只有在故障类型定义不清时，才加载 `knowledge-base/automotive/hara/common/02-malfuntioning_behavior.md`。

## 检查项

- 行数等于 Stage 0 功能数。
- 每个功能恰好有一行 `derive_mf`。
- 每个故障字段都有对应的 `field_reasoning`。
- `field_reasoning.是否有安全风险` 与可见字段值一致：
  - `是` 表示必须是具体描述，不能是 `nan`。
  - `否` 表示必须是 `nan`，且要说明为什么不适用。
- 描述必须是功能边界内的具体异常行为。
- 保持、制动、保护、力、压力、扭矩类功能不能遗漏安全相关的 `过小`。
- 方向性或二元状态功能不能遗漏合理的 `方向错误`。

## 执行流程

1. 先验证结构和数量。
2. 优先评审高风险或可疑行，再评审低风险行。
3. 对缺少具体“不适用”理由的 `nan` 字段重新推理。
4. 只修正证据充分的不一致。
5. 按 `references/stage1-review.md` 中的“输出 Schema（严格遵循）”写入 review JSON；字段名、顶层 key、数组/对象结构不要改名或增包一层。
6. 如果修正了 Stage 1 JSON，重新运行 Stage 1 验证并确认通过。

## 验证

```text
python tools/hara/check_stage_json.py --stage stage1 --json output/<RUN_ID>_stage1_derive_mf.json --stage0 output/<RUN_ID>_stage0_function_mapping.json --fix
```

## 返回

返回 `passed` 或 `failed`、问题数量、修正内容、评审文件路径，以及是否允许进入 Stage 2。
