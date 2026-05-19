---
name: hara-orchestrator
description: HARA 端到端流程编排与质量门禁。用于完整 HARA 分析、协调多个 HARA 阶段、从中间阶段恢复、验证阶段输出、合并 Stage 3A/3B、校验 ASIL、生成 SG_Sum 或导出最终 JSON/Excel。本 skill 只控制流程；具体分析交给 hara-stage0/1/2/3a/3b/4 及各 review skill。
---

# HARA 编排器

## 职责边界

将本 skill 作为完整 HARA 流程的单一入口。不要在编排器上下文里执行阶段分析、评审或 SEC 分维度判断；这里只做调度、验证、合并、ASIL 校验、导出和状态汇总。

## 上下文管理

- 先读取本文件，再只读取当前决策所需的引用文件。
- 给子 agent 传文件路径，不要粘贴大型 JSON 或知识库全文。
- 跨阶段只通过 JSON 文件传递结果；不要传递上一个 agent 的自由文本推理。
- 编排器只保存阶段状态、产物路径、验证摘要和门禁结论。
- Stage 3 按单个 `MF_ID` 处理；Stage 3A、Stage 3AR、Stage 3B、Stage 3BR 和合并校验是独立上下文边界。
- 编排器不要加载完整知识库；由各 stage skill 判断需要读取哪些 `knowledge-base/automotive/hara/...` 文件。

## 真正子 Agent 要求

每个主阶段和 Review 阶段必须创建新的真实子 agent：

- 使用实际可用的 `Agent` 工具，`subagent_type=”claude”`，`run_in_background=true`。
- 不要用同一个上下文”并行列多个任务”替代子 agent；不要把多个 stage 合并给同一个 worker。
- 不要用 `multi_tool_use.parallel`、手写清单或普通函数调用模拟阶段 agent；这些只能用于本地读文件/跑工具，不能承担阶段分析。
- Review 子 agent 不复用生成子 agent 的上下文，必须重新从产物和窄参考文件评审。
- 如果当前运行环境没有 `Agent` 工具，停止并说明无法满足”真正创建子 agent”的隔离要求，不要降级模拟。

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
Agent(
  subagent_type="claude",
  description="<简短描述>",
  prompt="<按上方模板填充的 prompt>",
  run_in_background=true
)
```

对于独立 `MF_ID` 或 Stage3B 内部独立批次，先连续调用多个 `Agent` 创建多个 worker，等待所有子任务完成后再合并结果。

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
| Review | `hara-stage0r/1r/2r/3ar/3br/4r` | 对应 `references/*-review.md` 或人工审查留痕 |

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
| 3 | `prepare_stage1_context.py` + `hara-stage1` | Stage 0 JSON；按 `Function_ID` 拆分 | `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json` | 单片验证 |
| 4 | `hara-stage1r` + `merge_stage1.py` + `merge_stage1_review.py` | Stage1 context + Stage1 单功能片段 | `output/<RUN_ID>_stage1_derive_mf.json`、`output/<RUN_ID>_stage1_review.json` | 单功能语义评审 + Stage1 合并后验证 |
| 5 | `hara-stage2` | Stage0 + Stage1 单功能片段 | `output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json` | 单片验证 |
| 6 | `hara-stage2r` + `merge_stage2.py` + `merge_stage2_review.py` | Stage1 单功能片段 + Stage2 单功能片段 | `output/<RUN_ID>_stage2_mf_vehicle_hazards.json`、`output/<RUN_ID>_stage2_review.json` | 单功能语义评审 + Stage2 合并后验证 |
| 7 | `prepare_stage3_context.py` | Stage1 context 目录 + Stage2 JSON | `output/<RUN_ID>_stage3_context_<MF_ID>.json` | 每个 MF 一个上下文 |
| 8 | `hara-stage3a` | 当前 MF 的 Stage3 context | `output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json` | 验证 stage3a |
| 9 | `hara-stage3ar` | Stage3 context + Stage3A JSON | `output/<RUN_ID>_stage3a_<MF_ID>_review.json` | 场景语义评审通过 |
| 10 | `hara-stage3b` | Stage3 context + Stage3A JSON | `output/<RUN_ID>_stage3b_<MF_ID>_sec.json` | 验证 stage3b |
| 11 | `hara-stage3br` | Stage3A JSON + Stage3B SEC JSON | `output/<RUN_ID>_stage3b_<MF_ID>_review.json` | SEC 语义评审通过 |
| 12 | `merge_stage3.py` + `check_stage_json.py` | Stage 3A + Stage 3B | `output/<RUN_ID>_stage3_<MF_ID>_hara.json` | 验证 stage3 + ASIL 一致性 |
| 13 | `hara-stage4` | 所有 Stage 3 HARA 文件 | `output/<RUN_ID>_stage4_sg_sum.json` | 同一 MF 内按安全目标汇总 + 操作模式已填写 |
| 14 | `hara-stage4r` | Stage 4 JSON + 必要 HARA 来源行 | `output/<RUN_ID>_stage4_review.json` | 操作模式评审通过 |
| 15 | 合并/导出工具 | 所有阶段输出 | `output/<RUN_ID>.json`、`.xlsx` | 最终验证与导出 |

## 编排步骤

1. 解析 `RUN_ID`、输入源文档和恢复点。
2. 对恢复点之后的每个主阶段创建独立 worker，并在 prompt 中显式列出输入、输出、schema 和验证命令。
3. worker 完成后，编排器运行或复核对应 `check_stage_json.py`；通过后再启动 Review worker。
4. Stage1 特例：先运行 `prepare_stage1_context.py` 生成 `output/<RUN_ID>_stage1_context_<Function_ID>.json`。随后为每个 `Function_ID` 创建独立 Stage1 worker；每个 worker 只读取当前 context 文件和必要规则，输出 `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`。每个片段必须先通过 `check_stage_json.py --stage stage1_slice --fix`。
5. Stage1R 特例：为每个 `Function_ID` 创建独立 Stage1R worker；每个 worker 只读取当前 context 和当前 Stage1 单功能片段，输出 `output/<RUN_ID>_stage1_<Function_ID>_review.json` 作为人工审查留痕，必要时修正当前 Stage1 单功能片段，并重新运行 `stage1_slice --fix`。所有 Function_ID 的 Stage1R 通过后，才运行 `merge_stage1.py` 合并最终 Stage1，再运行 `merge_stage1_review.py` 合并总 review。Stage1R review 文件不运行严格 schema check；合并脚本只检查 review 文件可解析、可识别 `Function_ID` 且覆盖 Stage0 全部功能。
6. Stage2 特例：为每个 `Function_ID` 创建独立 Stage2 worker；每个 worker 只读取当前 Stage1 单功能片段和当前功能 Stage0 上下文，输出 `output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json`。每个片段必须通过 `check_stage_json.py --stage stage2_slice --fix`。不要在 Stage2R 前合并最终 Stage2。
7. Stage2R 特例：为每个 `Function_ID` 创建独立 Stage2R worker；每个 worker 只读取当前 Stage1 单功能片段和当前 Stage2 单功能片段，输出 `output/<RUN_ID>_stage2_<Function_ID>_review.json` 作为人工审查留痕，必要时修正当前 Stage2 单功能片段，并重新运行 `stage2_slice --fix`。所有 Function_ID 的 Stage2R 通过后，才运行 `merge_stage2.py` 合并最终 Stage2，再运行 `merge_stage2_review.py` 合并总 review。
8. Review worker 通过后才进入下一主阶段；不通过则重跑或修正被评审阶段，再重新 Review。
9. Stage3 前运行 `prepare_stage3_context.py mf-context --all`，只拆分 Stage2 中产生的 MF；功能背景复用 `output/<RUN_ID>_stage1_context_<Function_ID>.json`。
10. 对每个 `MF_ID` 创建独立 Stage3A worker；Stage3A 机器校验通过后，创建对应 Stage3AR worker。Stage3AR 不通过则修正或重跑 Stage3A。
11. Stage3AR 通过后，再为对应 `MF_ID` 创建 Stage3B worker。Stage3B worker 内部仍必须使用真实子 agent 处理 S/E/C、Safety、FTTI 子任务；它不得在自己的总控上下文里做分维度评级。
12. Stage3B 机器校验通过后，创建 Stage3BR worker；Stage3BR 不通过则重跑对应 Stage3B 维度 batch 并重新合并 SEC。
13. Stage3BR 通过后，合并每个 MF 的 Stage3A/3B，并运行 `check_stage_json.py --stage stage3 --fix` 作为合并后门禁；ASIL 不一致必须回到 Stage3B 修正，不再调用 `apply_asil_matrix.py` 自动覆盖。
14. 所有 MF 的 Stage3 合并校验通过后，启动 Stage4 和 Stage4R。
15. 最后执行合并与 Excel 导出，并返回简洁状态摘要。

## 并行策略

- 可并行：不同 `Function_ID` 的 Stage1/Stage1R/Stage2/Stage2R；不同 `MF_ID` 的 Stage3A/Stage3AR/Stage3B/Stage3BR；Stage3B 内同一批次的 S/E/C 子任务；Safety 和 FTTI 子任务。
- 不可并行跨越门禁：Stage1 必须等 Stage0R 通过；Stage2 必须等 Stage1R 通过；Stage3A 必须等 Stage2R 通过；同一 MF 的 Stage3B 必须等 Stage3AR 通过；同一 MF 的 Stage3 合并必须等 Stage3BR 通过；Stage4 必须等所有 Stage3 HARA 通过 `--stage stage3`。
- 并行时也必须创建多个真实 worker。一个 worker 只负责一个 stage、一个 `MF_ID` 或一个批次维度输出文件。

## 门禁规则

- Review 阶段是进入下一主阶段的必要条件；其中 Stage1R 只做语义评审，不重复替代 Stage1 机器校验，Stage1R review 文件也不作为严格 JSON schema 门禁。
- 遇到验证 `error` 必须停止并修正；`warning` 需要说明，若影响最终 HARA 质量则修正。
- 修正后的产物必须写回规范输出路径，保证后续工具读取最新版本。
- 如果重跑某个阶段，必须重新运行受影响的所有下游验证门禁。

## 核心命令

```text
python tools/hara/extract_function_doc.py --input <input_path> --out output/<RUN_ID>_source_extraction.json
python tools/hara/check_stage_json.py --stage <stage> --json <stage_json> [stage-specific args] --fix
python tools/hara/prepare_stage1_context.py --stage0 output/<RUN_ID>_stage0_function_mapping.json --prefix <RUN_ID> --out-dir output
python tools/hara/check_stage_json.py --stage stage1_slice --json output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json --stage0 output/<RUN_ID>_stage0_function_mapping.json --function-id <Function_ID> --fix
python tools/hara/merge_stage1.py --stage0 output/<RUN_ID>_stage0_function_mapping.json --input-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage1_derive_mf.json
python tools/hara/check_stage_json.py --stage stage1 --json output/<RUN_ID>_stage1_derive_mf.json --stage0 output/<RUN_ID>_stage0_function_mapping.json --fix
python tools/hara/merge_stage1_review.py --input-dir output --stage0 output/<RUN_ID>_stage0_function_mapping.json --prefix <RUN_ID> --out output/<RUN_ID>_stage1_review.json
python tools/hara/check_stage_json.py --stage stage2_slice --json output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json --stage1 output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json --function-id <Function_ID> --fix
python tools/hara/merge_stage2.py --stage0 output/<RUN_ID>_stage0_function_mapping.json --input-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage2_mf_vehicle_hazards.json
python tools/hara/check_stage_json.py --stage stage2 --json output/<RUN_ID>_stage2_mf_vehicle_hazards.json --stage1 output/<RUN_ID>_stage1_derive_mf.json --fix
python tools/hara/merge_stage2_review.py --input-dir output --stage0 output/<RUN_ID>_stage0_function_mapping.json --prefix <RUN_ID> --out output/<RUN_ID>_stage2_review.json
python tools/hara/prepare_stage3_context.py mf-context --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --stage1-context-dir output --all --prefix <RUN_ID> --out-dir output
python tools/hara/prepare_stage3_context.py stage3a-review-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --prefix <RUN_ID> --out-dir output --batch-size 5
python tools/hara/prepare_stage3_context.py sec-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --prefix <RUN_ID> --out-dir output --batch-size 5
python tools/hara/prepare_stage3_context.py stage3b-review-batches --context output/<RUN_ID>_stage3_context_<MF_ID>.json --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage3b output/<RUN_ID>_stage3b_<MF_ID>_sec.json --mf-id <MF_ID> --prefix <RUN_ID> --out-dir output --batch-size 5
python tools/hara/merge_stage3.py --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage3b output/<RUN_ID>_stage3b_<MF_ID>_sec.json --output output/<RUN_ID>_stage3_<MF_ID>_hara.json
python tools/hara/check_stage_json.py --stage stage3 --json output/<RUN_ID>_stage3_<MF_ID>_hara.json --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --mf-id <MF_ID> --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
python tools/hara/generate_stage4_sg.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage4_sg_sum.json
python tools/hara/hara_stage_merge.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>_before_stage4_check.json
python tools/hara/check_stage_json.py --stage stage4 --json output/<RUN_ID>_stage4_sg_sum.json --hara output/<RUN_ID>_before_stage4_check.json --fix
python tools/hara/hara_stage_merge.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>.json
python tools/hara/run_hara_export.py --json output/<RUN_ID>.json --out output/<RUN_ID>.xlsx --mode basic
```

## 引用文件

- 只有在验证、合并、ASIL 校验或导出时，读取 `references/validation-export.md`。
- 只有在调整多 agent 架构时，读取 `references/architecture.md`。
- 只有在用户询问测试或中间阶段恢复时，读取 `references/testing-guide.md`。
- 只有在跨阶段结构契约问题时，读取 `references/json-contracts.md`；单阶段结构契约优先读对应 stage 的窄契约。

## 最终回复

返回简洁状态摘要：`status`、`system`、`json_path`、`excel_path`、最高 ASIL、warning/error 数量，以及本轮重跑过的阶段。
