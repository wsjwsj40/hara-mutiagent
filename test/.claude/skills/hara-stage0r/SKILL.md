---
name: hara-stage0r
description: Stage 0R 功能提取评审。用于在进入 Stage 1 前评审 output/<RUN_ID>_stage0_function_mapping.json 的完整性、功能边界准确性、子章节误提取、Function_ID 连续性、detail_text 质量和系统识别。
---

# Stage 0R：功能提取评审

## 职责边界

评审并在必要时修正 Stage 0。不要推导功能故障或整车危害。

## 输入输出

- 输入：`output/<RUN_ID>_stage0_function_mapping.json`。
- 可选输入：原始源文档或 `output/<RUN_ID>_source_extraction.json`。
- 输出：`output/<RUN_ID>_stage0_review.json`；如需修正，同时更新 Stage 0 JSON。

## 上下文加载

1. 读取 Stage 0 JSON。
2. 只有在检查遗漏或章节边界时，才读取源文档提取结果。
3. 读取 `references/stage0-review.md`，确认详细评审标准。
4. 不要加载 HARA 风险知识库。

## 检查项

- 完整性：源文档中的重要功能没有遗漏。
- 边界：子章节没有被误提取为独立功能。
- 编号：`Function_ID` 连续且唯一。
- 细节：`detail_text` 足够支持 Stage 1 故障推理。
- 系统线索：系统/功能域识别存在且合理。

## 执行流程

1. 如有源文档，比较 Stage 0 行与源文档结构。
2. 用行号或功能引用记录问题。
3. 只修正明确的提取错误或结构契约问题。
4. 按 `references/stage0-review.md` 中的“输出 Schema（严格遵循）”写入 review JSON；字段名、顶层 key、数组/对象结构不要改名或增包一层。
5. 如果修正了 Stage 0 JSON，重新运行 Stage 0 验证并确认通过。

## 返回

返回 `passed` 或 `failed`、问题数量、修正内容、评审文件路径，以及是否允许进入 Stage 1。
