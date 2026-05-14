---
name: hara-orchestrator
description: HARA 端到端流程编排与质量门禁。用于完整 HARA 分析、协调多个 HARA 阶段、从中间阶段恢复、验证阶段输出、合并 Stage 3A/3B、计算 ASIL、生成 SG_Sum 或导出最终 JSON/Excel。本 skill 只控制流程；具体分析交给 hara-stage0/1/2/3a/3b/4 及各 review skill。
---

# HARA 编排器

## 职责边界

将本 skill 作为完整 HARA 流程的单一入口。不要在编排器上下文里执行阶段分析、评审或 SEC 分维度判断；这里只做调度、验证、合并、ASIL 同步、导出和状态汇总。

## 上下文管理

- 先读取本文件，再只读取当前决策所需的引用文件。
- 给子 agent 传文件路径，不要粘贴大型 JSON 或知识库全文。
- 跨阶段只通过 JSON 文件传递结果；不要传递上一个 agent 的自由文本推理。
- 编排器只保存阶段状态、产物路径、验证摘要和门禁结论。
- Stage 3 按单个 `MF_ID` 处理；Stage 3A、Stage 3B、合并、Stage 3R 是独立上下文边界。
- 编排器不要加载完整知识库；由各 stage skill 判断需要读取哪些 `knowledge-base/automotive/hara/...` 文件。

## 真正子 Agent 要求

每个主阶段和 Review 阶段必须创建新的真实子 agent：

- 使用实际可用的 `spawn_agent` 工具，`agent_type="worker"`，`fork_context=false`。
- 不要用同一个上下文“并行列多个任务”替代子 agent；不要把多个 stage 合并给同一个 worker。
- 不要用 `multi_tool_use.parallel`、手写清单或普通函数调用模拟阶段 agent；这些只能用于本地读文件/跑工具，不能承担阶段分析。
- Review 子 agent 不复用生成子 agent 的上下文，必须重新从产物和窄参考文件评审。
- 如果当前运行环境没有 `spawn_agent`/`wait_agent`，停止并说明无法满足“真正创建子 agent”的隔离要求，不要降级模拟。

### 子 Agent 提示模板

每次调用 stage skill 都按这个模板生成 worker prompt，并把 `<...>` 替换为真实路径：

```text
使用 <stage skill>，在独立 worker 中完成 <stage name>。
你不独占代码库，不要回退或覆盖他人的无关改动。
工作区：<cwd>
输入文件：<input paths>
输出文件：<output path>
RUN_ID=<RUN_ID>；必要参数：<params>

必须先读取：
- skills/<stage skill>/SKILL.md
- 该 stage 的 schema/契约文件：<schema path>
- 只读取该 stage skill 要求的窄参考文件

输出要求：
- 严格按 schema 写 UTF-8 JSON 文件；不要输出 Markdown、代码围栏、表格或额外说明文本到产物文件。
- 写入后运行该 stage 的验证命令；验证失败时修 JSON 文件直到通过或返回明确阻塞。
- 最终只返回结构化摘要：status、output_file、validation、warnings/errors、changed_files。
```

示例调用形态：

```text
spawn_agent(
  agent_type="worker",
  fork_context=false,
  message="<按上方模板填充的 prompt>"
)
wait_agent(targets=["<agent_id>"])
```

对于独立 `MF_ID` 或 Stage3B 内部独立批次，先连续调用多个 `spawn_agent` 创建多个 worker，再用 `wait_agent` 等待需要进入门禁的 agent 结果。

## Schema 路由

每个生成型 stage prompt 必须显式要求读取对应 schema，并严格按 schema 写文件：

| Stage | Skill | Schema/契约 |
|---|---|---|
| Stage 0 | `hara-stage0` | `skills/hara-stage0/references/json-contracts.md` |
| Stage 1 | `hara-stage1` | `skills/hara-stage1/references/json-contracts.md` |
| Stage 2 | `hara-stage2` | `skills/hara-stage2/references/json-contracts.md` |
| Stage 3A | `hara-stage3a` | `skills/hara-stage3a/references/json-contracts.md` |
| Stage 3B | `hara-stage3b` | `skills/hara-stage3b/references/json-contracts.md` |
| Stage 4 | `hara-stage4` | `skills/hara-stage4/references/json-contracts.md` |
| Review | `hara-stage0r/1r/2r/3r/4r` | 对应 `references/*-review.md` 中的输出 Schema |

子 agent 产物不符合 schema 时，编排器必须先让对应 worker 修复并重新验证，不能让下游 agent 猜测结构。

## 路径约定

优先使用当前工作区资源：

- Skills：`skills/hara-*`
- 工具：`tools/hara`
- 知识库：`knowledge-base/automotive/hara`
- 输出目录：`output`
- 运行标识：`<RUN_ID>`，默认 `<SYSTEM>_HARA`

如果当前工作区没有对应资源，再回退到 `~/.claude` 下的安装副本。

## 流程

| 步骤 | Skill/工具 | 输入 | 输出 | 门禁 |
|---|---|---|---|---|
| 0 | `extract_function_doc.py` | Word/PDF/TXT/MD 源文档 | `output/<RUN_ID>_source_extraction.json` | 可选 |
| 1 | `hara-stage0` | 源文本/路径 | `output/<RUN_ID>_stage0_function_mapping.json` | 验证 stage0 |
| 2 | `hara-stage0r` | Stage 0 JSON，必要时加源文档 | `output/<RUN_ID>_stage0_review.json` | 必须通过 |
| 3 | `hara-stage1` | Stage 0 JSON | `output/<RUN_ID>_stage1_derive_mf.json` | 验证 stage1 |
| 4 | `hara-stage1r` | Stage 0 + Stage 1 JSON | `output/<RUN_ID>_stage1_review.json` | 必须通过 |
| 5 | `hara-stage2` | Stage 0 + Stage 1 JSON | `output/<RUN_ID>_stage2_mf_vehicle_hazards.json` | 验证 stage2 |
| 6 | `hara-stage2r` | Stage 1 + Stage 2 JSON | `output/<RUN_ID>_stage2_review.json` | 必须通过 |
| 7 | `prepare_stage3_context.py` | Stage 0 + Stage 2 JSON | `output/<RUN_ID>_stage3_context_<MF_ID>.json` | Stage3 最小上下文 |
| 8 | `hara-stage3a` | 当前 MF 的 Stage3 context | `output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json` | 验证 stage3a |
| 9 | `hara-stage3b` | Stage3 context + Stage 3A JSON | `output/<RUN_ID>_stage3b_<MF_ID>_sec.json` | 验证 stage3b_raw |
| 10 | `merge_stage3.py` | Stage 3A + Stage 3B | `output/<RUN_ID>_stage3_<MF_ID>_hara.json` | 验证 stage3 |
| 11 | `hara-stage3r` | Stage3 context + 合并后的 Stage 3 HARA | `output/<RUN_ID>_stage3_<MF_ID>_review.json` | 必须通过 |
| 12 | `apply_asil_matrix.py` | 合并后的 Stage 3 HARA | 更新 Stage 3 HARA | ASIL 已同步 |
| 13 | `hara-stage4` | 所有 Stage 3 HARA 文件 | `output/<RUN_ID>_stage4_sg_sum.json` | 验证 stage4 |
| 14 | `hara-stage4r` | Stage 3 HARA + Stage 4 JSON | `output/<RUN_ID>_stage4_review.json` | 必须通过 |
| 15 | 合并/导出工具 | 所有阶段输出 | `output/<RUN_ID>.json`、`.xlsx` | 最终验证与导出 |

## 编排步骤

1. 解析 `RUN_ID`、输入源文档和恢复点。
2. 对恢复点之后的每个主阶段创建独立 worker，并在 prompt 中显式列出输入、输出、schema 和验证命令。
3. worker 完成后，编排器运行或复核对应 `check_stage_json.py`；通过后再启动 Review worker。
4. Review worker 通过后才进入下一主阶段；不通过则重跑或修正被评审阶段，再重新 Review。
5. Stage3 前运行 `prepare_stage3_context.py mf-context --all` 生成每个 MF 的最小上下文。
6. 对每个 `MF_ID` 创建独立 Stage3A worker；Stage3A 全部或分批通过后，再为对应 `MF_ID` 创建 Stage3B worker。
7. Stage3B worker 内部仍必须使用真实子 agent 处理 S/E/C、Safety、FTTI 子任务；它不得在自己的总控上下文里做分维度评级。
8. 合并每个 MF 的 Stage3A/3B 后，为每个 `MF_ID` 创建独立 Stage3R worker。
9. 所有 Stage3R 通过后，统一执行 `apply_asil_matrix.py`，再启动 Stage4 和 Stage4R。
10. 最后执行合并与 Excel 导出，并返回简洁状态摘要。

## 并行策略

- 可并行：不同 `MF_ID` 的 Stage3A、Stage3B、Stage3R；Stage3B 内同一批次的 S/E/C 子任务；Safety 和 FTTI 子任务。
- 不可并行跨越门禁：Stage1 必须等 Stage0R 通过；Stage2 必须等 Stage1R 通过；Stage3 必须等 Stage2R 通过；Stage4 必须等所有 Stage3R 和 ASIL 同步完成。
- 并行时也必须创建多个真实 worker。一个 worker 只负责一个 stage、一个 `MF_ID` 或一个批次维度输出文件。

## 门禁规则

- Review 阶段是进入下一主阶段的必要条件。
- 遇到验证 `error` 必须停止并修正；`warning` 需要说明，若影响最终 HARA 质量则修正。
- 修正后的产物必须写回规范输出路径，保证后续工具读取最新版本。
- 如果重跑某个阶段，必须重新运行受影响的所有下游验证门禁。

## 核心命令

```text
python tools/hara/extract_function_doc.py --input <input_path> --out output/<RUN_ID>_source_extraction.json
python tools/hara/check_stage_json.py --stage <stage> --json <stage_json> [stage-specific args] --fix
python tools/hara/prepare_stage3_context.py mf-context --stage0 output/<RUN_ID>_stage0_function_mapping.json --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --all --prefix <RUN_ID> --out-dir output
python tools/hara/prepare_stage3_context.py sec-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --out-dir output --batch-size 5
python tools/hara/prepare_stage3_context.py review-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3 output/<RUN_ID>_stage3_<MF_ID>_hara.json --out-dir output --batch-size 5
python tools/hara/merge_stage3.py --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage3b output/<RUN_ID>_stage3b_<MF_ID>_sec.json --output output/<RUN_ID>_stage3_<MF_ID>_hara.json
python tools/hara/apply_asil_matrix.py --input output/<RUN_ID>_stage3_<MF_ID>_hara.json --output output/<RUN_ID>_stage3_<MF_ID>_hara.json
python tools/hara/generate_stage4_sg.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage4_sg_sum.json
python tools/hara/hara_stage_merge.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>.json
python tools/hara/run_hara_export.py --json output/<RUN_ID>.json --out output/<RUN_ID>.xlsx --mode basic
```

## 引用文件

- 只有在验证、合并、ASIL 同步或导出时，读取 `references/validation-export.md`。
- 只有在调整多 agent 架构时，读取 `references/architecture.md`。
- 只有在用户询问测试或中间阶段恢复时，读取 `references/testing-guide.md`。
- 只有在跨阶段结构契约问题时，读取 `references/json-contracts.md`；单阶段结构契约优先读对应 stage 的窄契约。

## 最终回复

返回简洁状态摘要：`status`、`system`、`json_path`、`excel_path`、最高 ASIL、warning/error 数量，以及本轮重跑过的阶段。
