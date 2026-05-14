# Stage 3B 合并、ASIL 与安全目标规则

## 使用方式

仅供 Stage3B 总控 agent 读取。S/E/C 子任务不要读取本文件；它们只输出各自维度的 JSON 数组。

总控 agent 只需要读取：

- 当前 MF 的 Stage3 context
- 当前 MF 的 Stage3A JSON
- `references/json-contracts.md`
- S/E/C 子任务输出数组
- 本文件
- `knowledge-base/automotive/hara/common/04-risk_assessment-asil.md`
- `knowledge-base/automotive/hara/common/05-safety_goal.md`
- `knowledge-base/automotive/hara/common/06-ftti.md`

不要在总控阶段重新阅读 S/E/C 详细评级规则；评级结论来自子任务。

## 合并输入

每个批次应有三类 JSON 数组：

- S 数组：`List_No`、`有风险的人员`、`可能的后果('S'的理由)`、`Severity 'S'`、`S评级推理`
- E 数组：`List_No`、`E-解释`、`暴露频率'E'`、`E评级推理`
- C 数组：`List_No`、`C-解释`、`控制能力 'C'`、`C评级推理`

## 合并规则

1. 以 `List_No` 为唯一键对齐 S/E/C 结果。
2. 如果任何 `List_No` 缺少 S、E 或 C 中任一结果，停止合并并重跑缺失子任务。
3. 不要改写子任务的评级结论；只做结构合并、一致性检查和 ASIL 计算。
4. `sec_reasoning` 由三类推理对象组成：

```json
{
  "S评级推理": {},
  "E评级推理": {},
  "C评级推理": {}
}
```

5. 最终 `sec_records` 按 `List_No` 升序排列，数量必须等于 Stage3A `scenarios` 数量。

## ASIL 计算

ASIL 映射以 `04-risk_assessment-asil.md` 为准。总控 agent 只负责从 `Sx`、`Ey`、`Cz` 中解析后缀并按该知识库计算。

`结果ASIL` 写法：

```text
B (S2+E4+C2=8)
QM (S1+E3+C2=6)
```

如果评级字段无法解析为 `S0-S3`、`E0-E4`、`C0-C3`，停止并修正对应子任务输出，不要猜测。

## 安全目标

`safety_goal` 是当前 MF 级别的一条安全目标，基于最高可信风险路径生成，不是每条场景各写一条。

根据 `05-safety_goal.md` 知识库生成。

## 安全状态

`safe_state` 应描述能满足安全目标的车辆状态。

根据 `05-safety_goal.md` 知识库生成，与 `safety_goal` 对应。

## FTTI

根据 `06-ftti.md` 知识库生成。

**注意**：当某场景的 `结果ASIL` 为 QM 时，该场景的 `FTTI(ms)` 字段应置为空。

## 输出对象

最终只输出一个 UTF-8 JSON object：

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
