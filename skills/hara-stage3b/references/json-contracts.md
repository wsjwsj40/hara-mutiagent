# HARA JSON 契约 - Stage 3B

本文件只定义 Stage3B 输出结构和机器可校验字段。评级方法、子任务编排和合并规则分别见 `stage3b-sec-rating.md`、`sec-batch-prompt.md` 和 `sec-merge-safety.md`。

所有产物必须是 UTF-8 JSON。不要输出 Markdown、代码围栏、表格或额外说明文本。

## 最终文件

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
    "generated_at": "ISO时间戳"
  },
  "sec_records": [
    {
      "List_No": 1,
      "E-解释": "<E等级定义和暴露理由>",
      "暴露频率'E'": "E0/E1/E2/E3/E4",
      "有风险的人员": "<受影响人员>",
      "可能的后果('S'的理由)": "<伤害分析和最高S选择理由>",
      "Severity 'S'": "S0/S1/S2/S3",
      "C-解释": "<C等级定义和可控性理由>",
      "控制能力 'C'": "C0/C1/C2/C3",
      "结果ASIL": "<由 merge_sec_batches.py 派生，check_stage_json.py 复算校验>",
      "sec_reasoning": {
        "S评级推理": {},
        "E评级推理": {},
        "C评级推理": {}
      },
      "FTTI(ms)": "<可选，毫秒>",
      "FTTI理由": "<可选>",
      "备注": ""
    }
  ],
  "safety_goal": "<当前MF最高可信风险路径对应的安全目标>",
  "safe_state": "<能实现安全目标的安全状态>"
}
```

## sec_records 约束

- 数量必须等于 Stage3A `scenarios` 数量。
- `List_No` 必须与 Stage3A `scenarios[*].List_No` 一一对应。
- `sec_reasoning` 必须包含 `S评级推理`、`E评级推理`、`C评级推理`。
- `Severity 'S'` 必须等于 `sec_reasoning.S评级推理.S等级`。
- `暴露频率'E'` 必须等于 `sec_reasoning.E评级推理.E等级`。
- `控制能力 'C'` 必须等于 `sec_reasoning.C评级推理.C等级`。
- `结果ASIL` 只能由合并脚本派生，子任务不要填写；`stage3b` check 会复算校验。
- Stage3B 只输出 SEC 增量字段，不重复输出 Stage3A 场景字段。

## S 中间文件

文件：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_s.json`

顶层为 JSON array。每项必须包含：

- `List_No`
- `有风险的人员`
- `可能的后果('S'的理由)`
- `Severity 'S'`
- `S评级推理`

`S评级推理` 至少包含 `伤害分析`、`碰撞对象`、`碰撞速度`、`参考规则`、`S等级`、`S理由`。

## E 中间文件

文件：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_e.json`

顶层为 JSON array。每项必须包含：

- `List_No`
- `E-解释`
- `暴露频率'E'`
- `E评级推理`

`E评级推理` 至少包含 `场景持续时间`、`场景发生频率`、`参考规则`、`E等级`、`E理由`。

## C 中间文件

文件：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_c.json`

顶层为 JSON array。每项必须包含：

- `List_No`
- `C-解释`
- `控制能力 'C'`
- `C评级推理`

`C评级推理` 至少包含 `感知来源`、`反应时间`、`可用操作`、`空间约束`、`参考规则`、`C等级`、`C理由`。

## FTTI 中间文件

文件：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_ftti.json`

顶层为 JSON array。每项必须包含：

- `List_No`
- `FTTI(ms)`
- `FTTI理由`

QM 场景的 `FTTI(ms)` 可以为空字符串。

## Safety 中间文件

文件：`output/<RUN_ID>_stage3b_<MF_ID>_safety.json`

```json
{
  "safety_goal": "<当前MF级安全目标>",
  "safe_state": "<当前MF级安全状态>"
}
```
