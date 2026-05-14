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

每个 review 是独立阶段，必须单独模型调用并输出独立文件：

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

Stage 3R 是特殊 review：除 `review_log` 外，还必须包含 `per_scenario_reviews`，逐条对应当前 MF HARA 文件中的每个场景。汇总文件不能替代逐 MF、逐场景 review。

`per_scenario_reviews` 每行必须包含：

- `List_No`
- `MF_ID`
- `result`
- `scenario_reality`
- `scenario_independence`
- `internal_consistency`
- `operational_domain_consistency`
- `max_asil_search_coverage`
- `motion_logic`
- `hazard_event_logic`
- `sec_reasoning`
- `safety_goal_consistency`
- `issues`
- `fixes`
- `notes`

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
      "子功能": "静态开关拉起",
      "字段推理": [
        {
          "字段": "过小",
          "推理": {
            "功能输出": "夹紧力（用于保持车辆静止）",
            "异常情况": "夹紧力低于设计下限",
            "后果": "无法有效保持车辆静止，车辆可能溜车",
            "是否有安全风险": "是"
          }
        },
        {
          "字段": "方向错误",
          "推理": {
            "功能输出": "拉起/释放动作方向",
            "异常情况": "请求拉起时执行释放动作",
            "后果": "与驾驶员意图相反，车辆可能从静止状态变为移动",
            "是否有安全风险": "是"
          }
        },
        {
          "字段": "过早",
          "推理": {
            "功能输出": "拉起动作执行时机",
            "异常情况": "在拉起条件未满足时提前执行",
            "后果": "本功能由驾驶员主动请求触发，无自动提前触发机理",
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
- `推理.是否有安全风险`：直接作为判断依据（`是` 表示适用，应填写故障描述；`否` 表示不适用，应填写 `nan`）

**一致性约束**：
- 如果 `推理.是否有安全风险` 为 `是`，则 `derive_mf` 中对应字段**不能**是 `nan`，必须填写具体故障描述
- 如果 `推理.是否有安全风险` 为 `否`，则 `derive_mf` 中对应字段**必须是** `nan`
- 评审时必须检查 `是否有安全风险` 与最终值的一致性

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
合并后的每条 `hara` 记录应保留 `scenario_reasoning` 和 `sec_reasoning`，用于 Stage3R 逐场景评审。

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

如果某个 MF 的最高 ASIL 为 `QM`，该 MF 在 `sg_sum` 中不得出现任何条目。
