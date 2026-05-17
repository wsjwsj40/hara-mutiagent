# HARA JSON 契约 - Stage 1

所有阶段文件必须是 UTF-8 JSON object。不要输出 Markdown 表格、代码围栏、额外说明文本或数组作为顶层结构。

## 完整输出 Schema（严格遵循）

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "stage": "stage1",
    "generated_at": "ISO时间戳",
    "source_file": "output/<RUN_ID>_stage0_function_mapping.json",
    "knowledge_files_used": []
  },
  "derive_mf": [
    {
      "No.": 1,
      "子功能": "<Stage0功能名称>",
      "功能丧失": "<具体故障描述或nan>",
      "过大": "<具体故障描述或nan>",
      "过早": "<具体故障描述或nan>",
      "过小": "<具体故障描述或nan>",
      "过晚": "<具体故障描述或nan>",
      "非预期激活": "<具体故障描述或nan>",
      "卡滞": "<具体故障描述或nan>",
      "方向错误": "<具体故障描述或nan>"
    }
  ],
  "field_reasoning": [
    {
      "row": 1,
      "子功能": "<Stage0功能名称>",
      "字段推理": [
        {
          "字段": "功能丧失",
          "推理": {
            "功能输出": "<该功能的核心输出/状态/命令>",
            "异常情况": "<该故障类型下的异常>",
            "后果": "<可追溯的人身伤害风险或不适用理由>",
            "是否有安全风险": "是/否"
          }
        }
      ]
    }
  ],
  "knowledge_evidence": [
    {
      "source": "<实际读取的知识库或参考文件>",
      "used_for": "<使用目的>"
    }
  ],
  "review_log": []
}
```

## 本阶段文件

文件：`output/<run_id>_stage1_derive_mf.json`

只允许顶层 key：`meta`、`derive_mf`、`review_log`、`knowledge_evidence`、`field_reasoning`。

## 单功能片段文件

文件：`output/<run_id>_stage1_<Function_ID>_derive_mf.json`

单功能片段复用同一顶层结构和行结构，但必须满足：

- `meta.stage` 为 `stage1_slice`。
- `meta.function_id` 为当前 `Function_ID`。
- `derive_mf` 只能有 1 行，`No.` 为 `1`。
- `field_reasoning` 只能有 1 行，`row` 为 `1`。
- 单片校验命令使用 `check_stage_json.py --stage stage1_slice --function-id <Function_ID>`。

所有单功能片段必须先通过 Stage1R 单功能语义评审；Stage1R 修正并复检后，才通过 `tools/hara/merge_stage1.py` 合并为本阶段最终文件。最终文件再按 `--stage stage1` 进行全量校验。

### derive_mf 约束

`derive_mf` 字段以“完整输出 Schema（严格遵循）”为准，不得新增、合并、拆分或改名字段。

### field_reasoning 结构（必须包含）

`field_reasoning` 用于记录每个故障字段的推理过程，结构以“完整输出 Schema（严格遵循）”为准。

**字段说明**：
- `字段`：故障类型名称
- `推理.是否有安全风险`：直接作为判断依据（`是` 表示适用，应填写故障描述；`否` 表示不适用，应填写 `nan`）

**一致性约束**：
- 如果 `推理.是否有安全风险` 为 `是`，则 `derive_mf` 中对应字段**不能**是 `nan`，必须填写具体故障描述
- 如果 `推理.是否有安全风险` 为 `否`，则 `derive_mf` 中对应字段**必须是** `nan`
- `check_stage_json.py --fix` 可执行机械一致性修复：`是 + nan` 时用同一推理记录的 `异常情况` 回填对应故障字段；`否 + 非 nan` 时将对应故障字段置为 `nan`
- 评审时必须检查 `是否有安全风险` 与最终值的一致性，并确认自动回填的异常情况是否足够具体
