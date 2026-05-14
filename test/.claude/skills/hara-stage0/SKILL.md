---
name: hara-stage0
description: Stage 0 功能提取。用于从功能文档、source_extraction JSON 或用户提供的功能文本中提取功能列表，生成 Function_ID、功能名称、detail_text 和系统线索。当需要启动 HARA 分析或重新生成 output/<RUN_ID>_stage0_function_mapping.json 时使用。不要用于故障、危害、SEC、ASIL 或安全目标分析。
---

# Stage 0：功能提取

## 职责边界

只提取功能。不要读取 HARA 风险知识库，不要推导功能故障，不要生成整车危害。保留源文档含义，让下游阶段能够基于 `detail_text` 推理。

## 输入输出

- 输入：功能文档路径、`output/<RUN_ID>_source_extraction.json` 或直接粘贴的功能文本。
- 输出：`output/<RUN_ID>_stage0_function_mapping.json`。
- 必读契约：`references/json-contracts.md`。

## 上下文加载

1. 读取源文件或 source-extraction 结果。
2. 读取 `references/json-contracts.md`，确认必填 JSON 结构。
3. 只有在需要判断章节层级、功能边界或示例时，才读取 `references/stage0-function-extraction.md`。
4. 本阶段不要读取 `knowledge-base/automotive/hara`。

## 规则

- 只提取独立功能单元。
- 将“工作电源挡位”“功能逻辑”“触发条件”“边界条件”等子章节合并进父功能的 `detail_text`，不要作为独立功能。
- 如果源文档存在真实功能分解，优先提取叶子层级功能。
- `Function_ID` 连续编号：`F001`、`F002`、`F003`，不得跳号。
- `detail_text` 必须包含源文档支持的完整运行背景：触发、输入、输出、前置条件、状态转换、限制、排除条件和备注。
- 尽量保留原始技术表述，不要把运行条件过度摘要掉。
- 在 `meta` 或行级备注中记录系统/功能域线索，供后续阶段加载系统知识库。

## 执行流程

1. 解析源文档结构，定位候选功能标题。
2. 将每个功能的描述性子章节合并到 `detail_text`。
3. 先读取 `references/json-contracts.md` 顶部的“完整输出 Schema（严格遵循）”。
4. 严格按 Schema 构建 `meta`、`function_mapping`、`review_log`；字段名、顶层 key、数组/对象结构不要改名或增包一层。
5. 只写 UTF-8 JSON，不输出 Markdown 包裹。
6. 返回前运行验证并修正结构问题；验证失败时修 JSON 文件，不用解释代替修复。

## 验证

```text
python tools/hara/check_stage_json.py --stage stage0 --json output/<RUN_ID>_stage0_function_mapping.json
```

## 返回

返回 `status`、`function_count`、识别到的 `system`、`output_file`，并说明下一步是否进入 Stage 0R。
