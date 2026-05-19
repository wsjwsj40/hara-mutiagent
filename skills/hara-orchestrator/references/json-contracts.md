# HARA JSON 契约

所有阶段文件必须是 UTF-8 JSON object。不要输出 Markdown 表格、代码围栏、额外说明文本或数组作为顶层结构。

## 使用方式

这是跨阶段总契约。只有在编排器需要比较多个阶段结构、排查合并问题或统一导出问题时读取。单阶段生成优先读取对应 skill 下更窄的 `references/json-contracts.md`。

## 目录

- 顶层结构
- Review JSON
- Stage 0: function_mapping
- Stage 1: derive_mf
- Stage 2: mf_vehicle_hazards
- Stage 3: hara
- Stage 4: sg_sum

## 顶层结构

最终合并 JSON 固定使用小写 key：

```json
{
  "meta": {},
  "function_mapping": [],
  "derive_mf": [],
  "mf_vehicle_hazards": [],
  "hara": [],
  "sg_sum": [],
  "review_log": []
}
```

每个阶段文件都应包含 `meta` 和 `review_log`。`meta.knowledge_files_used` 记录本阶段实际读取的知识库。

## Review JSON

每个 review 是独立阶段，必须单独模型调用并输出独立文件。以下结构作为标准 review 外壳；Stage3AR/Stage3BR 可保留更轻的人工审查留痕，但建议仍包含 `meta`、`overall_result`、`issues` 和 `fixes` 便于追踪：

```json
{
  "meta": {
    "run_id": "<run_id>",
    "stage": "<stage_review>",
    "target_file": "<被评审文件>",
    "generated_at": "ISO时间戳"
  },
  "overall_result": "pass/failed",
  "issues": [],
  "fixes": [],
  "review_log": [
    {
      "stage": "<stage_review>",
      "target": "<target>",
      "result": "pass",
      "issues": [],
      "fixes": [],
      "notes": ""
    }
  ]
}
```

如果 review 发现问题，先修正被评审 stage JSON，再把修正说明写入 review JSON 的 `fixes`，并在修正后的 stage JSON `review_log` 中记录通过。阶段完成文件中不要保留 `failed` 状态。

Stage3AR 和 Stage3BR 是语义审查留痕文件，不作为最终交付结构，通常不运行严格 schema check。Stage3A/3B 合并后不再生成独立集成 review 文件，合并完整性由 `check_stage_json.py --stage stage3` 校验。

## Stage 0: function_mapping

文件：`output/<run_id>_stage0_function_mapping.json`

只允许顶层 key：`meta`、`function_mapping`、`review_log`。

`function_mapping` 字段：

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

## Stage 1: derive_mf

文件：`output/<run_id>_stage1_derive_mf.json`

只允许顶层 key：`meta`、`derive_mf`、`review_log`、`knowledge_evidence`、`field_reasoning`。

`derive_mf` 固定列：

- `No.`
- `子功能`
- `功能丧失`
- `过大`
- `过早`
- `过小`
- `过晚`
- `非预期激活`
- `卡滞`
- `方向错误`

`field_reasoning` 结构（必须包含）：

用于记录每个故障字段的推理过程，推理在结论之前生成。

```json
{
  "field_reasoning": [
    {
      "row": 1,
      "子功能": "目标状态执行功能",
      "字段推理": [
        {
          "字段": "过小",
          "推理": {
            "功能输出": "目标保持力",
            "异常情况": "目标保持力低于设计下限",
            "后果": "无法有效维持设计目标状态，可能产生安全相关后果",
            "是否适用": "是",
            "是否有安全风险": "是"
          }
        },
        {
          "字段": "方向错误",
          "推理": {
            "功能输出": "互斥动作或目标状态方向",
            "异常情况": "请求 A 动作或 A 状态时执行相反 B 动作或 B 状态",
            "后果": "与请求或设计意图相反，可能产生安全相关后果",
            "是否适用": "是",
            "是否有安全风险": "是"
          }
        },
        {
          "字段": "过早",
          "推理": {
            "功能输出": "动作执行时机",
            "异常情况": "在触发条件未满足时提前执行",
            "后果": "若当前功能由外部即时请求触发且无自动提前触发机理，则该故障类型不适用",
            "是否适用": "否",
            "是否有安全风险": "否"
          }
        }
      ]
    }
  ]
}
```

**字段说明**：
- `字段`：故障类型名称
- `推理.是否适用`：直接作为 Stage1 可见故障字段判断依据（`是` 表示应填写故障描述；`否` 表示不适用，应填写 `nan`）
- `推理.是否有安全风险`：只表示该适用故障是否会进入 Stage2；`否` 不会把 Stage1 故障字段改成 `nan`

**一致性约束**：
- 如果 `推理.是否适用` 为 `是`，则 `derive_mf` 中对应字段**不能**是 `nan`，必须填写具体故障描述
- 如果 `推理.是否适用` 为 `否`，则 `derive_mf` 中对应字段**必须是** `nan`
- 如果 `推理.是否有安全风险` 为 `是`，则 `推理.是否适用` 必须为 `是`
- Stage2 只枚举 `derive_mf` 非 `nan` 且 `field_reasoning.推理.是否有安全风险=是` 的故障
- 评审时必须检查 `是否适用` 与最终值的一致性

## Stage 2: mf_vehicle_hazards

文件：`output/<run_id>_stage2_mf_vehicle_hazards.json`

只允许顶层 key：`meta`、`mf_vehicle_hazards`、`review_log`、`knowledge_evidence`、`hazard_reasoning`。

`mf_vehicle_hazards` 固定列：

- `No.`
- `Milf_ID`
- `Function_ID`
- `source_function_name`
- `Stage1_Row`
- `Fault_Field`
- `Stage1_Fault_Text`
- `故障描述`
- `整车级危害`
- `备注`

`整车级危害` 必须逐字来自 `knowledge-base/automotive/hara/common/vehicle_hazards.json`。
`hazard_reasoning[*].推理.选择的危害` 必须与对应行的 `整车级危害` 完全一致。

## Stage 3: hara

文件：`output/<run_id>_stage3_<MF_ID>_hara.json`

只允许顶层 key：`meta`、`max_asil_planning`、`hara`、`safety_goal`、`safe_state`、`review_log`、`knowledge_evidence`。

`hara` 固定列：

- `List_No`
- `MF_ID`
- `故障描述`
- `整车危害`
- `道路类型`
- `道路条件`
- `环境条件`
- `车辆状态`
- `车速(km/h)`
- `特殊要素`
- `附加条件`
- `驾驶员是否在车上`
- `危害事件`
- `E-解释`
- `暴露频率'E'`
- `有风险的人员`
- `可能的后果('S'的理由)`
- `Severity 'S'`
- `C-解释`
- `控制能力 'C'`
- `结果ASIL`
- `安全目标`
- `安全状态`
- `FTTI(ms)`
- `备注`

六大场景字段 `道路类型`、`道路条件`、`环境条件`、`车辆状态`、`车速(km/h)`、`特殊要素` 必须逐字来自 `knowledge-base/automotive/hara/common/operation_scenarios.json`。库外描述只能写入 `附加条件`。
合并后的每条 `hara` 记录应保留 `scenario_reasoning` 和 `sec_reasoning`，用于追溯 Stage3A 场景推理和 Stage3B SEC 推理。

每个单独 MF 文件内 `List_No` 可从 1 开始；最终合并时由工具重排为全局连续序号。

## Stage 4: sg_sum

文件：`output/<run_id>_stage4_sg_sum.json`

只允许顶层 key：`meta`、`sg_sum`、`review_log`。

`sg_sum` 固定列：

- `SG_No`
- `MF_ID`
- `安全目标`
- `ASIL Level`
- `安全状态`
- `操作模式`
- `FTTI(ms)`
- `Comments`

`sg_sum` 在同一 `MF_ID` 内按相同 `安全目标` 汇总。不同 MF 即使安全目标文字相同，也分别保留；`MF_ID` 必须是当前单个 MF，例如 `MF001`。

仅由 `QM` 场景组成的 MF/安全目标组合不得出现在 `sg_sum` 中。同一 MF/安全目标组合的 `ASIL Level` 取 HARA 中最高 ASIL，`FTTI(ms)` 取最小 FTTI。

除 `操作模式` 外，Stage4 其他字段必须由工具从 HARA 的 MF_ID + 安全目标分组派生。`操作模式` 是 Stage4 唯一需要模型填写的字段，不能保留空值或 `待Stage4模型填写` 占位。
