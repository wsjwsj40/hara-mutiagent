# HARA JSON 契约 - Stage 0

所有阶段文件必须是 UTF-8 JSON object。不要输出 Markdown 表格、代码围栏、额外说明文本或数组作为顶层结构。

## 完整输出 Schema（严格遵循）

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "stage": "stage0",
    "generated_at": "ISO时间戳",
    "source_file": "<输入文件路径或direct_text>",
    "system": "<识别到的系统或unknown>",
    "knowledge_files_used": []
  },
  "function_mapping": [
    {
      "Function_ID": "F001",
      "extracted_function_name": "<源文档中的功能名称>",
      "function_category": "<功能类别>",
      "remark": "<源文档备注或空字符串>",
      "function_description": "<功能摘要>",
      "source_table": "<来源表格/章节或空字符串>",
      "source_evidence": "<直接证据文本>",
      "section_id": "<主章节号>",
      "section_title": "<主章节标题>",
      "detail_section_ids": [
        "<绑定到该功能的详细章节号>"
      ],
      "detail_text": "<支持下游推理的完整功能细节>",
      "detail_evidence_blocks": [
        "<证据块或引用>"
      ],
      "is_hara_relevant": true,
      "exclude_reason": "",
      "system_hint": "<源文档中的系统线索>",
      "matched_system": "<匹配到的系统或unknown>",
      "match_confidence": "high/medium/low",
      "match_reason": "<匹配理由>",
      "conflict_notes": ""
    }
  ],
  "review_log": []
}
```

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
