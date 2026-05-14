# Stage 3B SEC 评级总控导航

## 使用方式

本文件只给 Stage3B 总控 agent 读取，用于选择上下文和编排子任务。它不承载 S/E/C 详细评级规则。

关键原则：不要让任何子任务同时读取 S、E、C 全量规则。每个评级维度只读取自己的批次上下文和窄规则文件。

## 文件分工

- JSON 结构契约：`references/json-contracts.md`
- 批处理总览：`references/sec-batch-prompt.md`
- S 子任务提示词：`references/sec-s-batch-prompt.md`
- S 权威知识库：`knowledge-base/automotive/hara/common/04-risk_assessment-s.md`
- E 子任务提示词：`references/sec-e-batch-prompt.md`
- E 权威知识库：`knowledge-base/automotive/hara/common/04-risk_assessment-e.md`
- C 子任务提示词：`references/sec-c-batch-prompt.md`
- C 权威知识库：`knowledge-base/automotive/hara/common/04-risk_assessment-c.md`
- 合并、ASIL：`references/sec-merge-safety.md`
- ASIL 权威知识库：`knowledge-base/automotive/hara/common/04-risk_assessment-asil.md`
- 安全目标知识库：`knowledge-base/automotive/hara/common/05-safety_goal.md`
- FTTI 知识库：`knowledge-base/automotive/hara/common/06-ftti.md`

## 总控上下文

Stage3B 总控 agent 的活跃上下文只保留：

- 当前 MF 的 `stage3_context_<MF_ID>.json`
- 当前 MF 的 `stage3a_<MF_ID>_scenarios.json`
- `json-contracts.md`
- `sec-batch-prompt.md`
- `sec-merge-safety.md`
- `04-risk_assessment-asil.md`
- `05-safety_goal.md`
- `06-ftti.md`
- 已完成批次的合成后 `sec_records` 摘要

总控 agent 不读取 S/E/C 知识库，除非是在定位某个子任务输出错误。

## 子任务上下文

每个批次最多 5 条场景。每个批次拆成三个互不共享推理上下文的子任务：

- S 子任务：只读取批次上下文、`sec-s-batch-prompt.md`、`04-risk_assessment-s.md`
- E 子任务：只读取批次上下文、`sec-e-batch-prompt.md`、`04-risk_assessment-e.md`
- C 子任务：只读取批次上下文、`sec-c-batch-prompt.md`、`04-risk_assessment-c.md`

子任务只输出 JSON 数组，不输出 Markdown、解释文字或顶层对象。

## 执行流程

1. 读取当前 MF 的 Stage3 context 和 Stage3A JSON。
2. 运行批次切片：

```text
python tools/hara/prepare_stage3_context.py sec-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --out-dir output --batch-size 5
```

3. 对每个 `stage3b_<MF_ID>_batchXX_context.json` 分别运行 S/E/C 子任务。
4. 按 `List_No` 合并三类结果；任一维度缺失时停止并重跑缺失子任务。
5. 依据 `sec-merge-safety.md` 计算 `结果ASIL`，组装 `sec_reasoning`。
6. 所有批次完成后，基于最高可信风险路径生成一个 MF 级 `safety_goal` 和 `safe_state`。
7. 写入 `output/<RUN_ID>_stage3b_<MF_ID>_sec.json`。

## 上下文压力控制

- 不在总控上下文保留子任务完整草稿，只保留结构化结果。
- 不跨 MF 读取或比较场景。
- 不把 Stage3A 场景复制到 Stage3B 输出中。
- 不把总知识库全文粘贴进提示词；按维度读取拆分后的知识库文件。
- 发现某个维度有争议时，只重跑对应维度子任务，不重跑整个 Stage3B。

## 验证

```text
python tools/hara/check_stage_json.py --stage stage3b_raw --json output/<RUN_ID>_stage3b_<MF_ID>_sec.json --mf-id <MF_ID> --min-scenarios 10 --max-scenarios 20
```
