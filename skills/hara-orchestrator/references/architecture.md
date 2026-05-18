# HARA 多 Agent 架构说明

## 使用方式

只有在调整多 agent 架构、排查上下文污染或解释 Stage3 并行方式时读取本文件。普通执行只读 `SKILL.md`。

## 架构概览

```text
hara-orchestrator（只编排，不分析）
  |
  +-- stage0 子 agent：功能提取
  +-- stage0r 子 agent：功能提取评审
  +-- stage1 子 agent：功能故障生成
  +-- stage1r 子 agent：功能故障评审
  +-- stage2 子 agent：整车危害生成
  +-- stage2r 子 agent：整车危害评审
  |
  +-- Stage3 上下文切片工具：prepare_stage3_context.py
  |     +-- 每个 MF 一个 stage3_context_<MF_ID>.json
  |
  +-- stage3a 子 agent（每个 MF 独立）
  +-- stage3ar 子 agent（每个 MF 独立）
  |     +-- batch 子任务：每批最多 5 条 Stage3A 场景做评审
  +-- stage3b 子 agent（每个 MF 独立）
  |     +-- batch 子任务：每批最多 5 条场景做 SEC 评级
  +-- stage3br 子 agent（每个 MF 独立）
  |     +-- batch 子任务：每批最多 5 条 Stage3A/Stage3B 配对记录做 SEC 评审
  +-- merge_stage3.py + check_stage_json.py：合并 Stage3A/3B 并做确定性校验
  |
  +-- stage4 子 agent：SG_Sum 汇总
  +-- stage4r 子 agent：SG_Sum 评审
```

## 核心原则

### 0. 必须使用真实子 agent

编排器和 Stage3B/Stage3AR/Stage3BR 总控必须通过实际 `Agent(subagent_type="claude", run_in_background=true, ...)` 创建独立 worker。不要用同一个上下文里的多段提示、普通并行工具调用或人工清空上下文来模拟子 agent。

如果当前环境没有 `Agent` 工具，停止并报告无法满足隔离要求；不要降级为单上下文执行。

### 1. 编排器不做语义分析

编排器只负责：

- 决定下一步调用哪个子 agent
- 传递文件路径和参数
- 运行验证、合并、导出工具
- 汇总状态和错误

编排器不要读取大 JSON，不要读取完整知识库，不要在主上下文里推理 HARA 内容。

### 2. 每个阶段独立上下文

每个主阶段和 Review 阶段都使用新的子 agent。阶段之间只通过 JSON 文件传递结果，不传递上一个 agent 的自由文本推理。

### 3. Review 独立于生成

Review 子 agent 不能复用生成子 agent 的上下文。它必须重新读取产物和窄参考文件，以减少“自己证明自己正确”的偏差。

### 4. Stage3 使用上下文切片

Stage3 是上下文压力最大的部分，必须先切片再分析：

```text
Stage2 MF + Stage1 function context
  -> prepare_stage3_context.py mf-context
  -> stage3_context_<MF_ID>.json
  -> Stage3A / Stage3AR / Stage3B / Stage3BR 子 agent
```

`stage3_context_<MF_ID>.json` 只包含：

- 当前 MF 的 Stage2 行
- 当前 MF 的 hazard_reasoning
- 复用的 Stage1 function context 和 `detail_text`
- 功能运行域线索
- 输入文件来源和上下文策略

Stage3A/3AR/3B/3BR 不应读取完整 Stage0 或完整 Stage2。Stage3 context 生成只拆 Stage2 MF，不重新拆功能背景。

### 5. Stage3 Review 分段批处理

Stage3AR：

```text
stage3_context_<MF_ID>.json + stage3a_<MF_ID>_scenarios.json
  -> prepare_stage3_context.py stage3a-review-batches
  -> stage3ar_<MF_ID>_batch01_context.json ...
  -> 每批一个场景评审子任务
```

Stage3B：

```text
stage3_context_<MF_ID>.json + stage3a_<MF_ID>_scenarios.json
  -> prepare_stage3_context.py sec-batches
  -> stage3b_<MF_ID>_batch01_context.json ...
  -> 每批一个评级子任务
```

Stage3BR：

```text
stage3_context_<MF_ID>.json + stage3a_<MF_ID>_scenarios.json + stage3b_<MF_ID>_sec.json
  -> prepare_stage3_context.py stage3b-review-batches
  -> stage3br_<MF_ID>_batch01_context.json ...
  -> 每批一个 SEC 评审子任务
```

Stage3BR 通过后，`merge_stage3.py` 合并 Stage3A/3B，随后 `check_stage_json.py --stage stage3` 检查合并完整性、Stage2 对齐、场景枚举和基础结构。合并后不再创建额外评审 agent。

批次大小默认 5 条。批次子任务只输出 JSON 数组，不输出解释文本；总控 agent 负责合并。

## Agent 通信

所有 agent 通过 JSON 文件通信：

| 阶段 | 子 agent 输入 | 子 agent 输出 |
|---|---|---|
| Stage0 | 源文本/文档 | Stage0 JSON |
| Stage0R | Stage0 JSON + 源文档可选 | Stage0 review JSON + 修正后 Stage0 |
| Stage1 | Stage1 context by Function_ID | Stage1 single-function JSON |
| Stage1R | Stage1 context + Stage1 single-function JSON | Stage1 review trace + 修正后 Stage1 single-function JSON |
| Stage2 | Stage1 single-function JSON + current Stage0 context | Stage2 single-function JSON |
| Stage2R | Stage1 single-function JSON + Stage2 single-function JSON | Stage2 review trace + 修正后 Stage2 single-function JSON |
| Stage3A | `stage3_context_<MF_ID>.json` | Stage3A scenarios JSON |
| Stage3AR | Stage3 context + Stage3A JSON + review batch contexts | Stage3A review trace |
| Stage3B | Stage3 context + Stage3A JSON + batch contexts | Stage3B SEC JSON |
| Stage3BR | Stage3 context + Stage3A JSON + Stage3B JSON + review batch contexts | Stage3B review trace |
| Stage3 merge/check | Stage3A JSON + Stage3B JSON | merged Stage3 HARA JSON |
| Stage4 | Stage3 HARA 文件目录 | Stage4 SG_Sum JSON |
| Stage4R | Stage3 HARA + Stage4 JSON | Stage4R review JSON |

## 失败处理

- 子 agent 失败：编排器记录失败 stage、输入路径、错误摘要，允许只重跑该 stage。
- 验证失败：先修正当前 stage 输出，再继续下游。
- Review 不通过：阻止进入下一阶段，重跑或修正被评审 stage。
- Stage3 某个 MF 失败：只重跑该 MF 的 Stage3A/3AR/3B/3BR 或合并校验，不影响其他 MF。

## 扩展方式

新增阶段时：

1. 新建 stage skill。
2. 在编排器流程表中加入该阶段。
3. 明确该阶段输入输出文件。
4. 若输入文件较大，先新增切片工具，再让子 agent 读取切片结果。
