---
name: hara-stage4r
description: Stage 4R SG_Sum 评审。用于基于所有 Stage 3 HARA 文件评审 output/<RUN_ID>_stage4_sg_sum.json，检查最高 ASIL 一致性、QM 过滤、MF 覆盖、安全目标质量、安全状态质量和最终合并导出准备情况。
---

# Stage 4R：SG_Sum 评审

## 职责边界

评审 Stage 4 输出和最终合并导出准备情况。除非生成工具不可用或输出结构明显错误，否则不要手工重建 SG_Sum。

## 输入输出

- 输入：
  - `output/<RUN_ID>_stage4_sg_sum.json`
  - 所有 `output/<RUN_ID>_stage3_<MF_ID>_hara.json` 文件
- 输出：`output/<RUN_ID>_stage4_review.json`；如需修正，同时更新 Stage 4 JSON。

## 上下文加载

1. 读取 Stage 4 JSON。
2. 使用工具或定向 JSON 查询，从 Stage 3 文件中提取每个 MF 的最高 ASIL；不要把所有 HARA 行粘贴进对话上下文。
3. 读取 `references/stage4-review.md`，确认评审标准。
4. 只有在安全目标表述存疑时，才加载 `knowledge-base/automotive/hara/common/05-safety_goal.md`。

## 检查项

- 每个非 QM 的 MF 都出现在 SG_Sum 中。
- 最高 ASIL 为 QM 的 MF 不出现在 SG_Sum 中。
- 每个 `ASIL Level` 等于该 MF HARA 行中的最高 ASIL。
- 安全目标清晰、可验证，并与危害关联。
- 安全状态能够合理实现安全目标。
- `SG_No` 连续，且 MF 没有重复。

## 执行流程

1. 验证 Stage 4。
2. 将 SG_Sum 与 Stage 3 文件中的最高 ASIL 证据对照。
3. 修正明确的 ASIL 不一致、重复行、未知 MF 或 QM 泄漏。
4. 按 `references/stage4-review.md` 中的“输出 Schema（严格遵循）”写入 review JSON；字段名、顶层 key、数组/对象结构不要改名或增包一层。
5. 如果修正了 Stage 4 JSON，重新运行 Stage 4 验证并确认通过。

## 命令

```text
python tools/hara/check_stage_json.py --stage stage4 --json output/<RUN_ID>_stage4_sg_sum.json --hara output/<RUN_ID>_stage3_<MF_ID>_hara.json --fix
```

## 返回

返回 `passed` 或 `failed`、`total_sg`、问题数量、修正内容，以及是否允许最终合并导出。
