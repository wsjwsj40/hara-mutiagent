---
name: hara-orchestrator
description: HARA 端到端流程编排与质量门禁。用于完整 HARA 分析、协调多个 HARA 阶段、从中间阶段恢复、验证阶段输出、合并 Stage 3A/3B、计算 ASIL、生成 SG_Sum 或导出最终 JSON/Excel。本 skill 只控制流程；具体分析交给 hara-stage0/1/2/3a/3b/4 及各 review skill。
---

# HARA 编排器

## 职责边界

将本 skill 作为完整 HARA 流程的单一入口。不要在这里执行阶段分析。每个分析或评审步骤都交给对应 stage skill，本上下文只保留文件路径、状态、验证结果和交接决策。

## 上下文管理

- 先读取本文件，再只读取当前决策所需的引用文件。
- 给 stage agent 传文件路径，不要粘贴大型 JSON 或知识库全文。
- 每个主阶段和 Review 阶段都必须由独立子 agent 执行；编排器只保存阶段状态、产物路径和验证摘要。
- 子 agent 完成后，编排器只接收结构化摘要和输出路径，不接收其完整推理过程。
- Stage 3 按单个 `MF_ID` 处理；Stage 3A、Stage 3B、合并、Stage 3R 是独立上下文边界。
- 编排器不要加载完整知识库；由各 stage skill 判断需要读取哪些 `knowledge-base/automotive/hara/...` 文件。
- 对大型产物优先使用 `rg`、JSON 工具和验证脚本检查，不要整文件灌入对话上下文。

## 子 Agent 调用规则

- 每次调用一个 stage skill，都新建独立子 agent。
- 给子 agent 的输入只包含：当前 stage 名称、输入文件路径、输出文件路径、`RUN_ID`、必要参数。
- 不要把上一个子 agent 的推理笔记传给下一个子 agent；跨阶段只通过 JSON 文件传递。
- Review 子 agent 不复用生成子 agent 的上下文，必须重新从产物和窄参考文件评审。
- 如果运行环境暂时不支持真正子 agent，则按同样边界模拟：完成一个 stage 后清空该阶段工作上下文，只保留输出路径和摘要。

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

## 子 Agent 调用指示

**重要：每个主阶段和 Review 阶段必须使用 Agent 工具启动独立子 agent，不要在当前上下文执行。**

### 标准流程调用（从源文档到最终输出）

```text
# === Step 0: 源文档提取（可选） ===
如果输入是 Word/PDF，先启动子 agent 执行提取：
Agent(
  subagent_type="claude",
  prompt="执行 python tools/hara/extract_function_doc.py --input <input_path> --out output/<RUN_ID>_source_extraction.json"
)

# === Step 1: Stage 0 功能提取 ===
Agent(
  subagent_type="claude",
  prompt="执行 /hara-stage0 skill。输入：<input_text 或 output/<RUN_ID>_source_extraction.json>，输出：output/<RUN_ID>_stage0_function_mapping.json。RUN_ID=<RUN_ID>"
)

# === Step 2: Stage 0 Review（门禁） ===
Agent(
  subagent_type="claude",
  prompt="执行 /hara-stage0r skill。输入：output/<RUN_ID>_stage0_function_mapping.json，输出：output/<RUN_ID>_stage0_review.json。RUN_ID=<RUN_ID>"
)
# 等待结果，如果 review 未通过，重新运行 Step 1

# === Step 3: Stage 1 推导 MF ===
Agent(
  subagent_type="claude",
  prompt="执行 /hara-stage1 skill。输入：output/<RUN_ID>_stage0_function_mapping.json，输出：output/<RUN_ID>_stage1_derive_mf.json。RUN_ID=<RUN_ID>"
)

# === Step 4: Stage 1 Review（门禁） ===
Agent(
  subagent_type="claude",
  prompt="执行 /hara-stage1r skill。输入：output/<RUN_ID>_stage0_function_mapping.json + output/<RUN_ID>_stage1_derive_mf.json，输出：output/<RUN_ID>_stage1_review.json。RUN_ID=<RUN_ID>"
)
# 等待结果，如果 review 未通过，重新运行 Step 3

# === Step 5: Stage 2 危害分析 ===
Agent(
  subagent_type="claude",
  prompt="执行 /hara-stage2 skill。输入：output/<RUN_ID>_stage0_function_mapping.json + output/<RUN_ID>_stage1_derive_mf.json，输出：output/<RUN_ID>_stage2_mf_vehicle_hazards.json。RUN_ID=<RUN_ID>"
)

# === Step 6: Stage 2 Review（门禁） ===
Agent(
  subagent_type="claude",
  prompt="执行 /hara-stage2r skill。输入：output/<RUN_ID>_stage1_derive_mf.json + output/<RUN_ID>_stage2_mf_vehicle_hazards.json，输出：output/<RUN_ID>_stage2_review.json。RUN_ID=<RUN_ID>"
)
# 等待结果，如果 review 未通过，重新运行 Step 5

# === Step 7-11: Stage 3 循环（对每个 MF_ID） ===
# 先准备 Stage 3 context
bash: python tools/hara/prepare_stage3_context.py mf-context --stage0 output/<RUN_ID>_stage0_function_mapping.json --stage2 output/<RUN_ID>_stage2_mf_vehicle_hazards.json --all --prefix <RUN_ID> --out-dir output

# 对每个 MF_ID：
for each MF_ID:
  # Step 8: Stage 3A 场景分析
  Agent(
    subagent_type="claude",
    prompt="执行 /hara-stage3a skill。输入：output/<RUN_ID>_stage3_context_<MF_ID>.json，输出：output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json。RUN_ID=<RUN_ID>, MF_ID=<MF_ID>"
  )

  # Step 9: Stage 3B SEC 分析
  Agent(
    subagent_type="claude",
    prompt="执行 /hara-stage3b skill。输入：output/<RUN_ID>_stage3_context_<MF_ID>.json + output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json，输出：output/<RUN_ID>_stage3b_<MF_ID>_sec.json。RUN_ID=<RUN_ID>, MF_ID=<MF_ID>"
  )

  # Step 10: 合并 Stage 3A/3B
  bash: python tools/hara/merge_stage3.py --stage3a output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json --stage3b output/<RUN_ID>_stage3b_<MF_ID>_sec.json --output output/<RUN_ID>_stage3_<MF_ID>_hara.json

  # Step 11: Stage 3 Review（门禁）
  Agent(
    subagent_type="claude",
    prompt="执行 /hara-stage3r skill。输入：output/<RUN_ID>_stage3_context_<MF_ID>.json + output/<RUN_ID>_stage3_<MF_ID>_hara.json，输出：output/<RUN_ID>_stage3_<MF_ID>_review.json。RUN_ID=<RUN_ID>, MF_ID=<MF_ID>"
  )
  # 等待结果，如果 review 未通过，重新运行 Step 8-11

  # Step 12: 应用 ASIL 矩阵
  bash: python tools/hara/apply_asil_matrix.py --input output/<RUN_ID>_stage3_<MF_ID>_hara.json --output output/<RUN_ID>_stage3_<MF_ID>_hara.json

# === Step 13: Stage 4 安全目标 ===
Agent(
  subagent_type="claude",
  prompt="执行 /hara-stage4 skill。输入：所有 output/<RUN_ID>_stage3_*_hara.json 文件，输出：output/<RUN_ID>_stage4_sg_sum.json。RUN_ID=<RUN_ID>"
)

# === Step 14: Stage 4 Review（门禁） ===
Agent(
  subagent_type="claude",
  prompt="执行 /hara-stage4r skill。输入：output/<RUN_ID>_stage4_sg_sum.json，输出：output/<RUN_ID>_stage4_review.json。RUN_ID=<RUN_ID>"
)
# 等待结果，如果 review 未通过，重新运行 Step 13

# === Step 15: 最终合并与导出 ===
bash: python tools/hara/hara_stage_merge.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>.json
bash: python tools/hara/run_hara_export.py --json output/<RUN_ID>.json --out output/<RUN_ID>.xlsx --mode basic
```

### 中间阶段恢复

如果从某个中间阶段恢复：

```text
# 例如：从 Stage 2 重新开始
# 直接调用对应 agent
Agent(
  subagent_type="claude",
  prompt="执行 /hara-stage2 skill。输入：output/<RUN_ID>_stage0_function_mapping.json + output/<RUN_ID>_stage1_derive_mf.json，输出：output/<RUN_ID>_stage2_mf_vehicle_hazards.json。RUN_ID=<RUN_ID>"
)
```

### 并行执行提示

对于独立的 MF_ID 处理，可以并行启动多个 Stage 3 子 agent：

```text
# 在同一消息中发送多个 Agent 调用
Agent(...) for MF_001
Agent(...) for MF_002
Agent(...) for MF_003
```

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
