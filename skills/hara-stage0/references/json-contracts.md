# HARA JSON 契约 - Stage 0

所有阶段文件必须是 UTF-8 JSON object。不要输出 Markdown 表格、代码围栏、额外说明文本或数组作为顶层结构。

## 本阶段文件

文件：`output/<run_id>_stage0_function_mapping.json`

只允许顶层 key：`meta`、`function_mapping`、`review_log`。

### function_mapping 字段

- `Function_ID`
- `extracted_function_name`
- `function_category`
- `remark`
- `function_description`
- `source_table`
- `source_evidence`
- `section_id`
- `section_title`
- `detail_section_ids`
- `detail_text`
- `detail_evidence_blocks`
- `is_hara_relevant`
- `exclude_reason`
- `system_hint`
- `matched_system`
- `match_confidence`
- `match_reason`
- `conflict_notes`
