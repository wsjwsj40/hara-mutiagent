# Stage 3B SEC 评级总控

本文件只给 Stage3B 总控读取，用于编排批次和隔离子任务。字段结构见 `json-contracts.md`，S/E/C 具体规则由各子任务读取对应知识库。

## 文件分工

- 输出契约：`references/json-contracts.md`
- 子任务通用约束：`references/sec-batch-prompt.md`
- S 子任务：`references/sec-s-batch-prompt.md` + `knowledge-base/automotive/hara/common/04-risk_assessment-s.md`
- E 子任务：`references/sec-e-batch-prompt.md` + `knowledge-base/automotive/hara/common/04-risk_assessment-e.md`
- C 子任务：`references/sec-c-batch-prompt.md` + `knowledge-base/automotive/hara/common/04-risk_assessment-c.md`
- FTTI 子任务：`references/sec-ftti-batch-prompt.md` + `knowledge-base/automotive/hara/common/06-ftti.md`
- 合并、安全目标、安全状态：`references/sec-merge-safety.md` + `knowledge-base/automotive/hara/common/04-risk_assessment-asil.md` + `knowledge-base/automotive/hara/common/05-safety_goal.md`

## 总控上下文

总控只保留：

- 当前 MF 的 `stage3_context_<MF_ID>.json`
- 当前 MF 的 `stage3a_<MF_ID>_scenarios.json`
- 批次文件路径
- 子任务输出文件路径
- 合并后的摘要和验证结果

总控不要读取 S/E/C 详细评级知识库正文，不要在总控上下文直接完成 S/E/C 评级。

## 子任务边界

每个 `stage3b_<MF_ID>_batchXX_context.json` 默认最多 5 条场景，拆为四类独立任务：

- S：只判断严重度，输出 `batchXX_s.json`
- E：只判断暴露度，输出 `batchXX_e.json`
- C：只判断可控性，输出 `batchXX_c.json`
- FTTI：只计算 FTTI，输出 `batchXX_ftti.json`

子任务只输出文件，不在聊天响应中返回 JSON 数组。任一维度缺失或校验不一致时，只重跑对应维度和对应 batch。

## 执行流程

1. 生成 Stage3B batch context：

```text
python tools/hara/prepare_stage3_context.py sec-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --prefix <RUN_ID> --out-dir output --batch-size 5
```

2. 对每个 batch 并行或顺序执行 S/E/C/FTTI 子任务。每个子任务只读取自己的 batch context、对应 prompt 和对应知识库。

3. 生成 `output/<RUN_ID>_stage3b_<MF_ID>_safety.json`，只包含 `safety_goal` 和 `safe_state`。

4. 调用合并脚本：

```text
python tools/hara/merge_sec_batches.py --s-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_s.json --e-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_e.json --c-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_c.json --ftti-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_ftti.json --safety output/<RUN_ID>_stage3b_<MF_ID>_safety.json --output output/<RUN_ID>_stage3b_<MF_ID>_sec.json --meta-mf-id <MF_ID> --meta-run-id <RUN_ID>
```

5. 校验 Stage3B SEC 文件：

```text
python tools/hara/check_stage_json.py --stage stage3b --json output/<RUN_ID>_stage3b_<MF_ID>_sec.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --min-scenarios 10 --max-scenarios 20
```

## 上下文压力控制

- 不跨 MF 读取或比较场景。
- 不把 Stage3A 场景复制到 Stage3B 输出中。
- 不把 S/E/C 知识库全文放进总控 prompt。
- 不在总控里保留子任务长篇推理草稿，只保留文件路径和校验摘要。
- 不为追求高 ASIL 修改子任务评级；有疑问时重跑对应维度。
