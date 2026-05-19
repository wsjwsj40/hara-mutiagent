# HARA 多 Agent 分阶段测试指南

## 概述

每个 Stage Agent 都支持独立运行，可以分阶段测试而不必每次从 Stage 0 开始。Stage 3 已拆成 `Stage3A -> Stage3AR -> Stage3B -> Stage3BR -> merge/check`，测试时按这个门禁顺序推进。

## 前置条件

独立运行某个 Stage 前，需要确保已有所有前置阶段 JSON 文件：

| 要运行的 Stage | 需要的前置文件 |
|---|---|
| Stage 0 | 无（输入文档或文本） |
| Stage 0R | `output/<RUN_ID>_stage0_function_mapping.json` |
| Stage 1 | `output/<RUN_ID>_stage0_function_mapping.json` |
| Stage 1R | `output/<RUN_ID>_stage1_context_<Function_ID>.json`<br>`output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json` |
| Stage 2 | `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`<br>`output/<RUN_ID>_stage1_context_<Function_ID>.json` |
| Stage 2R | `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`<br>`output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json` |
| Stage 3A | `output/<RUN_ID>_stage3_context_<MF_ID>.json` |
| Stage 3AR | `output/<RUN_ID>_stage3_context_<MF_ID>.json`<br>`output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json` |
| Stage 3B | `output/<RUN_ID>_stage3_context_<MF_ID>.json`<br>`output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json` |
| Stage 3BR | `output/<RUN_ID>_stage3_context_<MF_ID>.json`<br>`output/<RUN_ID>_stage3a_<MF_ID>_scenarios.json`<br>`output/<RUN_ID>_stage3b_<MF_ID>_sec.json` |
| Stage 4 | 所有 Stage 3 HARA JSON 文件；Stage4 只补 `操作模式` |
| Stage 4R | `output/<RUN_ID>_stage4_sg_sum.json`<br>所有 Stage 3 HARA JSON 文件；只评审 `操作模式` |

## 使用方式

### 方式一：通过 Orchestrator（完整流程）

```text
/hara-orchestrator
```

Orchestrator 会按顺序调用所有生成、Review、校验、合并和导出工具。

### 方式二：直接调用单个 Agent（独立测试）

#### 示例 1：只运行 Stage 1

```text
/hara-stage1
```

适用于调试功能故障生成。运行后应先通过 Stage1 单文件 check，再进入 `hara-stage1r`。

#### 示例 2：只评审 Stage 1

```text
/hara-stage1r
```

适用于 Stage 1 已生成后检查质量，或修正单个 `Function_ID` 的功能故障。

#### 示例 3：只处理单个 MF 的 Stage 3A 场景

```text
/hara-stage3a --run-id EPB_HARA --mf-id MF001
/hara-stage3ar --run-id EPB_HARA --mf-id MF001
```

适用于调试某个 MF 的场景生成、运行域约束、危害事件表达和场景独立性。

#### 示例 4：只处理单个 MF 的 Stage 3B 评级

```text
/hara-stage3b --run-id EPB_HARA --mf-id MF001
/hara-stage3br --run-id EPB_HARA --mf-id MF001
```

适用于 Stage3A 已通过后，只重跑 S/E/C/FTTI、安全目标或安全状态。

#### 示例 5：只做 Stage 3 合并校验

```text
python tools/hara/merge_stage3.py --stage3a output/EPB_HARA_stage3a_MF001_scenarios.json --stage3b output/EPB_HARA_stage3b_MF001_sec.json --output output/EPB_HARA_stage3_MF001_hara.json
python tools/hara/check_stage_json.py --stage stage3 --json output/EPB_HARA_stage3_MF001_hara.json --stage2 output/EPB_HARA_stage2_mf_vehicle_hazards.json --mf-id MF001 --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
```

适用于 Stage3AR 和 Stage3BR 已通过，且只需要检查 Stage3A/Stage3B 合并后的字段承接和一致性。

## 常见测试场景

### 场景 1：Stage 3A 发现某个 MF 场景有问题

```text
# 1. 只重新生成该 MF 的场景
/hara-stage3a --run-id EPB_HARA --mf-id MF005

# 2. 重新评审该 MF 的场景
/hara-stage3ar --run-id EPB_HARA --mf-id MF005
```

Stage3A 修正后，应重新运行 `check_stage_json.py --stage stage3a`，再进入 Stage3B。

### 场景 2：Stage 3B 发现 SEC 或 FTTI 有问题

```text
# 1. 只重跑该 MF 的评级
/hara-stage3b --run-id EPB_HARA --mf-id MF005

# 2. 重新评审该 MF 的评级
/hara-stage3br --run-id EPB_HARA --mf-id MF005
```

Stage3B 修正后，应重新运行 `check_stage_json.py --stage stage3b`，再合并 Stage3。

### 场景 3：只想测试某个 Review 阶段

```text
/hara-stage2r --run-id EPB_HARA
/hara-stage3ar --run-id EPB_HARA --mf-id MF001
/hara-stage3br --run-id EPB_HARA --mf-id MF001
/hara-stage4r --run-id EPB_HARA
```

## 快速命令参考

```text
# 完整流程
/hara-orchestrator

# 单独运行生成阶段
/hara-stage0
/hara-stage1
/hara-stage2
/hara-stage3a --run-id EPB_HARA --mf-id MF001
/hara-stage3b --run-id EPB_HARA --mf-id MF001
/hara-stage4

# 单独运行 Review
/hara-stage0r
/hara-stage1r
/hara-stage2r
/hara-stage3ar --run-id EPB_HARA --mf-id MF001
/hara-stage3br --run-id EPB_HARA --mf-id MF001
/hara-stage4r
```

Stage4 独立测试时，先用 `generate_stage4_sg.py` 从 Stage3 HARA 派生 SG_Sum，再让模型填写 `操作模式`，最后运行 `check_stage_json.py --stage stage4`。Stage4R 只检查已填写的 `操作模式` 是否具体且与来源场景一致。

## 注意事项

1. 独立运行某个 Stage 前，先确认前置文件存在且格式正确。
2. 同一轮分析中所有阶段应使用相同 `RUN_ID`。
3. 重新生成某个阶段可能覆盖原文件，先确认只重跑目标 `Function_ID` 或 `MF_ID`。
4. Review 不建议跳过；Stage3B 必须等 Stage3AR 通过，同一 MF 的 Stage3 合并必须等 Stage3BR 通过，Stage4 必须等所有 Stage3 HARA 合并校验通过。
