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
  +-- stage3b 子 agent（每个 MF 独立）
  |     +-- batch 子任务：每批最多 5 条场景做 SEC 评级
  +-- stage3r 子 agent（每个 MF 独立）
        +-- batch 子任务：每批最多 5 条 HARA 记录做评审
  |
  +-- stage4 子 agent：SG_Sum 汇总
  +-- stage4r 子 agent：SG_Sum 评审
```

## 核心原则

### 0. 必须使用真实子 agent

编排器和 Stage3B/Stage3R 总控必须通过实际 `spawn_agent(agent_type="worker", fork_context=false, ...)` 创建独立 worker。不要用同一个上下文里的多段提示、普通并行工具调用或人工清空上下文来模拟子 agent。

如果当前环境没有 `spawn_agent`/`wait_agent`，停止并报告无法满足隔离要求；不要降级为单上下文执行。

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
Stage0 + Stage2
  -> prepare_stage3_context.py mf-context
  -> stage3_context_<MF_ID>.json
  -> Stage3A / Stage3B / Stage3R 子 agent
```

`stage3_context_<MF_ID>.json` 只包含：

- 当前 MF 的 Stage2 行
- 当前 MF 的 hazard_reasoning
- 匹配到的 Stage0 功能行和 `detail_text`
- 功能运行域线索
- 输入文件来源和上下文策略

Stage3A/B/R 不应读取完整 Stage0 或完整 Stage2。

### 5. Stage3B 和 Stage3R 再批处理

Stage3B：

```text
stage3_context_<MF_ID>.json + stage3a_<MF_ID>_scenarios.json
  -> prepare_stage3_context.py sec-batches
  -> stage3b_<MF_ID>_batch01_context.json ...
  -> 每批一个评级子任务
```

Stage3R：

```text
stage3_context_<MF_ID>.json + stage3_<MF_ID>_hara.json
  -> prepare_stage3_context.py review-batches
  -> stage3r_<MF_ID>_batch01_context.json ...
  -> 每批一个评审子任务
```

批次大小默认 5 条。批次子任务只输出 JSON 数组，不输出解释文本；总控 agent 负责合并。

## Agent 通信

所有 agent 通过 JSON 文件通信：

| 阶段 | 子 agent 输入 | 子 agent 输出 |
|---|---|---|
| Stage0 | 源文本/文档 | Stage0 JSON |
| Stage0R | Stage0 JSON + 源文档可选 | Stage0 review JSON + 修正后 Stage0 |
| Stage1 | Stage0 JSON | Stage1 JSON |
| Stage1R | Stage0 + Stage1 JSON | Stage1 review JSON + 修正后 Stage1 |
| Stage2 | Stage0 + Stage1 JSON | Stage2 JSON |
| Stage2R | Stage1 + Stage2 JSON | Stage2 review JSON + 修正后 Stage2 |
| Stage3A | `stage3_context_<MF_ID>.json` | Stage3A scenarios JSON |
| Stage3B | Stage3 context + Stage3A JSON + batch contexts | Stage3B SEC JSON |
| Stage3R | Stage3 context + merged Stage3 JSON + review batch contexts | Stage3R review JSON |
| Stage4 | Stage3 HARA 文件目录 | Stage4 SG_Sum JSON |
| Stage4R | Stage3 HARA + Stage4 JSON | Stage4R review JSON |

## 失败处理

- 子 agent 失败：编排器记录失败 stage、输入路径、错误摘要，允许只重跑该 stage。
- 验证失败：先修正当前 stage 输出，再继续下游。
- Review 不通过：阻止进入下一阶段，重跑或修正被评审 stage。
- Stage3 某个 MF 失败：只重跑该 MF 的 Stage3A/B/R，不影响其他 MF。

## 扩展方式

新增阶段时：

1. 新建 stage skill。
2. 在编排器流程表中加入该阶段。
3. 明确该阶段输入输出文件。
4. 若输入文件较大，先新增切片工具，再让子 agent 读取切片结果。
