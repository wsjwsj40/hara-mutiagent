# HARA JSON 契约 - Stage 3B

所有阶段文件必须是 UTF-8 JSON object。不要输出 Markdown 表格、代码围栏、额外说明文本或数组作为顶层结构。

## 完整输出 Schema（严格遵循）

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "mf_id": "<MF_ID>",
    "stage": "stage3b",
    "generated_at": "ISO时间戳",
    "source_files": [
      "output/<RUN_ID>_stage3_context_<MF_ID>.json",
      "output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json"
    ],
    "knowledge_files_used": []
  },
  "sec_records": [
    {
      "List_No": 1,
      "E-解释": "<E等级定义+场景暴露理由>",
      "暴露频率'E'": "E0/E1/E2/E3/E4",
      "有风险的人员": "<本场景受影响人员>",
      "可能的后果('S'的理由)": "<人员伤害分析和最高S选择理由>",
      "Severity 'S'": "S0/S1/S2/S3",
      "C-解释": "<C等级定义+场景可控性理由>",
      "控制能力 'C'": "C0/C1/C2/C3",
      "结果ASIL": "QM/A/B/C/D (Sx+Ey+Cz=score)",
      "sec_reasoning": {
        "S评级推理": {
          "伤害分析": "<伤害机制>",
          "碰撞对象": "<风险对象或不涉及>",
          "碰撞速度": "<速度/能量依据或不涉及>",
          "参考规则": "04-risk_assessment-s.md",
          "S等级": "S0/S1/S2/S3",
          "S理由": "<选择理由>"
        },
        "E评级推理": {
          "场景持续时间": "<持续时间或暴露窗口>",
          "场景发生频率": "<场景频率依据>",
          "参考规则": "04-risk_assessment-e.md",
          "E等级": "E0/E1/E2/E3/E4",
          "E理由": "<选择理由>"
        },
        "C评级推理": {
          "感知来源": "<驾驶员/系统可感知线索>",
          "反应时间": "<可用反应时间>",
          "可用操作": "<可采取的控制动作>",
          "空间约束": "<道路/交通空间约束>",
          "参考规则": "04-risk_assessment-c.md",
          "C等级": "C0/C1/C2/C3",
          "C理由": "<选择理由>"
        }
      },
      "FTTI(ms)": 1000,
      "备注": ""
    }
  ],
  "safety_goal": "<该MF最高风险路径对应的安全目标>",
  "safe_state": "<能实现安全目标的安全状态>"
}
```

## 使用方式

只在需要确认 Stage 3B JSON 结构时读取本文件。它只定义结构，不承载评级规则。

- 总控导航读 `stage3b-sec-rating.md`
- 批处理总览读 `sec-batch-prompt.md`
- 合并、ASIL、安全目标读 `sec-merge-safety.md`
- ASIL 计算读 `04-risk_assessment-asil.md`
- S 子任务读 `sec-s-batch-prompt.md` + `04-risk_assessment-s.md`
- E 子任务读 `sec-e-batch-prompt.md` + `04-risk_assessment-e.md`
- C 子任务读 `sec-c-batch-prompt.md` + `04-risk_assessment-c.md`

不要为了字段名问题读取 `04-risk_assessment.md` 索引或任何风险评估知识库正文。

## 顶层结构

文件：`output/<RUN_ID>_stage3b_<MF_ID>_sec.json`

只允许顶层 key：

- `meta`
- `sec_records`
- `safety_goal`
- `safe_state`

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "mf_id": "<MF_ID>",
    "stage": "stage3b",
    "generated_at": "<ISO8601>"
  },
  "sec_records": [],
  "safety_goal": "...",
  "safe_state": "..."
}
```

## sec_records 字段

每条记录对应 Stage 3A 的一条 `scenarios`，按 `List_No` 一一对应。

必填字段：

- `List_No`
- `E-解释`
- `暴露频率'E'`
- `有风险的人员`
- `可能的后果('S'的理由)`
- `Severity 'S'`
- `C-解释`
- `控制能力 'C'`
- `结果ASIL`
- `sec_reasoning`

可选字段：

- `FTTI(ms)`
- `备注`

## sec_record 模板

```json
{
  "List_No": 1,
  "E-解释": "...",
  "暴露频率'E'": "E3",
  "有风险的人员": "...",
  "可能的后果('S'的理由)": "...",
  "Severity 'S'": "S1",
  "C-解释": "...",
  "控制能力 'C'": "C2",
  "结果ASIL": "QM (S1+E3+C2=6)",
  "sec_reasoning": {
    "S评级推理": {
      "伤害分析": "...",
      "碰撞对象": "...",
      "碰撞速度": "...",
      "参考规则": "04-risk_assessment-s.md",
      "S等级": "S1",
      "S理由": "..."
    },
    "E评级推理": {
      "场景持续时间": "...",
      "场景发生频率": "...",
      "参考规则": "04-risk_assessment-e.md",
      "E等级": "E3",
      "E理由": "..."
    },
    "C评级推理": {
      "感知来源": "...",
      "反应时间": "...",
      "可用操作": "...",
      "空间约束": "...",
      "参考规则": "04-risk_assessment-c.md",
      "C等级": "C2",
      "C理由": "..."
    }
  },
  "FTTI(ms)": 1000,
  "备注": ""
}
```

## 一致性约束

- `sec_records` 数量必须等于 Stage 3A `scenarios` 数量。
- `sec_records[*].List_No` 必须与 Stage 3A `scenarios[*].List_No` 一致。
- `sec_reasoning.S评级推理.S等级` 必须等于 `Severity 'S'`。
- `sec_reasoning.E评级推理.E等级` 必须等于 `暴露频率'E'`。
- `sec_reasoning.C评级推理.C等级` 必须等于 `控制能力 'C'`。
- `结果ASIL` 必须包含等级和计算式，例如 `B (S2+E4+C2=8)`。
- Stage 3B 只输出 SEC 增量字段，不重复输出 Stage 3A 的场景字段。

## S/E/C 中间输出

S 子任务只输出 JSON 数组：

```json
[
  {
    "List_No": 1,
    "有风险的人员": "...",
    "可能的后果('S'的理由)": "...",
    "Severity 'S'": "S1",
    "S评级推理": {}
  }
]
```

E 子任务只输出 JSON 数组：

```json
[
  {
    "List_No": 1,
    "E-解释": "...",
    "暴露频率'E'": "E3",
    "E评级推理": {}
  }
]
```

C 子任务只输出 JSON 数组：

```json
[
  {
    "List_No": 1,
    "C-解释": "...",
    "控制能力 'C'": "C2",
    "C评级推理": {}
  }
]
```

总控 agent 按 `List_No` 合并中间输出，任何一类缺失时不得生成最终文件。
