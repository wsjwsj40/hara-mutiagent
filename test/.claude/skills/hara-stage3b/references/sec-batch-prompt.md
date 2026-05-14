# Stage 3B 批处理提示词总览

Stage 3B 不让一个子任务同时判断 S/E/C。每个批次最多 5 条场景，每批拆成三个互相独立的评级子任务。

## 子任务与规则文件

- S 子任务：
  - 提示词：`sec-s-batch-prompt.md`
  - 权威知识库：`04-risk_assessment-s.md`
  - 输出：`有风险的人员`、`可能的后果('S'的理由)`、`Severity 'S'`、`S评级推理`
- E 子任务：
  - 提示词：`sec-e-batch-prompt.md`
  - 权威知识库：`04-risk_assessment-e.md`
  - 输出：`E-解释`、`暴露频率'E'`、`E评级推理`
- C 子任务：
  - 提示词：`sec-c-batch-prompt.md`
  - 权威知识库：`04-risk_assessment-c.md`
  - 输出：`C-解释`、`控制能力 'C'`、`C评级推理`

## 总控合并

Stage3B 总控 agent 使用 `sec-merge-safety.md` 和 `04-risk_assessment-asil.md` 合并三个子任务结果：

1. 三类子任务都只输出 JSON 数组，按 `List_No` 对齐。
2. 某个 `List_No` 缺少 S/E/C 任一结果时，禁止生成最终 `sec_records`，必须重跑缺失子任务。
3. `结果ASIL` 由 S/E/C 后缀求和计算。
4. 每条最终 `sec_record` 的 `sec_reasoning` 结构为：

```json
{
  "S评级推理": {},
  "E评级推理": {},
  "C评级推理": {}
}
```

5. 所有批次合并后，为当前 MF 生成一个 `safety_goal` 和一个 `safe_state`。

## 禁止事项

- 不要让 S 子任务读取 E/C 知识库。
- 不要让 E 子任务读取 S/C 知识库。
- 不要让 C 子任务读取 S/E 知识库。
- 不要把 `04-risk_assessment.md` 索引当作规则正文放入任一子任务上下文。
- 不要在子任务里计算 ASIL 或生成安全目标。
