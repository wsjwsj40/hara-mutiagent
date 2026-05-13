---
name: hara-stage4
description: Stage 4 SG_Sum 汇总。用于在 Stage 3 HARA 文件完成 ASIL 同步后，使用 generate_stage4_sg.py 生成 output/<RUN_ID>_stage4_sg_sum.json。过滤最高 ASIL 为 QM 的 MF，并继承每个 MF 的最高 ASIL。不要用于从零手写安全目标。
---

# Stage 4：SG_Sum 汇总

## 职责边界

使用确定性工具生成 SG_Sum。不要凭记忆手工重建 SG 行。

## 输入输出

- 输入：所有完成 ASIL 同步的 `output/<RUN_ID>_stage3_<MF_ID>_hara.json` 文件。
- 输出：`output/<RUN_ID>_stage4_sg_sum.json`。
- 仅在需要澄清工具行为或 SG 字段时，读取 `references/stage4-sg-summary.md`。

## 上下文加载

1. 不要把每个 Stage 3 文件全部读入对话上下文。
2. 使用 `generate_stage4_sg.py` 扫描 Stage 3 文件。
3. 只在摘要或排障时读取生成后的 Stage 4 JSON。
4. 只有在安全目标表述存疑时，才加载 `knowledge-base/automotive/hara/common/05-safety_goal.md`。

## 规则

- 排除最高 ASIL 为 `QM` 的 MF。
- SG_Sum 的 ASIL 继承该 MF 的最高 ASIL HARA 场景。
- 保留与最高风险路径对应的安全目标和安全状态。
- `SG_No` 连续编号。

## 执行流程

1. 确认所有 Stage 3 文件已经运行 `apply_asil_matrix.py`。
2. 运行生成工具。
3. 验证 Stage 4；可自动修复的 warning 交给 Stage 4R 或最终验证处理。

## 命令

```text
python tools/hara/generate_stage4_sg.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage4_sg_sum.json
python tools/hara/check_stage_json.py --stage stage4 --json output/<RUN_ID>_stage4_sg_sum.json --hara output/<RUN_ID>_stage3_<MF_ID>_hara.json --fix
```

## 返回

返回 `status`、`total_sg`、`qm_filtered`、ASIL 分布、输出文件，并说明下一步是否进入 Stage 4R。
