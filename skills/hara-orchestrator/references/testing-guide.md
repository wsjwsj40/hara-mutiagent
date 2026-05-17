# HARA 多 Agent 分阶段测试指南

## 概述

每个 Stage Agent 都支持独立运行，可以分阶段测试而不需要每次都从 Stage 0 开始。

## 前置条件

独立运行某个 Stage 前，需要确保已有所有前置阶段的 JSON 文件：

| 要运行的 Stage | 需要的前置文件 |
|---------------|---------------|
| Stage 0 | 无（输入文档或文本） |
| Stage 0R | `output/<RUN_ID>_stage0_function_mapping.json` |
| Stage 1 | `output/<RUN_ID>_stage0_function_mapping.json` |
| Stage 1R | `output/<RUN_ID>_stage1_context_<Function_ID>.json`<br>`output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json` |
| Stage 2 | `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`<br>`output/<RUN_ID>_stage1_context_<Function_ID>.json` |
| Stage 2R | `output/<RUN_ID>_stage1_<Function_ID>_derive_mf.json`<br>`output/<RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json` |
| Stage 3 | `output/<RUN_ID>_stage0_function_mapping.json`<br>`output/<RUN_ID>_stage2_mf_vehicle_hazards.json` |
| Stage 3R | `output/<RUN_ID>_stage3_<MF_ID>_hara.json`<br>`output/<RUN_ID>_stage2_mf_vehicle_hazards.json` |
| Stage 4 | 所有 Stage 3 HARA JSON 文件 |
| Stage 4R | `output/<RUN_ID>_stage4_sg_sum.json`<br>所有 Stage 3 HARA JSON 文件 |

## 使用方式

### 方式一：通过 Orchestrator（完整流程）

```
/hara-orchestrator
```

Orchestrator 会按顺序调用所有 Agent 和 Review。

### 方式二：直接调用单个 Agent（独立测试）

#### 示例 1：只运行 Stage 1

```
/hara-stage1

Orchestrator 会询问：
- RUN_ID（默认：EPB_HARA）
- Stage 0 JSON 路径（如果不在默认位置）
```

#### 示例 2：只评审 Stage 1

```
/hara-stage1r

适用于：
- Stage 1 已生成，想检查质量
- 发现 Stage 1 有问题，想重新评审
```

#### 示例 3：只处理单个 MF（Stage 3）

```
/hara-stage3 --run-id EPB_HARA --mf-id MF001

适用于：
- 只想测试某个 MF 的场景生成
- 某个 MF 需要重新生成
- 快速调试 Stage 3 问题
```

#### 示例 4：只评审单个 MF（Stage 3R）

```
/hara-stage3r --run-id EPB_HARA --mf-id MF001

适用于：
- 单个 MF 的场景质量检查
- 单个 MF 需要重新评审
```

## 常见测试场景

### 场景 1：Stage 3 发现某个 MF 场景有问题

```
# 1. 只重新生成该 MF
/hara-stage3 --run-id EPB_HARA --mf-id MF005

# 2. 重新评审该 MF
/hara-stage3r --run-id EPB_HARA --mf-id MF005
```

### 场景 2：Stage 1 有问题，需要重新生成

```
# 1. 重新运行 Stage 1
/hara-stage1 --run-id EPB_HARA

# 2. 评审新的 Stage 1
/hara-stage1r --run-id EPB_HARA
```

### 场景 3：只想测试某个 Review 阶段

```
# 评审 Stage 2
/hara-stage2r --run-id EPB_HARA

# 评审 Stage 4
/hara-stage4r --run-id EPB_HARA
```

## 注意事项

1. **文件依赖**：独立运行某个 Stage 前，确保所有前置文件存在且格式正确
2. **RUN_ID 一致**：所有阶段的文件应使用相同的 RUN_ID
3. **覆盖确认**：重新生成某个阶段时，会覆盖原有文件
4. **Review 必需**：虽然可以跳过 Review 直接进入下一阶段，但**不推荐**这样做

## 快速命令参考

```bash
# 完整流程
/hara-orchestrator

# 单独运行各 Stage
/hara-stage0
/hara-stage1
/hara-stage2
/hara-stage3

# 单独运行各 Review
/hara-stage0r
/hara-stage1r
/hara-stage2r
/hara-stage3r

# 带参数运行
/hara-stage3 --run-id EPB_HARA --mf-id MF001
/hara-stage3r --run-id EPB_HARA --mf-id MF001
```
